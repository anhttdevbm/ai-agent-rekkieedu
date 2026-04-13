"""
Kế hoạch cố định 45 câu cho «Quizz Session đầu giờ» (khớp UI phân bổ Đầu/Cuối + Dễ/TB/Khó).

- 30 câu đầu: BÀI CŨ (session trước); 15 câu sau: BÀI MỚI (session hiện tại).
- Mỗi khối 15 câu (1–15, 16–30, 31–45): đúng 5 Dễ + 5 Trung bình + 5 Khó (xen kẽ theo STT: 1,4,7… = Dễ; 2,5,8… = TB; 3,6,9… = Khó).
- Câu 1–15 — nhãn «Đầu»: Vận dụng chuyên sâu×4, Phân tích chuyên sâu×3, Sáng tạo×3, Thông hiểu×2, Vận dụng sơ bộ×2, Phân tích sơ bộ×1.
- Câu 16–30 — BÀI CŨ tiếp: Thông hiểu×5, Vận dụng sơ bộ×5, Phân tích sơ bộ×5.
- Câu 31–45 — nhãn «Cuối»: Sáng tạo×4, Vận dụng×6, Phân tích×5.

Quy ước cột difficulty (4–11), khớp hệ thống ngoài:
  4 Vận dụng chuyên sâu | 5 Phân tích chuyên sâu | 6 Sáng tạo | 7 Thông hiểu
  | 8 Vận dụng sơ bộ | 9 Phân tích sơ bộ | 10 Vận dụng | 11 Phân tích
"""

from __future__ import annotations

TIER_CYCLE_VI: tuple[str, ...] = ("Dễ", "Trung bình", "Khó")

# Mã difficulty (cột Excel / JSON): 4..11 — bắt buộc khớp quy ước LMS (không đổi thứ tự số).
DIFFICULTY_BY_COGNITIVE: dict[str, int] = {
    "van_dung_chuyen_sau": 4,
    "phan_tich_chuyen_sau": 5,
    "sang_tao": 6,
    "thong_hieu": 7,
    "van_dung_so_bo": 8,
    "phan_tich_so_bo": 9,
    "van_dung": 10,
    "phan_tich": 11,
}

# Thứ tự hiển thị legend / prompt: từ 4 lên 11.
DIFFICULTY_LEGEND_KEYS: tuple[str, ...] = (
    "van_dung_chuyen_sau",
    "phan_tich_chuyen_sau",
    "sang_tao",
    "thong_hieu",
    "van_dung_so_bo",
    "phan_tich_so_bo",
    "van_dung",
    "phan_tich",
)

COGNITIVE_LABEL_VI: dict[str, str] = {
    "thong_hieu": "Thông hiểu",
    "phan_tich_so_bo": "Phân tích sơ bộ",
    "van_dung_so_bo": "Vận dụng sơ bộ",
    "van_dung": "Vận dụng",
    "phan_tich": "Phân tích",
    "van_dung_chuyen_sau": "Vận dụng chuyên sâu",
    "phan_tich_chuyen_sau": "Phân tích chuyên sâu",
    "sang_tao": "Sáng tạo",
}


def _repeat(keys: list[str], counts: list[int]) -> list[str]:
    out: list[str] = []
    for k, n in zip(keys, counts, strict=True):
        out.extend([k] * n)
    return out


def _build_specs() -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []

    block1_cog = (
        _repeat(["van_dung_chuyen_sau", "phan_tich_chuyen_sau", "sang_tao", "thong_hieu", "van_dung_so_bo", "phan_tich_so_bo"], [4, 3, 3, 2, 2, 1])
    )
    for j, ck in enumerate(block1_cog):
        specs.append(
            {
                "index1": len(specs) + 1,
                "part": "prev",
                "category_vi": "BÀI CŨ",
                "tier_vi": TIER_CYCLE_VI[j % 3],
                "cognitive_key": ck,
                "cognitive_vi": COGNITIVE_LABEL_VI[ck],
                "difficulty": DIFFICULTY_BY_COGNITIVE[ck],
            }
        )

    block2_cog = _repeat(["thong_hieu", "van_dung_so_bo", "phan_tich_so_bo"], [5, 5, 5])
    for j, ck in enumerate(block2_cog):
        specs.append(
            {
                "index1": len(specs) + 1,
                "part": "prev",
                "category_vi": "BÀI CŨ",
                "tier_vi": TIER_CYCLE_VI[j % 3],
                "cognitive_key": ck,
                "cognitive_vi": COGNITIVE_LABEL_VI[ck],
                "difficulty": DIFFICULTY_BY_COGNITIVE[ck],
            }
        )

    block3_cog = _repeat(["sang_tao", "van_dung", "phan_tich"], [4, 6, 5])
    for j, ck in enumerate(block3_cog):
        specs.append(
            {
                "index1": len(specs) + 1,
                "part": "current",
                "category_vi": "BÀI MỚI",
                "tier_vi": TIER_CYCLE_VI[j % 3],
                "cognitive_key": ck,
                "cognitive_vi": COGNITIVE_LABEL_VI[ck],
                "difficulty": DIFFICULTY_BY_COGNITIVE[ck],
            }
        )

    assert len(specs) == 45
    return specs


SESSION_WARMUP_SPECS: list[dict[str, object]] = _build_specs()


def apply_session_warmup_plan(rows: list[dict[str, object]]) -> None:
    """Ghi đè difficulty theo kế hoạch cố định (bỏ qua giá trị model nếu lệch)."""
    if len(rows) != len(SESSION_WARMUP_SPECS):
        raise ValueError(f"Cần đúng {len(SESSION_WARMUP_SPECS)} câu, có {len(rows)}.")
    for i, row in enumerate(rows):
        row["difficulty"] = int(SESSION_WARMUP_SPECS[i]["difficulty"])


def session_warmup_difficulty_legend_vi() -> str:
    parts = [f"{DIFFICULTY_BY_COGNITIVE[k]} = {COGNITIVE_LABEL_VI[k]}" for k in DIFFICULTY_LEGEND_KEYS]
    return "; ".join(parts)


def session_warmup_spec_table_for_prompt(max_lines: int = 45) -> str:
    """Bảng STT cho user message (LLM)."""
    lines: list[str] = []
    n = min(max_lines, len(SESSION_WARMUP_SPECS))
    for i in range(n):
        s = SESSION_WARMUP_SPECS[i]
        lines.append(
            f"{s['index1']}. category={s['category_vi']} | độ khó diễn đạt={s['tier_vi']} | "
            f"mức nhận thức={s['cognitive_vi']} | difficulty(JSON/Excel)={s['difficulty']}"
        )
    return "\n".join(lines)


def session_warmup_distribution_summary_vi() -> str:
    """Mô tả ngắn cho UI (web/GUI)."""
    return (
        "45 câu: 30 BÀI CŨ + 15 BÀI MỚI. "
        "Mỗi khối 15 câu (1–15, 16–30, 31–45) có đúng 5 Dễ + 5 Trung bình + 5 Khó (theo STT). "
        "Câu 1–15 (cũ, Đầu): Vận dụng chuyên sâu×4, Phân tích chuyên sâu×3, Sáng tạo×3, Thông hiểu×2, Vận dụng sơ bộ×2, Phân tích sơ bộ×1. "
        "Câu 16–30 (cũ): Thông hiểu×5, Vận dụng sơ bộ×5, Phân tích sơ bộ×5. "
        "Câu 31–45 (mới, Cuối): Sáng tạo×4, Vận dụng×6, Phân tích×5. "
        f"Cột difficulty: {session_warmup_difficulty_legend_vi()}."
    )
