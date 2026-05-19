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
    """Ghi đè part/category/difficulty; hỗ trợ 15–45 câu."""
    n = len(rows)
    if n < 12:
        raise ValueError(f"Cần ít nhất 12 câu, có {n}.")
    if n > len(SESSION_END_SPECS):
        raise ValueError(f"Tối đa {len(SESSION_END_SPECS)} câu, có {n}.")
    for i, row in enumerate(rows):
        row["part"] = "current"
        row["difficulty"] = int(SESSION_END_DIFFICULTIES[i % len(SESSION_END_DIFFICULTIES)])
        row["category"] = "BÀI MỚI"


def session_end_distribution_summary_vi() -> str:
    return (
        "Tối đa 45 câu session hiện tại (thường 15–45 tùy tài liệu). "
        "Difficulty luân phiên: 6 Sáng tạo / 10 Vận dụng / 11 Phân tích."
    )

