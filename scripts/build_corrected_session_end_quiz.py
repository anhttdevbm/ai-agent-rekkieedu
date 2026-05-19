"""Tạo Excel quiz session cuối giờ (Session 01 intro) — cùng nội dung kỹ thuật L01–L06."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cham_bai.quiz_excel import (
    ensure_session_warmup_quiz_example_template,
    fill_template_session_warmup_quiz,
)
from cham_bai.quiz_gen import _session_quiz_blob_has_fluff, _validate_session_quiz_block_forbidden_question_styles
from cham_bai.session_end_plan import apply_session_end_plan

sys.path.insert(0, str(ROOT / "scripts"))
from build_corrected_session_warmup_quiz import _validate_intro_lesson_scope  # noqa: E402
from intro_lesson_end_bank import build_intro_lesson_end_rows  # noqa: E402


def build_rows() -> list[dict[str, object]]:
    rows = build_intro_lesson_end_rows()
    apply_session_end_plan(rows)
    return rows


def main() -> None:
    rows = build_rows()
    _validate_intro_lesson_scope(rows)
    for i, r in enumerate(rows):
        q = str(r["question_content"])
        hit = _session_quiz_blob_has_fluff(q)
        if hit:
            raise SystemExit(f"Câu {i + 1} vẫn fluff: {hit[0]} — {q[:80]}")
    _validate_session_quiz_block_forbidden_question_styles(
        [{"question_content": r["question_content"]} for r in rows],
        [],
    )

    out = ROOT / "output" / "Quizz_Session_Cuoi_Gio_Python_Intro_da_sua.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    tpl = ensure_session_warmup_quiz_example_template()
    fill_template_session_warmup_quiz(tpl, out, rows)
    print(f"Đã ghi {len(rows)} câu → {out}")


if __name__ == "__main__":
    main()
