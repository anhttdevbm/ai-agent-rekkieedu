from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cham_bai import __version__
from cham_bai.workflow import (
    GradeJobParams,
    batch_results_to_json,
    run_grade_batch,
    run_grade_job,
)


def _ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, OSError, ValueError):
            pass


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="agent-edu",
        description="Agent Edu — chấm bài: đề (.docx hoặc link Google Docs) + bài nộp → JSON (OpenRouter).",
    )
    p.add_argument(
        "--assignment",
        "--docx",
        dest="assignment",
        required=True,
        help="File .docx đề bài hoặc link Google Docs (https://docs.google.com/document/d/...)",
    )
    p.add_argument(
        "--submission",
        default="",
        help="Một bài nộp: thư mục hoặc link GitHub",
    )
    p.add_argument(
        "--submission-list",
        default="",
        metavar="FILE",
        help="File text: mỗi dòng một thư mục hoặc link GitHub (cùng một đề, chấm lô)",
    )
    p.add_argument(
        "--project-spec-repo",
        default="",
        metavar="URL",
        help="Tuỳ chọn: link GitHub repo đề / yêu cầu mini project (tham chiếu khi chấm)",
    )
    p.add_argument(
        "--report-repo",
        default="",
        metavar="URL",
        help="Tuỳ chọn: link GitHub repo báo cáo + mini project (mã nguồn + .docx, trích văn bản)",
    )
    p.add_argument(
        "--out",
        default="",
        help="Ghi JSON kết quả ra file (mặc định: in ra stdout)",
    )
    p.add_argument(
        "--model",
        default="",
        help="Model OpenRouter (mặc định từ OPENROUTER_MODEL hoặc claude-sonnet-4.6)",
    )
    p.add_argument(
        "--no-template",
        action="store_true",
        help="Không clone template GitHub từ link trong DOCX",
    )
    p.add_argument(
        "--strict-ai",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Nếu likely_ai và độ tin cậy đủ cao → 0 điểm, nhận xét 'dùng AI' (mặc định: bật)",
    )
    p.add_argument(
        "--ai-confidence",
        type=int,
        default=75,
        help="Ngưỡng integrity_confidence (0-100) để áp penalty khi likely_ai (mặc định: 75)",
    )
    p.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Giới hạn token output (mặc định: 4096)",
    )
    p.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Nhiệt độ sampling (mặc định: 0.2)",
    )
    p.add_argument("--version", action="store_true", help="In phiên bản và thoát")
    p.add_argument(
        "--debug",
        action="store_true",
        help="Ghi thêm raw_model_text và openrouter_response vào JSON (phúc tra)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    args = build_arg_parser().parse_args(argv)
    if args.version:
        print(__version__)
        return 0

    subs = _parse_submission_list(args)
    if not subs:
        print(
            "Cần --submission (một bài) hoặc --submission-list (file danh sách).",
            file=sys.stderr,
        )
        return 2

    params = GradeJobParams(
        assignment_ref=str(args.assignment),
        submission_ref=subs[0],
        out_path=Path(args.out) if (args.out or "").strip() else None,
        model=args.model,
        no_template=args.no_template,
        strict_ai=args.strict_ai,
        ai_confidence=max(0, min(100, args.ai_confidence)),
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        debug=args.debug,
        project_spec_repo_url=(args.project_spec_repo or "").strip(),
        report_repo_url=(args.report_repo or "").strip(),
    )

    if len(subs) == 1:
        res = run_grade_job(params)
        for w in res.warnings:
            print(f"Cảnh báo: {w}", file=sys.stderr)
        if not res.ok:
            print(res.error_message or "Lỗi không xác định.", file=sys.stderr)
            em = res.error_message or ""
            if "OpenRouter" in em or "Model không trả về JSON" in em:
                return 3
            return 2

        text = res.json_text or ""
        if params.out_path:
            print(str(res.written_path or params.out_path.resolve()))
        else:
            print(text)
        return 0

    batch = run_grade_batch(str(args.assignment), subs, params)
    for sub, res in batch:
        for w in res.warnings:
            print(f"[{sub}] Cảnh báo: {w}", file=sys.stderr)
        if not res.ok:
            print(f"[{sub}] Lỗi: {res.error_message}", file=sys.stderr)

    text = batch_results_to_json(str(args.assignment), batch)
    out_p = params.out_path
    if out_p:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(text, encoding="utf-8")
        print(str(out_p.resolve()))
    else:
        print(text)

    failed = sum(1 for _, r in batch if not r.ok)
    return 2 if failed else 0


def _parse_submission_list(args: argparse.Namespace) -> list[str]:
    lst = (getattr(args, "submission_list", None) or "").strip()
    if lst:
        p = Path(lst)
        if not p.is_file():
            print(f"Không tìm thấy file: {p}", file=sys.stderr)
            return []
        raw = p.read_text(encoding="utf-8")
        return [ln.strip() for ln in raw.splitlines() if ln.strip()]
    s = (args.submission or "").strip()
    return [s] if s else []


if __name__ == "__main__":
    raise SystemExit(main())
