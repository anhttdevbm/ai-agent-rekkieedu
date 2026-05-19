"""Quiz Session 02 cuối giờ — 45 câu toán tử & điều kiện (không kịch bản ship/đơn hàng)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from cham_bai.quiz_excel import (  # noqa: E402
    ensure_session_warmup_quiz_example_template,
    fill_template_session_warmup_quiz,
)
from cham_bai.quiz_gen import (  # noqa: E402
    _session_quiz_blob_has_fluff,
    _validate_session_quiz_block_forbidden_question_styles,
)
from cham_bai.session_end_plan import apply_session_end_plan  # noqa: E402
from session02_end_bank import build_session02_end_rows  # noqa: E402

_STORY_FLUFF = re.compile(
    r"\bNam\b|theo\s+kịch\s+bản|Shopee|phí\s+ship|giờ\s+vàng|đơn\s+hàng|"
    r"DA_HUY|miễn\s+phí|PLACEHOLDER|\d+k\b|sếp",
    re.I | re.UNICODE,
)


def build_rows() -> list[dict[str, object]]:
    rows = build_session02_end_rows()
    apply_session_end_plan(rows)
    return rows


def _validate(rows: list[dict[str, object]]) -> None:
    for i, r in enumerate(rows):
        blob = " ".join(
            str(r.get(k) or "")
            for k in (
                "question_content",
                "answer_1",
                "answer_2",
                "answer_3",
                "answer_4",
                "explanation_answer_1",
                "explanation_answer_2",
                "explanation_answer_3",
                "explanation_answer_4",
            )
        )
        if "PLACEHOLDER" in blob.upper():
            raise SystemExit(f"Câu {i + 1}: còn PLACEHOLDER")
        if _STORY_FLUFF.search(blob):
            raise SystemExit(f"Câu {i + 1}: kịch bản/fluff — {str(r.get('question_content'))[:70]}")
        hit = _session_quiz_blob_has_fluff(blob)
        if hit:
            raise SystemExit(f"Câu {i + 1}: fluff — {hit[0]}")


def main() -> None:
    rows = build_rows()
    _validate(rows)
    _validate_session_quiz_block_forbidden_question_styles(
        [{"question_content": r["question_content"]} for r in rows], [],
    )
    out = ROOT / "output" / "Quizz_Session02_Cuoi_Gio_da_sua.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    fill_template_session_warmup_quiz(ensure_session_warmup_quiz_example_template(), out, rows)
    print(f"Đã ghi {len(rows)} câu → {out}")


if __name__ == "__main__":
    main()
