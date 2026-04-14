"""
Kế hoạch 45 câu cho «Quizz Session cuối giờ».

Yêu cầu:
- Chỉ dùng 3 độ khó:
  - 6  Sáng tạo
  - 10 Vận dụng
  - 11 Phân tích
- Chia đều: 45 câu = 15 câu mỗi độ khó.
- Nội dung chỉ lấy của session hiện tại (tương ứng part='current').
"""

from __future__ import annotations


DIFFICULTY_LABEL_VI: dict[int, str] = {
    6: "Sáng tạo",
    10: "Vận dụng",
    11: "Phân tích",
}


SESSION_END_DIFFICULTIES: tuple[int, ...] = (6, 10, 11)


def _build_specs() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    # deterministic interleave: 6,10,11,6,10,11,... (15 vòng)
    for i in range(45):
        d = SESSION_END_DIFFICULTIES[i % len(SESSION_END_DIFFICULTIES)]
        out.append(
            {
                "index1": i + 1,
                "part": "current",
                "category_vi": "BÀI MỚI",
                "difficulty": d,
                "difficulty_vi": DIFFICULTY_LABEL_VI[d],
            }
        )
    assert len(out) == 45
    return out


SESSION_END_SPECS: list[dict[str, object]] = _build_specs()


def apply_session_end_plan(rows: list[dict[str, object]]) -> None:
    """Ghi đè part/category/difficulty theo plan cuối giờ (bỏ qua giá trị model nếu lệch)."""
    if len(rows) != len(SESSION_END_SPECS):
        raise ValueError(f"Cần đúng {len(SESSION_END_SPECS)} câu, có {len(rows)}.")
    for i, row in enumerate(rows):
        s = SESSION_END_SPECS[i]
        row["part"] = "current"
        row["difficulty"] = int(s["difficulty"])
        row["category"] = str(s["category_vi"])


def session_end_distribution_summary_vi() -> str:
    return "45 câu (session hiện tại). Difficulty chia đều: 6 Sáng tạo ×15; 10 Vận dụng ×15; 11 Phân tích ×15."

