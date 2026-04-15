from __future__ import annotations

import base64
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

from cham_bai.collector import CollectedBundle, format_bundle_for_prompt
from cham_bai.git_remote import fetch_repo_sources_bundle, normalize_github_repo_url
from cham_bai.openrouter import complete_chat_raw


_SYSTEM = """Bạn là giảng viên chấm bài tập về nhà. Chỉ cần NHẬN XÉT, không chấm điểm.
Yêu cầu nhận xét:
- ĐÚNG 2 câu ngắn, tiếng Việt, tự nhiên như người chấm thật.
- Không markdown, không gạch đầu dòng.
- Câu 1: nêu đúng/chưa đúng ý chính + 1 điểm mạnh nổi bật.
- Câu 2: nêu đúng 1 điểm cần sửa/thiếu quan trọng nhất (kèm gợi ý hành động).
- Tránh lan man; tổng độ dài 180–260 ký tự.
"""


def _img_to_data_url(raw: bytes, content_type: str) -> str:
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{content_type};base64,{b64}"


def _safe_filename(s: str) -> str:
    s = (s or "").strip() or "btvn"
    s = re.sub(r"[^\w\-.]+", "_", s, flags=re.UNICODE).strip("_")
    return s or "btvn"


@dataclass
class BtvnCommentParams:
    assignment_text: str
    assignment_images: list[tuple[str, bytes]]  # (content_type, bytes)
    submissions: list[str]
    model: str
    github_token: str = ""
    delay_s: float = 0.25


def _bundle_text(bundle: CollectedBundle | None) -> str:
    if not bundle or not bundle.files:
        return "(Không đọc được mã nguồn.)"
    return format_bundle_for_prompt(bundle)


def comment_one(
    *,
    assignment_text: str,
    assignment_images: list[tuple[str, bytes]],
    submission_ref: str,
    submission_bundle: CollectedBundle | None,
    model: str,
) -> str:
    parts: list[dict[str, Any]] = []
    parts.append(
        {
            "type": "text",
            "text": "ĐỀ BÀI (văn bản + ảnh nếu có):\n" + (assignment_text.strip() or "(trống)"),
        }
    )
    for ct, raw in assignment_images:
        parts.append({"type": "image_url", "image_url": {"url": _img_to_data_url(raw, ct)}})
    parts.append(
        {
            "type": "text",
            "text": "\n\nBÀI NỘP (repo): " + submission_ref.strip() + "\n\nMÃ NGUỒN:\n" + _bundle_text(submission_bundle),
        }
    )
    text, _ = complete_chat_raw(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": parts}],
        model=model,
        temperature=0.35,
        max_tokens=220,
        timeout_s=300.0,
    )
    return re.sub(r"\s+", " ", text).strip()


def run_btvn_comments_json(params: BtvnCommentParams) -> tuple[bool, str, list[dict[str, Any]] | None]:
    try:
        from cham_bai import settings

        settings.api_key()
    except RuntimeError as e:
        return False, str(e), None

    rows: list[dict[str, Any]] = []
    for ref in params.submissions:
        ref = (ref or "").strip()
        if not ref:
            continue
        gh = normalize_github_repo_url(ref)
        repo_err = ""
        bundle = None
        if gh:
            bundle, err = fetch_repo_sources_bundle(ref, github_token=(params.github_token or "").strip() or None)
            if err:
                repo_err = err
                bundle = None
        else:
            repo_err = "Chỉ hỗ trợ link GitHub (github.com / git@github.com)."

        comment = ""
        ai_err = ""
        if not repo_err:
            try:
                comment = comment_one(
                    assignment_text=params.assignment_text,
                    assignment_images=params.assignment_images,
                    submission_ref=gh or ref,
                    submission_bundle=bundle,
                    model=params.model,
                )
            except Exception as e:
                ai_err = str(e)[:800]
        rows.append(
            {
                "submission": ref,
                "repo": gh or "",
                "repo_error": repo_err,
                "comment": comment,
                "ai_error": ai_err,
            }
        )
        time.sleep(max(0.0, params.delay_s))
    return True, "", rows


# Backward compatible (nếu nơi khác vẫn gọi)
def run_btvn_comments(params: BtvnCommentParams) -> tuple[bool, str, Path | None]:
    ok, msg, rows = run_btvn_comments_json(params)
    if not ok or rows is None:
        return False, msg, None
    fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    out = Path(tmp_path)
    wb = Workbook()
    ws = wb.active
    ws.title = "BTVN"
    headers = ["submission", "repo", "repo_error", "comment", "ai_error"]
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        ws.cell(row=1, column=c).font = Font(bold=True)
    for r in rows:
        ws.append([r.get(h, "") for h in headers])
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 32
    ws.column_dimensions["D"].width = 70
    ws.column_dimensions["E"].width = 28
    wb.save(out)
    return True, "", out

