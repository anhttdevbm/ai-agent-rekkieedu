"""
Giao diện web (FastAPI) cho Agent Edu — chạy local, tái dùng logic GUI.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from cham_bai import __version__
from cham_bai.gdocs_reader import is_google_docs_url
from cham_bai.git_remote import normalize_github_repo_url
from cham_bai.model_options import IMAGE_MODEL_OPTIONS, MODEL_OPTIONS, QUIZ_KIND_OPTIONS
from cham_bai.quiz_excel import ensure_default_quiz_template, ensure_lesson_quiz_example_template
from cham_bai.quiz_excel import ensure_session_warmup_quiz_example_template
from cham_bai.quiz_gen import (
    QUIZ_KIND_LESSON,
    QUIZ_KIND_SESSION,
    QUIZ_KIND_SESSION_END,
    QUIZ_KIND_SESSION_WARMUP,
    QuizGenParams,
    default_quiz_output_path,
    default_session_end_quiz_output_path,
    default_session_warmup_quiz_output_path,
    normalize_quiz_kind,
    run_quiz_generation,
)
from cham_bai.reading_gen import (
    DEFAULT_LEARNING_GOALS,
    ReadingDocParams,
    reading_output_stem,
    run_reading_generation,
    sanitize_reading_filename_part,
)
from cham_bai.btvn_comment import BtvnCommentParams, run_btvn_comments_json
from cham_bai.workflow import (
    GradeJobParams,
    GradeJobResult,
    has_grade_slots,
    run_grade_batch,
    run_grade_job,
)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="web")


def _parse_bool_form(s: str | None) -> bool:
    return (s or "").strip().lower() in ("true", "1", "on", "yes")


def _static_dir() -> Path:
    return Path(__file__).resolve().parent / "web" / "static"


app = FastAPI(title="Agent Edu", version=__version__, docs_url=None, redoc_url=None)

if _static_dir().is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir())), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    index_path = _static_dir() / "index.html"
    if not index_path.is_file():
        return HTMLResponse(
            "<h1>Agent Edu web</h1><p>Thiếu file static/index.html</p>",
            status_code=500,
        )
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/api/meta")
async def api_meta() -> JSONResponse:
    return JSONResponse(
        {
            "version": __version__,
            "models": list(MODEL_OPTIONS),
            "image_models": list(IMAGE_MODEL_OPTIONS),
            "quiz_kinds": [{"label": a, "value": b} for a, b in QUIZ_KIND_OPTIONS],
            "default_model": os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6"),
            "default_image_model": IMAGE_MODEL_OPTIONS[0],
            "default_learning_goals": DEFAULT_LEARNING_GOALS,
        }
    )


def _format_grade_block(label: str, res: GradeJobResult) -> str:
    lines = [f"——— {label} ———"]
    for w in res.warnings:
        lines.append(f"[Cảnh báo] {w}")
    if not res.ok:
        lines.append(f"[Lỗi] {res.error_message or '?'}")
        return "\n".join(lines) + "\n"
    lines.append("[Xong]")
    if res.json_text:
        try:
            blob = json.loads(res.json_text)
            lines.append(f"Điểm: {blob.get('final_score')}")
            lines.append(f"Nhận xét: {blob.get('final_comment')}")
            mp = blob.get("mini_project_present")
            if mp is not None:
                lines.append(f"Mini project (chỉ có/không): {mp}")
        except json.JSONDecodeError:
            lines.append(res.json_text[:2000])
    return "\n".join(lines) + "\n"


async def _save_upload_optional(upload: UploadFile | None, suffix: str) -> str | None:
    if upload is None or not upload.filename:
        return None
    data = await upload.read()
    if not data:
        return None
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    Path(path).write_bytes(data)
    return path


def _run_grade_sync(
    assignment_ref: str,
    subs_lines: list[str],
    model: str,
    no_template: bool,
    strict_ai: bool,
    ai_confidence: int,
    report_repos_text: str = "",
) -> tuple[bool, str, list[dict]]:
    try:
        from cham_bai.settings import api_key as _need_key

        _need_key()
    except RuntimeError as e:
        return False, str(e), []

    params = GradeJobParams(
        assignment_ref=assignment_ref,
        submission_ref=subs_lines[0],
        out_path=None,
        model=model.strip(),
        no_template=no_template,
        strict_ai=strict_ai,
        ai_confidence=int(ai_confidence),
        debug=False,
        report_repos_text=report_repos_text or "",
    )

    log_parts: list[str] = []
    payload: list[dict] = []

    if len(subs_lines) == 1:
        res = run_grade_job(params)
        log_parts.append(_format_grade_block("Bài nộp", res))
        row: dict = {"submission": subs_lines[0], "ok": res.ok}
        if res.error_message:
            row["error"] = res.error_message
        if res.warnings:
            row["warnings"] = res.warnings
        if res.json_text:
            try:
                row["result"] = json.loads(res.json_text)
            except json.JSONDecodeError:
                row["result_raw"] = res.json_text
        payload.append(row)
        return res.ok, "\n".join(log_parts), payload

    batch = run_grade_batch(assignment_ref, subs_lines, params)
    ok_any = False
    for sub, res in batch:
        log_parts.append(_format_grade_block(sub, res))
        row = {"submission": sub, "ok": res.ok}
        if res.error_message:
            row["error"] = res.error_message
        if res.warnings:
            row["warnings"] = res.warnings
        if res.json_text:
            try:
                row["result"] = json.loads(res.json_text)
            except json.JSONDecodeError:
                row["result_raw"] = res.json_text
        payload.append(row)
        if res.ok:
            ok_any = True
    return ok_any, "\n".join(log_parts), payload


@app.post("/api/grade")
async def api_grade(
    assignment_text: str = Form(...),
    submissions_text: str = Form(""),
    report_repos_text: str = Form(""),
    model: str = Form(""),
    use_template: str = Form("true"),
    strict_ai: str = Form("true"),
    ai_confidence: int = Form(75),
) -> JSONResponse:
    subs_lines = [(ln.rstrip("\r") or "").strip() for ln in (submissions_text or "").splitlines()]

    assignment_ref = (assignment_text or "").strip()
    if not assignment_ref:
        raise HTTPException(
            status_code=400,
            detail="Điền đề bài: đường dẫn file .docx trên máy chủ hoặc link Google Docs.",
        )

    p = Path(assignment_ref)
    ok_docx = p.is_file() and p.suffix.lower() == ".docx"
    ok_gdoc = is_google_docs_url(assignment_ref)
    if not ok_docx and not ok_gdoc:
        raise HTTPException(
            status_code=400,
            detail="Đề cần là đường dẫn file .docx tồn tại trên máy chủ hoặc URL Google Docs.",
        )

    if not has_grade_slots(subs_lines, report_repos_text or ""):
        raise HTTPException(
            status_code=400,
            detail="Cần ít nhất một dòng có bài nộp (thư mục/GitHub) hoặc link repo báo cáo.",
        )

    for s in subs_lines:
        if not s.strip():
            continue
        if not normalize_github_repo_url(s) and not Path(s).is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Bài nộp không hợp lệ (thư mục trên máy chủ hoặc link GitHub): {s[:160]}",
            )

    for ln in (report_repos_text or "").splitlines():
        u = ln.strip()
        if u and not normalize_github_repo_url(u):
            raise HTTPException(
                status_code=400,
                detail=f"Dòng repo báo cáo không hợp lệ (chỉ GitHub): {u[:160]}",
            )

    loop = asyncio.get_event_loop()

    def work():
        return _run_grade_sync(
            assignment_ref,
            subs_lines,
            model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6"),
            not _parse_bool_form(use_template),
            _parse_bool_form(strict_ai),
            ai_confidence,
            report_repos_text=report_repos_text or "",
        )

    ok, log, results = await loop.run_in_executor(_executor, work)

    return JSONResponse({"ok": ok, "log": log, "results": results})


@app.post("/api/quiz")
async def api_quiz(
    background_tasks: BackgroundTasks,
    quiz_kind_label: str = Form(...),
    subject: str = Form(""),
    lesson: str = Form(""),
    session: str = Form(""),
    session_prev: str = Form(""),
    session_current: str = Form(""),
    num_questions: int = Form(5),
    model: str = Form(""),
    template_file: UploadFile | None = File(None),
    docx_file: UploadFile | None = File(None),
) -> FileResponse:
    kind_map = dict(QUIZ_KIND_OPTIONS)
    qkind = normalize_quiz_kind(kind_map.get(quiz_kind_label.strip(), QUIZ_KIND_SESSION))

    tmp_tpl = await _save_upload_optional(template_file, ".xlsx")
    if tmp_tpl:
        template_path = Path(tmp_tpl)
    elif qkind == QUIZ_KIND_LESSON:
        template_path = ensure_lesson_quiz_example_template()
    elif qkind in (QUIZ_KIND_SESSION_WARMUP, QUIZ_KIND_SESSION_END):
        template_path = ensure_session_warmup_quiz_example_template()
    else:
        template_path = ensure_default_quiz_template()

    tmp_docx = await _save_upload_optional(docx_file, ".docx")
    docx_path = Path(tmp_docx) if tmp_docx else None
    if docx_path and not docx_path.is_file():
        if tmp_tpl:
            try:
                os.unlink(tmp_tpl)
            except OSError:
                pass
        if tmp_docx:
            try:
                os.unlink(tmp_docx)
            except OSError:
                pass
        raise HTTPException(status_code=400, detail="File DOCX không hợp lệ.")

    out_dir = tempfile.mkdtemp(prefix="quiz_out_")
    lesson_s = (lesson or "").strip()
    session_s = (session or "").strip()
    subj_s = (subject or "").strip()
    prev_s = (session_prev or "").strip()
    curr_s = (session_current or "").strip()
    if qkind == QUIZ_KIND_SESSION_WARMUP:
        if not subj_s or not curr_s:
            _cleanup_quiz_temp(tmp_tpl, tmp_docx, out_dir)
            raise HTTPException(status_code=400, detail="Thiếu môn học hoặc session hiện tại.")
        lesson_s = subj_s
        session_s = curr_s
        out_path = Path(out_dir) / default_session_warmup_quiz_output_path(template_path, curr_s).name
    elif qkind == QUIZ_KIND_SESSION_END:
        if not subj_s or not curr_s:
            _cleanup_quiz_temp(tmp_tpl, tmp_docx, out_dir)
            raise HTTPException(status_code=400, detail="Thiếu môn học hoặc session hiện tại.")
        lesson_s = subj_s
        session_s = curr_s
        out_path = Path(out_dir) / default_session_end_quiz_output_path(template_path, curr_s).name
    else:
        out_path = Path(out_dir) / default_quiz_output_path(template_path, lesson_s, session_s).name

    try:
        from cham_bai.settings import api_key as _need_key

        _need_key()
    except RuntimeError as e:
        _cleanup_quiz_temp(tmp_tpl, tmp_docx, out_dir)
        raise HTTPException(status_code=400, detail=str(e)) from e

    params = QuizGenParams(
        template_xlsx=template_path,
        docx_path=docx_path,
        lesson=lesson_s,
        session=session_s,
        session_prev=prev_s,
        session_current=curr_s,
        num_questions=(45 if qkind in (QUIZ_KIND_SESSION_WARMUP, QUIZ_KIND_SESSION_END) else int(num_questions)),
        model=(model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")).strip(),
        output_xlsx=out_path,
        subject=subj_s,
        quiz_kind=qkind,
    )

    loop = asyncio.get_event_loop()

    def gen():
        return run_quiz_generation(params)

    ok, msg = await loop.run_in_executor(_executor, gen)
    if tmp_tpl:
        try:
            os.unlink(tmp_tpl)
        except OSError:
            pass
    if tmp_docx:
        try:
            os.unlink(tmp_docx)
        except OSError:
            pass

    if not ok:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=msg)

    safe_name = out_path.name
    background_tasks.add_task(shutil.rmtree, out_dir, True)

    return FileResponse(
        path=str(out_path),
        filename=safe_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _cleanup_quiz_temp(tmp_tpl: str | None, tmp_docx: str | None, out_dir: str | None) -> None:
    if tmp_tpl:
        try:
            os.unlink(tmp_tpl)
        except OSError:
            pass
    if tmp_docx:
        try:
            os.unlink(tmp_docx)
        except OSError:
            pass
    if out_dir:
        shutil.rmtree(out_dir, ignore_errors=True)


@app.post("/api/btvn")
async def api_btvn(
    background_tasks: BackgroundTasks,
    assignment_text: str = Form(""),
    submissions_text: str = Form(...),
    model: str = Form(""),
    github_token: str = Form(""),
    assignment_images: list[UploadFile] | None = File(None),
) -> JSONResponse:
    subs_lines = [
        ln.strip()
        for ln in (submissions_text or "").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not subs_lines:
        raise HTTPException(status_code=400, detail="Chưa có danh sách bài nộp (mỗi dòng 1 link GitHub).")

    imgs: list[tuple[str, bytes]] = []
    if assignment_images:
        for f in assignment_images:
            if not f or not f.filename:
                continue
            raw = await f.read()
            if not raw:
                continue
            ct = (f.content_type or "").strip() or "image/png"
            if not ct.startswith("image/"):
                continue
            # giới hạn nhẹ để tránh payload quá lớn
            if len(raw) > 5_000_000:
                raise HTTPException(status_code=400, detail=f"Ảnh quá lớn: {f.filename} (>5MB).")
            imgs.append((ct, raw))

    params = BtvnCommentParams(
        assignment_text=(assignment_text or "").strip(),
        assignment_images=imgs,
        submissions=subs_lines,
        model=(model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")).strip(),
        github_token=(github_token or "").strip(),
    )

    loop = asyncio.get_event_loop()

    def work():
        return run_btvn_comments_json(params)

    ok, msg, rows = await loop.run_in_executor(_executor, work)
    if not ok or rows is None:
        raise HTTPException(status_code=500, detail=msg or "Lỗi không xác định.")

    return JSONResponse({"ok": True, "rows": rows})


@app.post("/api/reading")
async def api_reading(
    background_tasks: BackgroundTasks,
    subject: str = Form(...),
    session: str = Form(...),
    lesson: str = Form(...),
    session_stt: str = Form("1"),
    lesson_stt: str = Form("1"),
    video_url: str = Form(""),
    technology: str = Form(""),
    audience: str = Form("Sinh viên năm 1, mới học lập trình"),
    learning_goals: str = Form(DEFAULT_LEARNING_GOALS),
    references_hint: str = Form(""),
    text_model: str = Form(""),
    image_model: str = Form(""),
    generate_illustrations: str = Form("true"),
) -> FileResponse:
    subject = subject.strip()
    session = session.strip()
    lesson = lesson.strip()
    if not subject or not session or not lesson:
        raise HTTPException(status_code=400, detail="Điền đủ môn, session và lesson.")

    try:
        from cham_bai.settings import api_key as _need_key

        _need_key()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    ss = (session_stt or "1").strip() or "1"
    ls = (lesson_stt or "1").strip() or "1"
    stem = reading_output_stem(subject, ss, ls)

    work_dir = tempfile.mkdtemp(prefix="reading_")
    out_docx = Path(work_dir) / f"{stem}.docx"
    out_xlsx = Path(work_dir) / f"{stem}.xlsx"

    params = ReadingDocParams(
        subject=subject,
        session=session,
        lesson=lesson,
        session_stt=ss,
        lesson_stt=ls,
        video_url=(video_url or "").strip() or None,
        technology=(technology or "").strip(),
        audience=(audience or "").strip(),
        learning_goals=(learning_goals or "").strip(),
        references_hint=(references_hint or "").strip(),
        text_model=(text_model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")).strip(),
        image_model=(image_model or IMAGE_MODEL_OPTIONS[0]).strip(),
        generate_illustrations=_parse_bool_form(generate_illustrations),
        output_docx=out_docx,
        output_xlsx=out_xlsx,
    )

    loop = asyncio.get_event_loop()

    def gen():
        return run_reading_generation(params)

    ok, msg = await loop.run_in_executor(_executor, gen)
    if not ok:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=msg)

    zip_fd, zip_path = tempfile.mkstemp(suffix=".zip")
    os.close(zip_fd)
    zip_p = Path(zip_path)
    with zipfile.ZipFile(zip_p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(out_docx, arcname=out_docx.name)
        zf.write(out_xlsx, arcname=out_xlsx.name)

    def cleanup():
        try:
            zip_p.unlink(missing_ok=True)
        except OSError:
            pass
        shutil.rmtree(work_dir, ignore_errors=True)

    background_tasks.add_task(cleanup)

    zip_name = sanitize_reading_filename_part(stem) + ".zip"
    return FileResponse(
        path=str(zip_p),
        filename=zip_name,
        media_type="application/zip",
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        "cham_bai.web_app:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
    )


if __name__ == "__main__":
    main()
