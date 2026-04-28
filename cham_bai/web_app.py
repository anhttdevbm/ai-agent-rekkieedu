"""
Giao diện web (FastAPI) cho Agent Edu — chạy local, tái dùng logic GUI.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import html as _html
import hashlib
import shutil
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from cham_bai import __version__
from cham_bai.gdocs_reader import fetch_google_doc_plain_text, is_google_docs_url
from cham_bai.git_remote import normalize_github_repo_url
from cham_bai.model_options import (
    DEFAULT_BTVN_MODEL,
    IMAGE_MODEL_OPTIONS,
    MODEL_OPTIONS,
    QUIZ_KIND_OPTIONS,
)
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
from cham_bai.group_activity import GroupGradeParams, grade_group_activity
from cham_bai.hackathon_exam import (
    HackathonExamParams,
    build_hackathon_exam_docx_bytes,
    build_hackathon_exam_docx_from_spec,
)
from cham_bai.hackathon_ai import (
    build_required_bullets,
    ensure_practice_section,
    ensure_required_section,
    generate_hackathon_exam_spec,
    normalize_exam_template,
)
from cham_bai.workflow import (
    GradeJobParams,
    GradeJobResult,
    has_grade_slots,
    is_valid_report_source_url,
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
            "default_btvn_model": os.getenv("OPENROUTER_BTVN_MODEL", DEFAULT_BTVN_MODEL),
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
        if u and not is_valid_report_source_url(u):
            raise HTTPException(
                status_code=400,
                detail=f"Dòng báo cáo không hợp lệ (GitHub, Google Docs hoặc OneDrive/SharePoint): {u[:160]}",
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
    lecture_gdocs_urls_text: str = Form(""),
    lecture_prev_gdocs_urls_text: str = Form(""),
    lecture_current_gdocs_urls_text: str = Form(""),
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

    # Lecture source (ưu tiên Google Docs nhiều link; fallback DOCX upload).
    # Allow long URLs to wrap/break into multiple lines: join continuation lines.
    def _parse_docs_urls(text: str) -> list[str]:
        out: list[str] = []
        buf2 = ""
        for ln in (text or "").splitlines():
            s = (ln or "").strip()
            if not s or s.startswith("#"):
                continue
            if s.lower().startswith(("http://", "https://")):
                if buf2:
                    out.append(buf2)
                buf2 = s
            else:
                buf2 = (buf2 + s) if buf2 else s
        if buf2:
            out.append(buf2)
        return out

    def _fetch_docs_text(urls: list[str], *, label: str) -> str:
        if not urls:
            return ""
        parts: list[str] = []
        for idx, u in enumerate(urls[:12], start=1):
            if not is_google_docs_url(u):
                raise HTTPException(status_code=400, detail=f"Link Google Docs không hợp lệ ({label}, dòng {idx}): {u[:180]}")
            try:
                txt = fetch_google_doc_plain_text(u)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Lỗi đọc Google Docs ({label}, dòng {idx}): {e}")
            txt = (txt or "").strip()
            if txt:
                parts.append(f"=== {label} DOC {idx} ===\nNguồn: {u}\n\n{txt}\n")
        return ("\n\n".join(parts)).strip()

    lecture_text = ""
    lecture_prev_text = ""
    lecture_curr_text = ""
    try:
        # Warmup: 2 nhóm link (session cũ / session hiện tại)
        prev_urls = _parse_docs_urls(lecture_prev_gdocs_urls_text)
        curr_urls = _parse_docs_urls(lecture_current_gdocs_urls_text)
        lecture_prev_text = _fetch_docs_text(prev_urls, label="SESSION TRƯỚC") if prev_urls else ""
        lecture_curr_text = _fetch_docs_text(curr_urls, label="SESSION HIỆN TẠI") if curr_urls else ""

        # Fallback: ô 1 nhóm link (cũ)
        urls_single = _parse_docs_urls(lecture_gdocs_urls_text)
        lecture_text = _fetch_docs_text(urls_single, label="BÀI GIẢNG") if urls_single else ""
    except HTTPException:
        _cleanup_quiz_temp(tmp_tpl, None, None)
        raise

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
        lecture_text=lecture_text,
        lecture_text_prev=lecture_prev_text,
        lecture_text_current=lecture_curr_text,
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


def _rk_bearer(token: str) -> str:
    t = (token or "").strip()
    if not t:
        return ""
    if t.lower().startswith("bearer "):
        return t
    return "Bearer " + t


def _rk_sanitize_html(s: str) -> str:
    raw = (s or "").strip()
    # drop script/style and basic inline handlers
    raw = re.sub(r"<script[\s\S]*?</script>", "", raw, flags=re.I)
    raw = re.sub(r"<style[\s\S]*?</style>", "", raw, flags=re.I)
    raw = re.sub(r"\son\w+=(\"[^\"]*\"|'[^']*')", "", raw, flags=re.I)
    return raw


_IMG_SRC_RE = re.compile(r"<img[^>]+src=[\"'](?P<src>[^\"']+)[\"'][^>]*>", re.I)


def _rk_extract_image_urls(html: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for m in _IMG_SRC_RE.finditer(html or ""):
        u = (m.group("src") or "").strip()
        if not u:
            continue
        if u not in seen:
            seen.add(u)
            urls.append(u)
    return urls


def _rk_html_to_plain_text(html: str) -> str:
    s = (html or "").strip()
    if not s:
        return ""
    # line breaks for common tags
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p\s*>", "\n\n", s)
    s = re.sub(r"(?i)</li\s*>", "\n", s)
    # remove tags
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s+\n", "\n\n", s)
    return s.strip()


async def _rk_fetch_image_bytes(url: str) -> tuple[str, bytes] | None:
    u = (url or "").strip()
    if not u.startswith(("http://", "https://")):
        return None
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            r = await client.get(u, headers={"User-Agent": "AgentEdu/1.0"})
        r.raise_for_status()
        raw = r.content or b""
        if not raw or len(raw) < 64:
            return None
        if len(raw) > 5_000_000:
            return None
        ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
        if ct and ct.startswith("image/"):
            return ct, raw
        # best-effort sniff
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png", raw
        if raw[:2] == b"\xff\xd8":
            return "image/jpeg", raw
        if raw[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif", raw
        if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            return "image/webp", raw
        return None
    except Exception:
        return None


@app.post("/api/rikkei/session")
async def api_rikkei_session(
    session_id: int = Form(...),
    rikkei_token: str = Form(...),
) -> JSONResponse:
    sid = int(session_id)
    tok = (rikkei_token or "").strip()
    if not tok:
        raise HTTPException(status_code=400, detail="Thiếu token Rikkei.")
    url = f"https://apiportal.rikkei.edu.vn/sessions/{sid}"
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            r = await client.get(url, headers={"Authorization": _rk_bearer(tok), "User-Agent": "AgentEdu/1.0"})
        if r.status_code in (401, 403):
            raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc không có quyền truy cập session này.")
        r.raise_for_status()
        data = r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Lỗi gọi API Rikkei: {e}")

    hw = data.get("homework") if isinstance(data, dict) else None
    if not isinstance(hw, list):
        hw = []
    out_hw: list[dict] = []
    for item in hw:
        if not isinstance(item, dict):
            continue
        hid = item.get("id")
        title = item.get("title") or ""
        desc = item.get("description") or ""
        desc_s = _rk_sanitize_html(str(desc))
        out_hw.append(
            {
                "id": hid,
                "title": str(title),
                "description_html": desc_s,
                "plain_text": _rk_html_to_plain_text(desc_s),
                "image_urls": _rk_extract_image_urls(desc_s),
            }
        )

    return JSONResponse(
        {
            "id": data.get("id") if isinstance(data, dict) else sid,
            "name": data.get("name") if isinstance(data, dict) else f"Session {sid}",
            "homework": out_hw,
        }
    )


def _extract_rikkei_token(payload: object) -> str:
    """
    Best-effort: Rikkei portal implementations vary.
    Try common shapes: {"token":..}, {"accessToken":..}, {"data":{"token":..}}, etc.
    """
    if isinstance(payload, dict):
        for k in ("token", "accessToken", "access_token", "secretToken", "secret_token", "jwt"):
            v = payload.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        data = payload.get("data")
        if isinstance(data, dict):
            for k in ("token", "accessToken", "access_token", "secretToken", "secret_token", "jwt"):
                v = data.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
    return ""


@app.post("/api/rikkei/login")
async def api_rikkei_login(
    email: str = Form(...),
    password: str = Form(...),
) -> JSONResponse:
    em = (email or "").strip()
    pw = password or ""
    if not em or not pw:
        raise HTTPException(status_code=400, detail="Thiếu email hoặc mật khẩu.")

    url = "https://apiportal.rikkei.edu.vn/auth/secret-token"
    # Do NOT log credentials. Only exchange to token.
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            # Attempt 1: BasicAuth, empty JSON (some setups use only auth header)
            r = await client.post(url, auth=(em, pw), headers={"User-Agent": "AgentEdu/1.0"})
            if r.status_code >= 400:
                # Attempt 2: JSON body with email/password
                r = await client.post(
                    url,
                    json={"email": em, "password": pw},
                    headers={"User-Agent": "AgentEdu/1.0", "Accept": "application/json"},
                )
        if r.status_code in (401, 403):
            raise HTTPException(status_code=401, detail="Sai tài khoản hoặc không có quyền.")
        r.raise_for_status()
        data = r.json()
        tok = _extract_rikkei_token(data)
        if not tok:
            # fallback: if API returns raw string
            if isinstance(data, str) and data.strip():
                tok = data.strip()
        if not tok:
            raise HTTPException(status_code=502, detail="Đăng nhập OK nhưng không tìm thấy token trong response.")
        return JSONResponse({"ok": True, "token": tok})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Lỗi đăng nhập Rikkei: {e}")


@app.post("/api/btvn")
async def api_btvn(
    background_tasks: BackgroundTasks,
    assignment_text: str = Form(""),
    assignment_image_urls: str = Form(""),
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

    # Ảnh từ URL trong đề (từ Rikkei)
    ublob = (assignment_image_urls or "").strip()
    if ublob:
        try:
            urls = json.loads(ublob)
        except json.JSONDecodeError:
            urls = []
        if isinstance(urls, list):
            # giới hạn nhẹ để tránh payload
            for u in urls[:10]:
                if not isinstance(u, str):
                    continue
                got = await _rk_fetch_image_bytes(u)
                if got:
                    imgs.append(got)

    btvn_model = (model or "").strip() or (
        os.getenv("OPENROUTER_BTVN_MODEL", DEFAULT_BTVN_MODEL).strip()
        or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6").strip()
    )
    params = BtvnCommentParams(
        assignment_text=(assignment_text or "").strip(),
        assignment_images=imgs,
        submissions=subs_lines,
        model=btvn_model,
        github_token=(github_token or "").strip(),
    )

    loop = asyncio.get_event_loop()

    def work():
        return run_btvn_comments_json(params)

    ok, msg, rows = await loop.run_in_executor(_executor, work)
    if not ok or rows is None:
        raise HTTPException(status_code=500, detail=msg or "Lỗi không xác định.")

    at = (assignment_text or "").strip()
    fp = hashlib.sha1(at.encode("utf-8", errors="ignore")).hexdigest()[:10] if at else ""
    return JSONResponse(
        {
            "ok": True,
            "rows": rows,
            "assignment_fingerprint": {
                "chars": len(at),
                "sha1_10": fp,
                "head": at[:160],
            },
        }
    )


@app.post("/api/group-activity")
async def api_group_activity(
    video_transcript: str = Form(...),
    report_file: UploadFile = File(...),
    model: str = Form(""),
) -> PlainTextResponse:
    try:
        from cham_bai.settings import api_key as _need_key

        _need_key()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    m = (model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")).strip()
    vt = (video_transcript or "").strip()
    if not vt:
        raise HTTPException(status_code=400, detail="Thiếu transcript/ghi chú video.")

    if not report_file or not report_file.filename:
        raise HTTPException(status_code=400, detail="Thiếu file báo cáo.")
    raw = await report_file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="File báo cáo rỗng.")
    if len(raw) > 12_000_000:
        raise HTTPException(status_code=400, detail="File báo cáo quá lớn (>12MB).")
    fname = str(report_file.filename or "").strip()
    params = GroupGradeParams(
        report_filename=fname,
        report_bytes=raw,
        video_transcript=vt,
        model=m,
    )

    loop = asyncio.get_event_loop()

    def work():
        return grade_group_activity(params)

    try:
        result = await loop.run_in_executor(_executor, work)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return PlainTextResponse(result or "", media_type="text/plain; charset=utf-8")


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


@app.post("/api/hackathon")
async def api_hackathon(
    duration_minutes: int = Form(120),
    mode: str = Form("manual"),  # manual | ai
    subject: str = Form(""),
    outline_text: str = Form(""),
    technology: str = Form("MySQL"),
    ide: str = Form("MySQL Workbench"),
    exam_code: str = Form("006"),
    exam_template: str = Form("mysql"),
    extra_notes: str = Form(""),
    model: str = Form(""),
    body_text: str = Form(""),
) -> FileResponse:
    mins = max(1, int(duration_minutes or 0))
    m = (model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")).strip()

    raw: bytes
    if (mode or "").strip().lower() == "ai":
        # Need OpenRouter key
        try:
            from cham_bai.settings import api_key as _need_key

            _need_key()
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Fixed header like mẫu
        header_top = "KIỂM TRA HACKATHON"
        subj = (subject or "").strip() or "NHẬP MÔN CSDL MYSQL"
        try:
            ex_int = int(str(exam_code or "").strip() or "6")
        except Exception:
            ex_int = 6
        ex_int = max(1, min(999, ex_int))
        ex_code = f"{ex_int:03d}"
        hs = f"{subj} - Đề {ex_code}"
        tpl = normalize_exam_template(exam_template)

        try:
            spec = generate_hackathon_exam_spec(
                model=m,
                header_top=header_top,
                header_sub=hs,
                duration_minutes=mins,
                subject=subj,
                outline_text=(outline_text or "").strip(),
                technology=(technology or "").strip() or "MySQL",
                ide=(ide or "").strip() or "MySQL Workbench",
                exam_code=ex_code,
                exam_template=tpl,
                extra_notes=(extra_notes or "").strip(),
            )
            # Ensure required "Yêu cầu" always exists (AI sometimes omits).
            req_bullets = build_required_bullets(
                exam_template=tpl,
                technology=(technology or "").strip() or "MySQL",
                ide=(ide or "").strip() or "MySQL Workbench",
            )
            spec = ensure_required_section(spec, required_bullets=req_bullets)
            spec = ensure_practice_section(spec)
            raw = build_hackathon_exam_docx_from_spec(spec)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Lỗi tạo đề bằng AI: {e}")
    else:
        body = (body_text or "").strip()
        if not body:
            raise HTTPException(status_code=400, detail="Thiếu nội dung đề.")
        header_top = "KIỂM TRA HACKATHON"
        subj = (subject or "").strip() or "NHẬP MÔN CSDL MYSQL"
        try:
            ex_int = int(str(exam_code or "").strip() or "6")
        except Exception:
            ex_int = 6
        ex_int = max(1, min(999, ex_int))
        ex_code = f"{ex_int:03d}"
        hs = f"{subj} - Đề {ex_code}"
        params = HackathonExamParams(
            header_top=header_top,
            header_sub=hs,
            duration_minutes=mins,
            body_text=body,
        )
        raw = build_hackathon_exam_docx_bytes(params)

    if not raw:
        raise HTTPException(status_code=500, detail="Không tạo được file DOCX.")

    out_dir = tempfile.mkdtemp(prefix="hackathon_out_")
    out_path = Path(out_dir) / "de_hackathon.docx"
    out_path.write_bytes(raw)
    background_tasks = BackgroundTasks()
    background_tasks.add_task(shutil.rmtree, out_dir, True)
    return FileResponse(
        path=str(out_path),
        filename=out_path.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        background=background_tasks,
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
