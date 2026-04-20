from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path

from cham_bai.assignment import load_assignment
from cham_bai.collector import CollectedBundle, collect_sources
from cham_bai.docx_reader import DocxContent
from cham_bai.gdocs_reader import is_google_docs_url
from cham_bai.gdocs_reader import fetch_google_doc_plain_text, is_google_docs_url
from cham_bai.git_remote import fetch_repo_sources_bundle, normalize_github_repo_url
from cham_bai.github_template import fetch_template_bundle
from cham_bai.grader import dump_outcome_json, grade_submission
from cham_bai.settings import model as resolve_model


@dataclass
class GradeJobParams:
    """assignment_ref: file .docx hoặc link Google Docs; submission_ref: thư mục hoặc GitHub."""

    assignment_ref: str
    submission_ref: str
    out_path: Path | None = None
    model: str = ""
    no_template: bool = False
    strict_ai: bool = True
    ai_confidence: int = 75
    max_tokens: int = 4096
    temperature: float = 0.2
    debug: bool = False
    # Nhiều dòng: dòng i khớp bài nộp dòng i (chấm lô). Dòng trống = không có repo báo cáo cho bài đó.
    report_repos_text: str = ""


@dataclass
class GradeJobResult:
    ok: bool
    json_text: str | None = None
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)
    written_path: Path | None = None


def _load_submission_bundle(
    submission_ref: str,
) -> tuple[CollectedBundle | None, str | None, list[str]]:
    """Trả về (bundle, lỗi, cảnh báo). Chuỗi rỗng = không bài tập đầu giờ (bundle rỗng, dùng khi chỉ chấm repo báo cáo)."""
    warnings: list[str] = []
    ref = submission_ref.strip()
    if not ref:
        warnings.append(
            "Bài tập đầu giờ trống — chỉ chấm theo repo báo cáo + mini (nếu có) cho dòng này."
        )
        return CollectedBundle(root=Path(".").resolve(), files=[]), None, warnings

    local = Path(ref)
    gh = normalize_github_repo_url(ref)

    if local.is_dir():
        try:
            return collect_sources(local), None, warnings
        except Exception as e:
            return None, f"Lỗi đọc thư mục nộp bài: {e}", warnings

    if gh:
        bundle, err = fetch_repo_sources_bundle(ref)
        if err:
            return None, err, warnings
        warnings.append(f"Đã tải bài nộp từ GitHub: {gh}")
        return bundle, None, warnings

    return (
        None,
        f"Không phải thư mục hợp lệ hoặc link GitHub hợp lệ: {ref}",
        warnings,
    )


def _github_token_for_fetch() -> str | None:
    t = (os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or "").strip()
    return t or None


def grade_row_label(submission_ref: str, report_url: str, row_index: int) -> str:
    """Nhãn log/JSON khi bài nộp trống nhưng vẫn có dòng chấm (repo báo cáo)."""
    s = (submission_ref or "").strip()
    r = (report_url or "").strip()
    if s:
        return s
    if r:
        return f"(chỉ repo báo cáo) {r}"
    return f"(dòng {row_index + 1} trống)"


def _normalize_parallel_submissions_and_reports(
    submission_refs: list[str],
    report_repos_text: str,
) -> tuple[list[str], list[str], list[str]]:
    """
    Cùng số dòng sau khi pad; bỏ các cặp trống ở cuối.
    Cho phép dòng i chỉ có repo báo cáo (bài nộp i trống).
    """
    sl = [(str(x) if x is not None else "").strip() for x in (submission_refs or [])]
    rl = [(ln.rstrip("\r") or "").strip() for ln in (report_repos_text or "").splitlines()]
    n = max(len(sl), len(rl))
    sl = sl + [""] * (n - len(sl))
    rl = rl + [""] * (n - len(rl))
    while n > 0 and not sl[n - 1] and not rl[n - 1]:
        n -= 1
    sl, rl = sl[:n], rl[:n]
    return sl, rl, []


def has_grade_slots(submission_refs: list[str], report_repos_text: str) -> bool:
    """Có ít nhất một dòng chấm (bài nộp hoặc repo báo cáo hoặc cả hai)."""
    s, _, _ = _normalize_parallel_submissions_and_reports(
        submission_refs,
        report_repos_text,
    )
    return bool(s)


def normalized_grade_rows(
    submission_refs: list[str],
    report_repos_text: str,
) -> tuple[list[str], list[str], list[str]]:
    """Cặp (bài nộp, repo) đã pad và bỏ dòng trống cuối — dùng GUI/CLI nếu cần."""
    return _normalize_parallel_submissions_and_reports(
        submission_refs,
        report_repos_text,
    )


def is_valid_report_source_url(url: str) -> bool:
    """Báo cáo: GitHub repo hoặc link Google Docs (bài chỉ nộp Docs)."""
    s = (url or "").strip()
    if not s:
        return False
    return bool(normalize_github_repo_url(s)) or is_google_docs_url(s)


def _load_optional_report_bundle(
    url: str,
    *,
    label_vi: str,
) -> tuple[CollectedBundle | None, list[str]]:
    s = (url or "").strip()
    if not s:
        return None, []
    warns: list[str] = []

    if is_google_docs_url(s):
        try:
            plain = fetch_google_doc_plain_text(s)
        except Exception as e:
            warns.append(f"{label_vi} (Google Docs): {e}")
            return None, warns
        bundle = CollectedBundle(
            root=Path("(google-docs-báo-cáo)"),
            files=[("_gdocs_baocao/export.txt", plain)],
        )
        warns.append(f"Đã tải {label_vi} từ Google Docs (văn bản export).")
        return bundle, warns

    if not normalize_github_repo_url(s):
        warns.append(
            f"{label_vi}: cần link GitHub hoặc Google Docs (https://docs.google.com/document/d/...)."
        )
        return None, warns

    docx_w: list[str] = []
    bundle, err = fetch_repo_sources_bundle(
        s,
        github_token=_github_token_for_fetch(),
        include_docx_text=True,
        docx_out_warnings=docx_w,
    )
    norm = normalize_github_repo_url(s)
    if err or bundle is None:
        warns.append(f"{label_vi}: {err or 'Không tải được repo.'}")
        return None, warns
    warns.append(f"Đã tải {label_vi}: {norm}")
    for w in docx_w:
        warns.append(f"{label_vi} (DOCX): {w}")
    return bundle, warns


def _prepare_assignment(
    assignment_ref: str, no_template: bool
) -> tuple[
    DocxContent | None,
    CollectedBundle | None,
    str | None,
    list[str],
    str | None,
]:
    """
    Tải đề + template một lần.
    Trả về (doc, template_bundle, template_error, warnings, lỗi_chuỗi).
    Nếu lỗi_chuỗi khác None thì doc là None.
    """
    warnings: list[str] = []
    try:
        doc = load_assignment(assignment_ref)
    except ValueError as e:
        return None, None, None, [], str(e)
    except RuntimeError as e:
        return None, None, None, [], str(e)
    except Exception as e:
        return None, None, None, [], f"Lỗi đọc đề bài: {e}"

    if is_google_docs_url(assignment_ref):
        warnings.append(
            "Đề lấy từ Google Docs; tài liệu cần chia sẻ 'Bất kỳ ai có liên kết' (có thể xem)."
        )

    template_bundle = None
    template_error: str | None = None
    if not no_template and doc.github_repo_urls:
        url = doc.github_repo_urls[0]
        template_bundle, template_error = fetch_template_bundle(url)
        if template_error and template_bundle is None:
            warnings.append(f"Template: {template_error}")
    elif not no_template and not doc.github_repo_urls:
        template_error = "Đề không chứa link GitHub repo để làm template."

    return doc, template_bundle, template_error, warnings, None


def _grade_single_from_prepared(
    doc: DocxContent,
    template_bundle: CollectedBundle | None,
    template_error: str | None,
    submission_ref: str,
    params: GradeJobParams,
    prep_warnings: list[str],
    *,
    report_bundle: CollectedBundle | None = None,
) -> GradeJobResult:
    warnings = list(prep_warnings)
    submission, submission_error, sub_warns = _load_submission_bundle(submission_ref)
    warnings.extend(sub_warns)
    if submission_error or submission is None:
        return GradeJobResult(
            ok=False,
            error_message=submission_error or "Không đọc được bài nộp.",
            warnings=warnings,
        )

    ref_nonempty = bool((submission_ref or "").strip())
    if not submission.files and report_bundle is None:
        return GradeJobResult(
            ok=False,
            error_message="Thiếu cả bài tập đầu giờ (bài nộp) và repo báo cáo — không có gì để chấm.",
            warnings=warnings,
        )
    if not submission.files and ref_nonempty:
        warnings.append(
            "Không thu thập được file mã nguồn nào từ bài nộp (thư mục rỗng hoặc repo không có file phù hợp)."
        )

    try:
        m = resolve_model(params.model or None)
        outcome = grade_submission(
            doc,
            submission,
            template_bundle,
            model=m,
            template_error=template_error,
            strict_ai_penalty=params.strict_ai,
            ai_penalty_min_confidence=max(0, min(100, params.ai_confidence)),
            temperature=params.temperature,
            max_tokens=params.max_tokens,
            report_bundle=report_bundle,
        )
    except RuntimeError as e:
        return GradeJobResult(ok=False, error_message=str(e), warnings=warnings)
    except Exception as e:
        return GradeJobResult(
            ok=False,
            error_message=f"Lỗi khi gọi OpenRouter: {e}",
            warnings=warnings,
        )

    text = dump_outcome_json(outcome, include_raw=params.debug)
    written: Path | None = None
    if params.out_path:
        params.out_path.parent.mkdir(parents=True, exist_ok=True)
        params.out_path.write_text(text, encoding="utf-8")
        written = params.out_path.resolve()

    return GradeJobResult(
        ok=True,
        json_text=text,
        warnings=warnings,
        written_path=written,
    )


def run_grade_batch(
    assignment_ref: str,
    submission_refs: list[str],
    params: GradeJobParams,
    *,
    attach_prep_warnings_to_first_only: bool = True,
) -> list[tuple[str, GradeJobResult]]:
    """
    Cùng một đề, chấm nhiều bài nộp. Đề và template tải một lần.
    Repo báo cáo (tuỳ chọn): `params.report_repos_text` — nhiều dòng, dòng i khớp bài nộp thứ i.
    Một dòng có thể chỉ có repo báo cáo (bài nộp trống) hoặc chỉ bài nộp (repo trống).
    """
    subs, report_urls, align_warns = _normalize_parallel_submissions_and_reports(
        submission_refs,
        params.report_repos_text,
    )
    if not subs:
        return [
            (
                "",
                GradeJobResult(
                    ok=False,
                    error_message="Thiếu dữ liệu — cần ít nhất một dòng có bài nộp hoặc link repo báo cáo.",
                ),
            )
        ]

    doc, template_bundle, template_error, prep_w, err = _prepare_assignment(
        assignment_ref, params.no_template
    )
    if err:
        lab0 = grade_row_label(subs[0], report_urls[0] if report_urls else "", 0)
        return [(lab0, GradeJobResult(ok=False, error_message=err))]

    assert doc is not None

    report_bundle_cache: dict[str, tuple[CollectedBundle | None, list[str]]] = {}

    def _report_bundle_for_url(url: str) -> tuple[CollectedBundle | None, list[str]]:
        key = (url or "").strip()
        if not key:
            return None, []
        if key in report_bundle_cache:
            return report_bundle_cache[key]
        b, w = _load_optional_report_bundle(
            key,
            label_vi="Báo cáo (GitHub / Google Docs)",
        )
        report_bundle_cache[key] = (b, w)
        return b, w

    p_inner = replace(params, out_path=None) if len(subs) > 1 else params
    out: list[tuple[str, GradeJobResult]] = []
    for i, submission_ref in enumerate(subs):
        pw: list[str] = []
        if i == 0 or not attach_prep_warnings_to_first_only:
            pw.extend(prep_w)
            pw.extend(align_warns)
        rep_u = report_urls[i] if i < len(report_urls) else ""
        rb, rb_warns = _report_bundle_for_url(rep_u)
        pw.extend(rb_warns)
        r = _grade_single_from_prepared(
            doc,
            template_bundle,
            template_error,
            submission_ref,
            p_inner,
            pw,
            report_bundle=rb,
        )
        out.append((grade_row_label(submission_ref, rep_u, i), r))
    return out


def run_grade_job(params: GradeJobParams) -> GradeJobResult:
    """Một bài nộp (tương thích cũ)."""
    batch = run_grade_batch(
        params.assignment_ref,
        [params.submission_ref],
        params,
        attach_prep_warnings_to_first_only=True,
    )
    return batch[0][1]


def batch_results_to_json(
    assignment_ref: str,
    results: list[tuple[str, GradeJobResult]],
) -> str:
    """JSON mảng: mỗi phần tử có submission + các trường kết quả parse từ json_text."""
    items: list[dict] = []
    for sub, res in results:
        row: dict = {"submission": sub, "ok": res.ok}
        if res.error_message:
            row["error"] = res.error_message
        if res.warnings:
            row["warnings"] = res.warnings
        if res.json_text:
            try:
                row["result"] = json.loads(res.json_text)
            except json.JSONDecodeError:
                row["result_raw"] = res.json_text
        items.append(row)
    return json.dumps(
        {"assignment": assignment_ref, "count": len(items), "results": items},
        ensure_ascii=False,
        indent=2,
    )
