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


_SYSTEM = """Bạn là giảng viên chấm bài tập về nhà. Chỉ xuất NHẬN XÉT cho học viên (sinh viên đọc trực tiếp), không chấm điểm.

Ngôn ngữ (bắt buộc):
- Toàn bộ nội dung xuất ra CHỈ là tiếng Việt. Cấm mọi câu tiếng Anh, cấm trích dẫn dài câu SQL/đề bằng tiếng Anh; nếu cần nhắc kỹ thuật thì diễn đạt bằng tiếng Việt (vd. “điều kiện OR”, “ngoặc đơn”, “độ ưu tiên AND/OR”).
- Cấm đoạn suy nghĩ dạo đầu: "Okay", "Let's", "The issue", "In SQL", "First", "I need", "That means", "The query", "The corrected query", v.v.
- Cấm giải thích từng bước như đang tự nhủ; không lặp lại toàn bộ đề hay dạy lý thuyết dài.

Cấu trúc nhận xét (bắt buộc, 2–3 câu liền mạch, giọng tự nhiên):
1) Câu mở: đánh giá mức độ bài làm đã đáp ứng yêu cầu đề — ưu tiên nêu **ý chính / nguyên nhân cốt lõi** mà sinh viên đã làm đúng (bám đề và mã thật; không bịa nếu bài không thể hiện).
2) Câu tiếp: **điểm mạnh nổi bật**, cụ thể kỹ thuật (vd. nhóm điều kiện đúng, cú pháp, cách sửa hợp lý…).
3) Câu cuối bắt đầu bằng “Tuy nhiên,” hoặc “Tuy nhiên cần lưu ý:”: một điểm còn thiếu theo đề + gợi ý hành động rõ ràng.

Bài SQL — sửa lỗi / phân tích độ ưu tiên AND–OR (khi đề hoặc mã liên quan):
- Câu mở **không** dừng ở “đúng logic lọc chung chung”; nếu bài nộp có phân tích hoặc sửa đúng, hãy nói thẳng **vì sao lệch** (vd. toán tử AND được ưu tiên trước OR nên nhóm điều kiện quận bị hiểu sai, khiến một khu vực không bị lọc theo điểm đánh giá như mong muốn) — diễn đạt bằng tiếng Việt, không lý thuyết dài.
- Điểm mạnh: nhấn mạnh **câu lệnh sau khi sửa** dùng **ngoặc đơn** nhóm phần OR rồi mới AND với điều kiện điểm (hoặc tương đương đúng) là **chuẩn xác**.
- Tuy nhiên: nếu trong repo **chỉ thấy bản đúng** mà đề yêu cầu phân tích lỗi / đối chiếu, gợi ý sinh viên **giữ hoặc thêm lại câu truy vấn sai ban đầu** (bản gốc lỗi) cạnh bản đã sửa để **minh họa trực quan** sự khác biệt trước và sau — giúp bài trình bày hoàn chỉnh hơn. Chỉ gợi ý khi thật sự phù hợp bài nộp.

Hình thức:
- Không markdown, không gạch đầu dòng, không đánh số (1. 2.).
- Độ dài khoảng 350–520 ký tự (đủ chi tiết nhưng không lan man). TỐI THIỂU 320 ký tự.
- Phong cách mục tiêu (SQL sửa lỗi ưu tiên AND/OR — chỉ bắt chước cấu trúc, nội dung theo bài thật): «Bài phân tích đúng nguyên nhân cốt lõi: … Điểm mạnh là câu đã sửa dùng ngoặc đơn … chuẩn xác. Tuy nhiên, nên bổ sung … (vd. câu truy vấn lỗi gốc để đối chiếu trước–sau) …»
"""

# Âm tiết có dấu — dùng để cắt phần tiếng Anh dạo đầu nếu model vẫn lẫn.
_VN_MARKED = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơớờởỡùúụủũưừứựửữỳýỵỷỹđ"
    r"ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]+"
)

# Đoạn mở kiểu giải thích SQL/lý thuyết bằng tiếng Anh (model hay lẫn trước nhận xét tiếng Việt).
_EN_HEAD_MARKERS = (
    "okay",
    "ok,",
    "ok.",
    "let's",
    "let ",
    "first,",
    "first ",
    "the user",
    "i need",
    "i'll",
    "we need",
    "to tackle",
    "let me",
    "the issue",
    "operator precedence",
    "in sql,",
    "in sql ",
    "that means",
    "the query is",
    "the query would",
    "the corrected query",
    "interpreted as",
    "higher precedence",
)


def _vietnamese_comment_only(raw: str) -> str:
    """Giữ phần nhận xét tiếng Việt; bỏ đoạn tiếng Anh / reasoning ở đầu nếu có."""
    s = re.sub(r"\s+", " ", (raw or "").strip())
    if not s:
        return s

    # 1) Nếu có các "mỏ neo" nhận xét tiếng Việt, ưu tiên cắt từ đó (tránh cắt nhầm ở chữ "Quận")
    anchors = (
        "Bài ",
        "Bài làm",
        "Bài phân tích",
        "Điểm mạnh",
        "Tuy nhiên",
        "Tuy nhiên,",
        "Tuy nhiên cần",
    )
    cut_at = -1
    for a in anchors:
        i = s.find(a)
        if i >= 0:
            cut_at = i if cut_at < 0 else min(cut_at, i)
    if cut_at >= 0:
        s = s[cut_at:].strip(" ,.;:\u2014-")
    else:
        # fallback: cắt từ chỗ có ký tự tiếng Việt có dấu (nhưng tránh cắt quá sớm)
        head = s[:520].lower()
        looks_en_meta = any(m in head for m in _EN_HEAD_MARKERS) or any(
            head.startswith(p) for p in _EN_HEAD_MARKERS[:12]
        )
        m_vn = _VN_MARKED.search(s)
        if m_vn and m_vn.start() > 0:
            if looks_en_meta or m_vn.start() > 60:
                s = s[m_vn.start() :].strip(" ,.;:\u2014-")

    # 2) Loại các câu rõ ràng là tiếng Anh / meta. Giữ lại 2–3 câu tiếng Việt.
    en_words = (
        " wait",
        " district",
        " interpreted",
        " precedence",
        " that means",
        " the query",
        " in sql",
        " select ",
        " where ",
        " rating ",
        " repo",
        " sample data",
        " should be",
        " incorrect",
        " correct",
        " looking back",
        " maybe",
        " let me",
        " i need",
        " the user",
    )
    sentences = re.split(r"(?<=[.!?])\s+", s)
    kept: list[str] = []
    for sent in sentences:
        t = sent.strip()
        if not t:
            continue
        low = " " + t.lower() + " "
        if any(w in low for w in en_words):
            continue
        # yêu cầu tiếng Việt: có ký tự có dấu hoặc bắt đầu bằng các anchor
        if _VN_MARKED.search(t) or any(t.startswith(a) for a in anchors):
            kept.append(t)
        if len(kept) >= 3:
            break

    out = " ".join(kept).strip()
    # Nếu cắt xong quá ngắn (thường do model trả 1 câu hoặc ta lọc quá tay),
    # ưu tiên trả về bản đã cắt anchor nhưng chưa lọc câu để giữ đủ ý.
    if out and (len(out) < 240 or len(kept) < 2):
        return s.strip()
    return out or s.strip()


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
    parts.append(
        {
            "type": "text",
            "text": (
                "\n\n---\nYÊU CẦU XUẤT (bắt buộc): Viết 2–3 câu tiếng Việt liền mạch: "
                "(1) nêu rõ sinh viên đã nắm đúng **gì cốt lõi** (vd. bài SQL sửa lỗi thì nói thẳng nguyên nhân do thứ tự ưu tiên AND/OR nếu bài thể hiện) → "
                "(2) điểm mạnh kỹ thuật cụ thể (vd. ngoặc đơn nhóm OR chuẩn) → "
                "(3) “Tuy nhiên,” + một gợi ý làm bài **hoàn chỉnh hơn** (vd. nếu chỉ có câu đúng mà đề cần phân tích lỗi: gợi ý thêm câu truy vấn sai gốc để đối chiếu trước–sau). "
                "Không tiếng Anh, không đoạn suy nghĩ đầu câu. Độ dài mục tiêu 350–520 ký tự, tối thiểu 320 ký tự."
            ),
        }
    )
    text, _ = complete_chat_raw(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": parts}],
        model=model,
        temperature=0.2,
        max_tokens=480,
        timeout_s=300.0,
    )
    return _vietnamese_comment_only(re.sub(r"\s+", " ", text).strip())


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

