from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import io
import html as _html
from pathlib import Path

from docx import Document
from openpyxl import load_workbook

from cham_bai.openrouter import complete_chat_raw
from cham_bai.schemas import parse_llm_json


@dataclass
class GroupGradeParams:
    report_filename: str
    report_bytes: bytes
    video_transcript: str
    model: str


_SYSTEM = """Bạn là giảng viên chấm HOẠT ĐỘNG NHÓM.

Đầu vào gồm:
- BÁO CÁO (đã trích text từ file nhóm nộp)
- TRANSCRIPT / GHI CHÚ VIDEO (do người chấm cung cấp)

Nguyên tắc:
1) Tuyệt đối KHÔNG bịa nội dung video. Nếu transcript/ghi chú không đủ, phải ghi rõ trong kết quả.
2) Đánh giá 2 phần:
   - Hoạt động nhóm trong video: mức độ phối hợp, phân công, nhóm trưởng điều phối.
   - Báo cáo: nhóm trưởng có báo cáo đúng/đủ theo nội dung nhóm đã làm (đối chiếu theo ghi chú video nếu có).
3) Trong cuộc họp, nhóm trưởng phải thể hiện đủ các ý:
   - Công việc đã làm
   - Khó khăn gặp phải
   - Thành viên không tham gia hoặc không hoàn thành nhiệm vụ (nêu rõ và có bằng chứng từ transcript/báo cáo)
3) Ngôn ngữ: tiếng Việt, ngắn gọn, thực tế.

CHỈ trả về một JSON hợp lệ theo schema:
{
  "comment": "2-4 câu tiếng Việt, không bullet, không markdown",
  "video_evidence": "du" | "thieu",
  "leader_report_match": true|false|"khong_ro",
  "notes": "1-2 câu nếu thiếu dữ liệu video/report"
}
"""

def _strip_xml_tags(s: str) -> str:
    # keep only text nodes content (very basic)
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def _wb_to_text(xlsx_bytes: bytes, *, max_cells: int = 2500) -> str:
    wb = load_workbook(filename=io.BytesIO(xlsx_bytes), data_only=True)  # type: ignore[name-defined]
    parts: list[str] = []
    cells = 0
    for ws in wb.worksheets[:8]:
        parts.append(f"=== SHEET: {ws.title} ===")
        for row in ws.iter_rows(values_only=True):
            if cells >= max_cells:
                parts.append("[... TRUNCATED ...]")
                return "\n".join(parts).strip()
            vals = []
            for v in row:
                if v is None:
                    vals.append("")
                else:
                    s = str(v).strip()
                    vals.append(s)
            line = " | ".join(x for x in vals if x != "")
            if line.strip():
                parts.append(line)
            cells += 1
    return "\n".join(parts).strip()

def _extract_docx_plain_bytes(raw: bytes, *, max_chars: int = 28000) -> str:
    doc = Document(io.BytesIO(raw))
    parts: list[str] = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    text = "\n".join(parts).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 80] + " … [TRUNCATED]"
    return text


def report_file_bytes_to_text(filename: str, raw: bytes) -> tuple[str, list[str]]:
    warns: list[str] = []
    name = (filename or "").strip()
    ext = Path(name).suffix.lower()
    if ext == ".xlsx":
        try:
            return _wb_to_text(raw), warns
        except Exception as e:
            return "", [f"Lỗi đọc XLSX: {e}"]
    if ext == ".docx":
        try:
            return _extract_docx_plain_bytes(raw), warns
        except Exception as e:
            return "", [f"Lỗi đọc DOCX: {e}"]
    return "", [f"File báo cáo chưa hỗ trợ: {name or '(không tên)'} (chỉ nhận .docx hoặc .xlsx)"]


def grade_group_activity(params: GroupGradeParams) -> dict[str, Any]:
    report_text, warns = report_file_bytes_to_text(params.report_filename, params.report_bytes)
    video_notes = (params.video_transcript or "").strip()

    user_parts = [
        {
            "type": "text",
            "text": (
                "BÁO CÁO (text trích):\n"
                + (report_text.strip() or "(trống/không đọc được)")
                + "\n\nTRANSCRIPT / GHI CHÚ VIDEO:\n"
                + (video_notes or "(trống)")
                + ("\n\nCẢNH BÁO:\n" + "\n".join(warns) if warns else "")
            ),
        }
    ]

    text, _ = complete_chat_raw(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user_parts}],
        model=params.model,
        temperature=0.2,
        max_tokens=650,
        timeout_s=300.0,
    )
    try:
        blob = parse_llm_json(text)
        if isinstance(blob, dict):
            blob.setdefault("_fetch_warnings", warns)
            blob.setdefault("_transcript_chars", len(video_notes or ""))
            # Chuẩn hoá output: bỏ các field cũ nếu model lỡ trả.
            blob.pop("score", None)
            blob.pop("leader_activity_ok", None)
            return blob
    except Exception:
        try:
            # fallback: đôi khi provider trả hẳn dict ở dạng string Python-ish hoặc rác
            blob2 = json.loads((text or "").strip())
            if isinstance(blob2, dict):
                blob2.setdefault("_fetch_warnings", warns)
                blob2.setdefault("_transcript_chars", len(video_notes or ""))
                blob2.pop("score", None)
                blob2.pop("leader_activity_ok", None)
                return blob2
        except Exception:
            pass
    return {
        "comment": "Không chấm được do model không trả JSON hợp lệ.",
        "video_evidence": "thieu",
        "leader_report_match": "khong_ro",
        "notes": (text or "")[:1200],
        "_fetch_warnings": warns,
        "_transcript_chars": len(video_notes or ""),
    }

