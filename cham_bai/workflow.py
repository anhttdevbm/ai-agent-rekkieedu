from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path

from cham_bai.assignment import load_assignment
from cham_bai.collector import CollectedBundle, collect_sources
from cham_bai.docx_reader import DocxContent
from cham_bai.gdocs_reader import is_google_docs_url
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
    """Trả về (bundle, lỗi, cảnh báo)."""
    warnings: list[str] = []
    ref = submission_ref.strip()
    if not ref:
        return None, "Chưa chỉ định thư mục hoặc link GitHub bài nộp.", warnings

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


def _aligned_report_repo_urls(
    submission_count: int,
    report_repos_text: str,
) -> tuple[list[str], list[str]]:
    """Mỗi chỉ số i tương ứng submission thứ i (0-based)."""
    raw = (report_repos_text or "").splitlines()
    out = [raw[i].strip() if i < len(raw) else "" for i in range(submission_count)]
    warns: list[str] = []
    nonempty = sum(1 for ln in raw if ln.strip())
    if len(raw) > submission_count:
        warns.append(
            f"Số dòng link repo báo cáo ({len(raw)}) > số bài nộp ({submission_count}); chỉ dùng {submission_count} dòng đầu."
        )
    if submission_count > 1 and nonempty and len(raw) < submission_count:
        warns.append(
            f"Số dòng link repo báo cáo ({len(raw)}) < số bài nộp ({submission_count}); các bài thiếu dòng coi như không có repo."
        )
    return out, warns


def _load_optional_github_bundle(
    url: str,
    *,
    label_vi: str,
) -> tuple[CollectedBundle | None, list[str]]:
    s = (url or "").strip()
    if not s:
        return None, []
    if not normalize_github_repo_url(s):
        return None, [f"{label_vi}: không phải link GitHub hợp lệ — bỏ qua."]
    docx_w: list[str] = []
    bundle, err = fetch_repo_sources_bundle(
        s,
        github_token=_github_token_for_fetch(),
        include_docx_text=True,
        docx_out_warnings=docx_w,
    )
    warns: list[str] = []
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

    if not submission.files:
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
    """
    subs = [s.strip() for s in submission_refs if s.strip()]
    if not subs:
        return [("", GradeJobResult(ok=False, error_message="Danh sách bài nộp trống."))]

    doc, template_bundle, template_error, prep_w, err = _prepare_assignment(
        assignment_ref, params.no_template
    )
    if err:
        return [(subs[0], GradeJobResult(ok=False, error_message=err))]

    assert doc is not None

    report_urls, align_warns = _aligned_report_repo_urls(len(subs), params.report_repos_text)

    report_bundle_cache: dict[str, tuple[CollectedBundle | None, list[str]]] = {}

    def _report_bundle_for_url(url: str) -> tuple[CollectedBundle | None, list[str]]:
        key = (url or "").strip()
        if not key:
            return None, []
        if key in report_bundle_cache:
            return report_bundle_cache[key]
        b, w = _load_optional_github_bundle(
            key,
            label_vi="Repo báo cáo + mini project",
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
        out.append((submission_ref, r))
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
