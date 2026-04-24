from __future__ import annotations

import json
import re
from typing import Any

from cham_bai.openrouter import complete_chat_raw
from cham_bai.schemas import parse_llm_json


_SYSTEM = """Bạn là giảng viên ra đề thi Hackathon (ĐỀ TỰ LUẬN) cho sinh viên.

Mục tiêu:
- Sinh đề đúng chuẩn form kiểu mẫu: có phần Yêu cầu (bullet), phần Thực hành chia PHẦN 1/2/3, có bảng mô tả cấu trúc bảng, bảng dữ liệu mẫu, và thang chấm điểm (bảng).
- Chủ đề và nội dung phải bám theo input của người dùng (môn/chủ đề/công nghệ/IDE/mã đề).
- Ngôn ngữ: tiếng Việt.

GIỚI HẠN ĐỘ DÀI (để tránh lỗi JSON/cụt):
- Mỗi bảng cấu trúc (schema table): tối đa 8 dòng cột.
- Mỗi bảng dữ liệu mẫu: tối đa 6 dòng dữ liệu.
- Thang chấm điểm: đúng 6 dòng (1..6) và total=100.
- Không nhồi quá nhiều chữ trong 1 ô bảng (<= 80 ký tự/ô).

YÊU CẦU XUẤT:
- Chỉ output 1 JSON object hợp lệ (không markdown, không ```).
- JSON phải theo schema:
{
  "header_top": "KIỂM TRA ...",
  "header_sub": ".... - Đề 006",
  "duration_minutes": 120,
  "sections": [
    {
      "title": "Yêu cầu:",
      "lines": [],
      "paragraphs": [],
      "bullets": ["...", "..."],
      "numbered": [],
      "tables": []
    },
    {
      "title": "Thực hành:",
      "lines": [],
      "paragraphs": [],
      "bullets": [],
      "numbered": [],
      "tables": []
    }
  ],
  "rubric": {
    "rows": [
      { "q": "1", "content": "....", "points": 15 }
    ],
    "total": 100
  }
}

Quy tắc bảng:
- Mỗi table: { "title": "...", "headers": [...], "rows": [[...], ...] }
- Các ô là string; dùng "✅" nếu muốn.

RÀNG BUỘC BỐ CỤC (bắt buộc):
- Trong các section có bảng (đặc biệt PHẦN 1), hãy đặt bảng trong "tables" trước, và đặt các yêu cầu dạng câu hỏi trong "numbered" để hiển thị NGAY BÊN DƯỚI bảng.
- Ví dụ đúng (ý tưởng): sau các bảng cấu trúc, "numbered" phải có các dòng như:
  "Tạo bảng (15 điểm) ...",
  "Chèn dữ liệu (10 điểm) ...",
  và sau các bảng dữ liệu mẫu cũng có dòng yêu cầu tương ứng.

QUAN TRỌNG CHO PHẦN 2 / PHẦN 3:
- KHÔNG dùng dạng "2.1/2.2/3.1". Thay vào đó, TOÀN BỘ câu hỏi trong PHẦN 1/2/3 phải đánh số LIÊN TỤC:
  1., 2., 3., ... đến N (vd tổng 17 câu thì từ 1 đến 17), không reset theo phần.
- Các câu hỏi phải đưa vào field "lines" (mỗi dòng là 1 câu), và mỗi dòng phải bắt đầu bằng "k. " (k là số thứ tự).
- Không dùng list-number tự đánh số (vì Word có thể reset số).
- Với PHẦN 2 và PHẦN 3: "tables" phải để rỗng [] (chỉ văn bản).
"""


_REPAIR_SYSTEM = """Bạn đang sửa lỗi output.

YÊU CẦU XUẤT:
- Chỉ output 1 JSON object HỢP LỆ theo đúng schema đã nêu.
- Không markdown, không ``` , không giải thích, không chữ ngoài JSON.
- JSON phải bắt đầu bằng '{' và kết thúc bằng '}'.
- Tuyệt đối không thiếu dấu phẩy giữa các field/array item.
"""


def _extract_json_object_candidate(text: str) -> str:
    raw = (text or "").strip()
    # strip fenced blocks
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if m:
        raw = (m.group(1) or "").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return raw
    return raw[start : end + 1].strip()


def _fix_common_json_issues(s: str) -> str:
    t = (s or "").strip()
    if not t:
        return t
    # normalize smart quotes
    t = t.replace("“", '"').replace("”", '"').replace("’", "'").replace("–", "-")
    # remove trailing commas before } or ]
    t = re.sub(r",\s*([}\]])", r"\1", t)
    # remove null bytes/control chars
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", t)
    return t


def _parse_json_best_effort(text: str) -> dict[str, Any]:
    # 1) normal parser (handles ```json fences)
    try:
        return parse_llm_json(text)
    except Exception:
        pass
    # 2) extract + fix common issues
    cand = _extract_json_object_candidate(text)
    cand2 = _fix_common_json_issues(cand)
    return json.loads(cand2)


def generate_hackathon_exam_spec(
    *,
    model: str,
    header_top: str,
    header_sub: str,
    duration_minutes: int,
    subject: str,
    outline_text: str,
    technology: str,
    ide: str,
    exam_code: str,
    extra_notes: str = "",
) -> dict[str, Any]:
    outlines = [
        ln.strip()
        for ln in (outline_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not outlines:
        outlines = ["Tạo CSDL và các bảng", "Truy vấn dữ liệu cơ bản", "Truy vấn dữ liệu nâng cao"]

    # Fixed "Yêu cầu" block (must appear right after header)
    subj = (subject or "").strip() or "NHẬP MÔN CSDL MYSQL"
    code3 = (exam_code or "").strip() or "006"
    required_bullets = [
        "Tạo github repository theo cú pháp :  [Tên lớp]_[Họ Tên]_[Mã đề]",
        "Ví dụ: HN-K24-CNTT1_NguyenVanA_001",
        "Sau khi hoàn thành, đẩy code lên github repo và nộp link cho người phụ trách",
        f"Công nghệ sử dụng: {technology.strip() or 'MySQL'}",
        f"IDE : {ide.strip() or 'MySQL Workbench'}",
        "Thực hành bài trong script, lưu thành file tên hackathon.sql trong repository đã tạo ở trên.",
        "Lưu ý tuyệt đối không sử dụng Chat-GPT hay AI để làm bài, không copy bài người khác , nếu bị phát hiện sẽ lập biên bản và xử lý theo qui định.",
    ]

    user = {
        "header_top": header_top,
        "header_sub": header_sub,
        "duration_minutes": duration_minutes,
        "subject": subj,
        "outline": outlines,
        "technology": technology,
        "ide": ide,
        "exam_code": exam_code,
        "extra_notes": extra_notes,
        "required_section": {"title": "Yêu cầu:", "bullets": required_bullets},
        "constraints": {
            "must_include_sections": ["Yêu cầu:", "Thực hành:", "PHẦN 1", "PHẦN 2", "PHẦN 3", "Thang chấm điểm"],
            "total_points": 100,
        },
    }

    extra = {"response_format": {"type": "json_object"}}
    text, _ = complete_chat_raw(
        [
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": (
                    "Hãy sinh đề theo input JSON sau (bám sát, đầy đủ như mẫu). "
                    "Nếu là CSDL MySQL, hãy có tối thiểu 4 bảng + dữ liệu mẫu + câu update/delete + truy vấn cơ bản/nâng cao.\n\n"
                    + json.dumps(user, ensure_ascii=False)
                ),
            },
        ],
        model=model,
        temperature=0.35,
        max_tokens=3500,
        timeout_s=420.0,
        extra_body=extra,
    )
    try:
        return _parse_json_best_effort(text)
    except Exception as e1:
        # Repair pass 1: model đôi khi trả thiếu/cụt hoặc lẫn chữ.
        bad = (text or "").strip()
        tail = bad[-4500:] if len(bad) > 4500 else bad
        text2, _ = complete_chat_raw(
            [
                {"role": "system", "content": _REPAIR_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        "Output JSON trước bị lỗi hoặc không parse được. "
                        "Hãy output LẠI 1 JSON object hợp lệ theo schema, dựa trên input.\n\n"
                        "=== INPUT ===\n"
                        + json.dumps(user, ensure_ascii=False)
                        + "\n\n=== OUTPUT LỖI (trích) ===\n"
                        + tail
                    ),
                },
            ],
            model=model,
            temperature=0.15,
            max_tokens=3500,
            timeout_s=420.0,
            extra_body=extra,
        )
        try:
            return _parse_json_best_effort(text2)
        except Exception as e2:
            # Repair pass 2: gửi kèm lỗi decode để model sửa đúng vị trí
            err_msg = f"{type(e2).__name__}: {e2}"
            tail2 = (text2 or "").strip()
            tail2 = tail2[-4500:] if len(tail2) > 4500 else tail2
            text3, _ = complete_chat_raw(
                [
                    {"role": "system", "content": _REPAIR_SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            "JSON vẫn lỗi. Hãy sửa và output lại JSON hợp lệ theo schema.\n"
                            "Quan trọng: output chỉ 1 JSON object, không chữ thừa.\n\n"
                            f"Lỗi parse: {err_msg}\n\n"
                            "=== INPUT ===\n"
                            + json.dumps(user, ensure_ascii=False)
                            + "\n\n=== OUTPUT LỖI (trích) ===\n"
                            + tail2
                        ),
                    },
                ],
                model=model,
                temperature=0.05,
                max_tokens=3500,
                timeout_s=420.0,
                extra_body=extra,
            )
            return _parse_json_best_effort(text3)


def ensure_required_section(spec: dict[str, Any], *, required_bullets: list[str]) -> dict[str, Any]:
    """
    Ensure 'Yêu cầu:' section exists and contains required bullets.
    If missing, inject it as the first section.
    """
    if not isinstance(spec, dict):
        return spec
    secs = spec.get("sections")
    if not isinstance(secs, list):
        secs = []
    # find existing
    idx = None
    for i, s in enumerate(secs):
        if isinstance(s, dict) and str(s.get("title") or "").strip().lower().startswith("yêu cầu"):
            idx = i
            break
    block = {
        "title": "Yêu cầu:",
        "paragraphs": [],
        "bullets": required_bullets,
        "numbered": [],
        "tables": [],
    }
    if idx is None:
        secs = [block] + secs
    else:
        # merge bullets
        cur = secs[idx] if isinstance(secs[idx], dict) else {}
        cur_b = cur.get("bullets")
        if not isinstance(cur_b, list):
            cur_b = []
        # overwrite with required (stable)
        cur["title"] = "Yêu cầu:"
        cur["bullets"] = required_bullets
        cur.setdefault("paragraphs", [])
        cur.setdefault("numbered", [])
        cur.setdefault("tables", [])
        secs[idx] = cur
    spec["sections"] = secs
    return spec


def ensure_practice_section(spec: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure there is a 'Thực hành:' title before PHẦN 1/2/3.
    If missing, inject it right before the first section whose title starts with 'PHẦN'.
    """
    if not isinstance(spec, dict):
        return spec
    secs = spec.get("sections")
    if not isinstance(secs, list):
        secs = []

    def _is_practice(s: Any) -> bool:
        return isinstance(s, dict) and str(s.get("title") or "").strip().lower().startswith("thực hành")

    def _is_part(s: Any) -> bool:
        return isinstance(s, dict) and str(s.get("title") or "").strip().upper().startswith("PHẦN")

    if any(_is_practice(s) for s in secs):
        return spec

    insert_at = None
    for i, s in enumerate(secs):
        if _is_part(s):
            insert_at = i
            break
    block = {"title": "Thực hành:", "paragraphs": [], "bullets": [], "numbered": [], "tables": []}
    if insert_at is None:
        secs.append(block)
    else:
        secs.insert(insert_at, block)
    spec["sections"] = secs
    return spec

