from __future__ import annotations

import json
from typing import Any

from cham_bai.openrouter import complete_chat_raw
from cham_bai.schemas import parse_llm_json


_SYSTEM = """Bạn là giảng viên ra đề thi Hackathon (ĐỀ TỰ LUẬN) cho sinh viên.

Mục tiêu:
- Sinh đề đúng chuẩn form kiểu mẫu: có phần Yêu cầu (bullet), phần Thực hành chia PHẦN 1/2/3, có bảng mô tả cấu trúc bảng, bảng dữ liệu mẫu, và thang chấm điểm (bảng).
- Chủ đề và nội dung phải bám theo input của người dùng (môn/chủ đề/công nghệ/IDE/mã đề).
- Ngôn ngữ: tiếng Việt.

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
      "paragraphs": [],
      "bullets": ["...", "..."],
      "numbered": [],
      "tables": []
    },
    {
      "title": "Thực hành:",
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
"""


def generate_hackathon_exam_spec(
    *,
    model: str,
    header_top: str,
    header_sub: str,
    duration_minutes: int,
    topic: str,
    technology: str,
    ide: str,
    exam_code: str,
    extra_notes: str = "",
) -> dict[str, Any]:
    user = {
        "header_top": header_top,
        "header_sub": header_sub,
        "duration_minutes": duration_minutes,
        "topic": topic,
        "technology": technology,
        "ide": ide,
        "exam_code": exam_code,
        "extra_notes": extra_notes,
        "constraints": {
            "must_include_sections": ["Yêu cầu:", "Thực hành:", "PHẦN 1", "PHẦN 2", "PHẦN 3", "Thang chấm điểm"],
            "total_points": 100,
        },
    }

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
    )
    return parse_llm_json(text)

