from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cham_bai.cli import _ensure_utf8_stdio
from cham_bai.quiz_gen import (
    QuizGenParams,
    QUIZ_KIND_SESSION_WARMUP,
    default_quiz_output_path,
    default_session_warmup_quiz_output_path,
    normalize_quiz_kind,
    run_quiz_generation,
)


def main() -> int:
    _ensure_utf8_stdio()
    p = argparse.ArgumentParser(
        prog="agent-edu-quiz",
        description="Tạo file Excel quiz đầu giờ từ mẫu + OpenRouter.",
    )
    p.add_argument("--template", required=True, help="File .xlsx mẫu (hàng 1 = tiêu đề cột)")
    p.add_argument(
        "--out",
        default="",
        help="File .xlsx đầu ra. Bỏ trống = tự tạo tên trong thư mục của --template "
        "(session_warmup: quizz_session_Dau_gio_<session-current>_<timestamp>.xlsx; khác: quiz_<lesson>_<session>_<timestamp>.xlsx).",
    )
    p.add_argument("--lesson", default="", help="Tên lesson (bắt buộc nếu kind=lesson hoặc kind=session)")
    p.add_argument("--session", default="", help="Tên session (bắt buộc nếu kind=lesson hoặc kind=session)")
    p.add_argument("--subject", default="", help="Môn học / lĩnh vực (tuỳ chọn — đưa vào prompt AI)")
    p.add_argument("--session-prev", default="", help="Session trước (tuỳ chọn — chỉ dùng cho kind=session_warmup)")
    p.add_argument("--session-current", default="", help="Session hiện tại (tuỳ chọn — chỉ dùng cho kind=session_warmup)")
    p.add_argument("--docx", default="", help="DOCX bài giảng (tuỳ chọn)")
    p.add_argument(
        "--num",
        type=int,
        default=10,
        help="Số câu (1–50). Với mẫu 7 cột (Các đáp án / Kết quả / Giải thích) luôn 5 câu — tham số này bị bỏ qua.",
    )
    p.add_argument("--model", default="", help="Model OpenRouter")
    p.add_argument(
        "--kind",
        default="session",
        choices=("session", "lesson", "session_warmup"),
        help="session = quiz theo session; session_warmup = quizz session đầu giờ (có session trước/hiện tại); lesson = ôn tập theo lesson",
    )
    args = p.parse_args()

    template_path = Path(args.template)
    out = (args.out or "").strip()
    qkind = normalize_quiz_kind(args.kind)
    lesson = (args.lesson or "").strip()
    session = (args.session or "").strip()
    subject = (args.subject or "").strip()
    session_prev = (args.session_prev or "").strip()
    session_current = (args.session_current or "").strip()
    if qkind == QUIZ_KIND_SESSION_WARMUP:
        if not subject or not session_current:
            print("Thiếu --subject hoặc --session-current cho kind=session_warmup.", file=sys.stderr)
            return 2
        lesson = subject
        session = session_current
    else:
        if not lesson or not session:
            print("Thiếu --lesson hoặc --session.", file=sys.stderr)
            return 2

    if out:
        out_path = Path(out)
    elif qkind == QUIZ_KIND_SESSION_WARMUP:
        out_path = default_session_warmup_quiz_output_path(template_path, session_current)
    else:
        out_path = default_quiz_output_path(template_path, lesson, session)

    params = QuizGenParams(
        template_xlsx=template_path,
        docx_path=Path(args.docx) if (args.docx or "").strip() else None,
        lesson=lesson,
        session=session,
        num_questions=max(1, min(50, args.num)),
        model=args.model,
        output_xlsx=out_path,
        subject=subject,
        session_prev=session_prev,
        session_current=session_current,
        quiz_kind=qkind,
    )
    ok, msg = run_quiz_generation(params)
    if ok:
        print(msg)
        return 0
    print(msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
