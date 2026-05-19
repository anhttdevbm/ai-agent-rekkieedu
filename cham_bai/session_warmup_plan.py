"""
Kế hoạch cố định 45 câu cho «Quizz Session đầu giờ».

Yêu cầu hiện tại:
- Chỉ dùng 6 mức difficulty: 4, 5, 6, 7, 8, 9
  4 Vận dụng chuyên sâu | 5 Phân tích chuyên sâu | 6 Sáng tạo | 7 Thông hiểu
  | 8 Vận dụng sơ bộ | 9 Phân tích sơ bộ
- 45 câu chia đều theo 6 mức difficulty:
  mỗi mức 7 câu, còn dư 3 câu → cộng thêm 1 câu cho 3 mức đầu theo thứ tự legend.

Ghi chú: vẫn giữ nhãn 30 câu «BÀI CŨ» + 15 câu «BÀI MỚI» và vòng Dễ/TB/Khó theo STT để dễ nhìn,
nhưng difficulty được áp theo phân bổ đều ở trên.
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
}

# Thứ tự hiển thị legend / prompt: theo yêu cầu (6 mức).
DIFFICULTY_LEGEND_KEYS: tuple[str, ...] = (
    "van_dung_chuyen_sau",
    "phan_tich_chuyen_sau",
    "sang_tao",
    "thong_hieu",
    "van_dung_so_bo",
    "phan_tich_so_bo",
)

COGNITIVE_LABEL_VI: dict[str, str] = {
    "thong_hieu": "Thông hiểu",
    "phan_tich_so_bo": "Phân tích sơ bộ",
    "van_dung_so_bo": "Vận dụng sơ bộ",
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

    # Chia đều 45 câu theo 6 mức cognitive_key (7 câu/mức, dư 3 câu cho 3 mức đầu theo legend).
    keys = list(DIFFICULTY_LEGEND_KEYS)
    base = 45 // len(keys)  # 7
    rem = 45 % len(keys)   # 3
    pool: list[str] = []
    for i, k in enumerate(keys):
        pool.extend([k] * (base + (1 if i < rem else 0)))

    # Trộn đơn giản theo vòng để không dồn cùng loại vào một đoạn.
    # (Không random để luôn tái lập.)
    ordered: list[str] = []
    buckets: dict[str, int] = {k: pool.count(k) for k in keys}
    idx = 0
    while len(ordered) < 45:
        k = keys[idx % len(keys)]
        if buckets.get(k, 0) > 0:
            ordered.append(k)
            buckets[k] -= 1
        idx += 1

    for j, ck in enumerate(ordered):
        specs.append(
            {
                "index1": len(specs) + 1,
                "part": ("prev" if (len(specs) < 30) else "current"),
                "category_vi": ("BÀI CŨ" if (len(specs) < 30) else "BÀI MỚI"),
                "tier_vi": TIER_CYCLE_VI[j % 3],
                "cognitive_key": ck,
                "cognitive_vi": COGNITIVE_LABEL_VI[ck],
                "difficulty": DIFFICULTY_BY_COGNITIVE[ck],
            }
        )

    assert len(specs) == 45
    return specs


SESSION_WARMUP_SPECS: list[dict[str, object]] = _build_specs()


def apply_session_warmup_plan(rows: list[dict[str, object]], *, prev_count: int | None = None) -> None:
    """Ghi đè difficulty/category; hỗ trợ 15–45 câu (không bắt buộc đủ 45)."""
    n = len(rows)
    if n < 12:
        raise ValueError(f"Cần ít nhất 12 câu, có {n}.")
    if n > len(SESSION_WARMUP_SPECS):
        raise ValueError(f"Tối đa {len(SESSION_WARMUP_SPECS)} câu, có {n}.")
    pc = int(prev_count) if prev_count is not None else min(30, (n * 2 + 1) // 3)
    pc = max(0, min(n, pc))
    for i, row in enumerate(rows):
        spec = SESSION_WARMUP_SPECS[min(i, len(SESSION_WARMUP_SPECS) - 1)]
        row["difficulty"] = int(spec["difficulty"])
        row["category"] = "BÀI CŨ" if i < pc else "BÀI MỚI"


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
        "Tối đa 45 câu (thường 15–45 tùy lượng tài liệu): ~2/3 BÀI CŨ + phần còn BÀI MỚI. "
        "Không cố đủ 45 nếu kiến thức mỏng. "
        "Difficulty chỉ dùng 6 mức: 4/5/6/7/8/9. "
        f"Cột difficulty: {session_warmup_difficulty_legend_vi()}."
    )
