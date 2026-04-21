from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx
import io
import html as _html
from openpyxl import load_workbook

from cham_bai.gdocs_reader import (
    fetch_google_doc_plain_text,
    fetch_google_sheet_plain_text,
    is_google_docs_url,
    is_google_sheet_url,
)
from cham_bai.openrouter import complete_chat_raw
from cham_bai.schemas import parse_llm_json
from cham_bai.video_transcript import fetch_youtube_transcript_plain


@dataclass
class GroupGradeParams:
    report_url: str
    video_url: str
    video_notes: str
    model: str
    yescribe_token: str = ""
    yescribe_uniqueid: str = ""
    yescribe_cookie: str = ""


_SYSTEM = """Bạn là giảng viên chấm HOẠT ĐỘNG NHÓM.

Đầu vào gồm:
- BÁO CÁO (từ Google Docs/Excel đã trích text)
- LINK VIDEO (chỉ là link)
- GHI CHÚ VIDEO (nếu có): có thể là transcript/tóm tắt do người chấm cung cấp

Nguyên tắc:
1) Tuyệt đối KHÔNG bịa nội dung video nếu chỉ có link mà không có transcript/ghi chú. Khi thiếu dữ liệu video, phải ghi rõ trong kết quả.
2) Đánh giá 2 phần:
   - Hoạt động nhóm trong video: mức độ phối hợp, phân công, nhóm trưởng điều phối.
   - Báo cáo: nhóm trưởng có báo cáo đúng/đủ theo nội dung nhóm đã làm (đối chiếu theo ghi chú video nếu có).
3) Ngôn ngữ: tiếng Việt, ngắn gọn, thực tế.

CHỈ trả về một JSON hợp lệ theo schema:
{
  "score": 0-100,
  "comment": "2-4 câu tiếng Việt, không bullet, không markdown",
  "video_evidence": "du" | "thieu",
  "leader_activity_ok": true|false|"khong_ro",
  "leader_report_match": true|false|"khong_ro",
  "notes": "1-2 câu nếu thiếu dữ liệu video/report"
}
"""

_YT_ID_RE = re.compile(r"(?:v=|/shorts/|youtu\.be/)(?P<id>[A-Za-z0-9_-]{6,})", re.I)
_YESCRIBE_BOOTSTRAP_URL = "https://yescribe.ai/vi/youtube-transcript-generator"


def _extract_youtube_id(url: str) -> str | None:
    m = _YT_ID_RE.search(url or "")
    return (m.group("id").strip() if m else None)


def _strip_xml_tags(s: str) -> str:
    # keep only text nodes content (very basic)
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def fetch_youtube_transcript_text(video_url: str) -> tuple[str, list[str]]:
    """
    Best-effort: youtube-transcript-api trước, rồi timedtext public. Nếu video không có caption -> trả rỗng.
    """
    warns: list[str] = []
    text_lib, err_lib = fetch_youtube_transcript_plain(video_url, max_chars=22000)
    if (text_lib or "").strip():
        warns.append("Đã lấy transcript YouTube qua youtube-transcript-api.")
        return text_lib.strip(), warns
    if err_lib:
        warns.append(f"youtube-transcript-api: {err_lib}")

    vid = _extract_youtube_id(video_url)
    if not vid:
        warns.append("Không nhận diện được ID video YouTube.")
        return "", warns
    # thử tiếng Việt trước, rồi fallback English + auto
    candidates = [
        f"https://www.youtube.com/api/timedtext?lang=vi&v={vid}",
        f"https://www.youtube.com/api/timedtext?lang=en&v={vid}",
        f"https://www.youtube.com/api/timedtext?v={vid}",
    ]
    headers = {"User-Agent": "AgentEdu/1.0"}
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for u in candidates:
            try:
                r = client.get(u, headers=headers)
                if r.status_code != 200:
                    continue
                t = (r.text or "").strip()
                if not t or "<transcript" not in t.lower():
                    continue
                text = _strip_xml_tags(t)
                # timedtext thường rất ngắn nếu không có caption
                if len(text) >= 80:
                    if "lang=vi" in u:
                        warns.append("Đã lấy transcript YouTube (vi) từ timedtext.")
                    elif "lang=en" in u:
                        warns.append("Đã lấy transcript YouTube (en) từ timedtext.")
                    else:
                        warns.append("Đã lấy transcript YouTube từ timedtext.")
                    return text, warns
            except Exception:
                continue
    warns.append("Không lấy được transcript YouTube (video không có caption public hoặc bị chặn).")
    return "", warns


def _yescribe_auth_header_variants(token: str) -> list[dict[str, str]]:
    t = (token or "").strip()
    if not t:
        return [{}]
    low = t.lower()
    out: list[dict[str, str]] = []
    if low.startswith("bearer "):
        out.append({"Authorization": t})
    else:
        out.append({"Authorization": f"Bearer {t}"})
        out.append({"X-API-Key": t})
        out.append({"Authorization": t})
    # giữ thứ tự, bỏ trùng
    seen: set[tuple[tuple[str, str], ...]] = set()
    uniq: list[dict[str, str]] = []
    for h in out:
        key = tuple(sorted(h.items()))
        if key not in seen:
            seen.add(key)
            uniq.append(h)
    return uniq


def _yescribe_read_uniqueid_from_cookies(client: httpx.Client) -> str:
    for name in ("uniqueId", "uniqueid", "UniqueId"):
        try:
            v = client.cookies.get(name)
            if v:
                return str(v).strip()
        except Exception:
            continue
    return ""


def _yescribe_bootstrap_session(client: httpx.Client, *, user_agent: str, accept_language: str) -> list[str]:
    """GET trang web để nhận cookie (uniqueId, v.v.). JSESSIONID thường do api.yescribe.ai set ở lần POST sau."""
    w: list[str] = []
    try:
        r = client.get(
            _YESCRIBE_BOOTSTRAP_URL,
            headers={
                "User-Agent": user_agent,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": accept_language,
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Referer": "https://yescribe.ai/",
            },
        )
        if r.status_code != 200:
            w.append(f"Yescribe bootstrap GET HTTP {r.status_code}.")
        elif _yescribe_read_uniqueid_from_cookies(client):
            w.append("Yescribe: đã tải trang generator — có cookie uniqueId cho API.")
        else:
            w.append(
                "Yescribe bootstrap: không thấy cookie uniqueId (có thể trang tạo id bằng JS — hãy dán uniqueid thủ công)."
            )
    except Exception as e:
        w.append(f"Yescribe bootstrap GET lỗi: {e}")
    return w


def fetch_yescribe_transcript_text(
    video_url: str,
    *,
    api_token: str | None = None,
    uniqueid: str | None = None,
    cookie: str | None = None,
) -> tuple[str, list[str]]:
    """
    Lấy transcript qua API yescribe.ai.

    Trình duyệt thường gửi kèm header ``uniqueid`` và cookie phiên ``JSESSIONID`` (không phải Bearer).
    Có thể dán từ DevTools → Request Headers, hoặc dùng API key qua ô token / YESCRIBE_API_KEY.

    Nếu **không** dán cookie và **không** có API key: tự **GET** trang
    ``/vi/youtube-transcript-generator`` để lấy cookie ``uniqueId`` (giống mở trang trên trình duyệt),
    rồi POST — ``JSESSIONID`` có thể xuất hiện sau lần gọi API đầu (sẽ thử POST lại một lần).
    """
    warns: list[str] = []
    u = (video_url or "").strip()
    if not u:
        return "", warns
    env_tok = (os.getenv("YESCRIBE_API_KEY") or os.getenv("YESCRIBE_TOKEN") or "").strip()
    token = ((api_token or "").strip() or env_tok).strip()
    env_uid = (os.getenv("YESCRIBE_UNIQUEID") or "").strip()
    uid = ((uniqueid or "").strip() or env_uid).strip()
    env_ck = (os.getenv("YESCRIBE_COOKIE") or "").strip()
    ck = ((cookie or "").strip() or env_ck).strip()
    use_manual_cookie = bool(ck)

    if not token and not uid and not ck:
        warns.append(
            "Yescribe: chưa nhập gì — sẽ thử tải trang generator để lấy cookie; nếu vẫn Unauthorized hãy dán Cookie JSESSIONID + uniqueid từ DevTools."
        )

    # Theo payload bạn đưa: {"videoUrl":"..."}
    payloads: list[dict[str, Any]] = [{"videoUrl": u}]
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    accept_language = "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
    api_headers_base: dict[str, str] = {
        "User-Agent": ua,
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": accept_language,
        "Origin": "https://yescribe.ai",
        "Referer": "https://yescribe.ai/vi/youtube-transcript-generator",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }

    endpoint = "https://api.yescribe.ai/api/v1/yescribe/record/getVideoDetail"
    auth_opts = _yescribe_auth_header_variants(token)
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        if not token and not use_manual_cookie:
            warns.extend(_yescribe_bootstrap_session(client, user_agent=ua, accept_language=accept_language))
            if not uid:
                uid = _yescribe_read_uniqueid_from_cookies(client)

        for auth_extra in auth_opts:
            for p in payloads:
                for attempt in range(2):
                    headers = {**api_headers_base, **auth_extra}
                    if uid:
                        headers["uniqueid"] = uid
                    if use_manual_cookie:
                        headers["Cookie"] = ck
                    try:
                        r = client.post(endpoint, headers=headers, json=p)
                        if r.status_code != 200:
                            warns.append(f"Yescribe HTTP {r.status_code}.")
                            break
                        data = r.json()
                    except Exception:
                        warns.append("Yescribe lỗi gọi API hoặc parse JSON.")
                        break
                    try:
                        code = int(data.get("code", 0))
                    except Exception:
                        code = 0
                    msg = str(data.get("msg") or "")
                    if code != 200:
                        warns.append(f"Yescribe code={data.get('code')}, msg={data.get('msg')}.")
                        low = msg.lower()
                        if (
                            attempt == 0
                            and not use_manual_cookie
                            and ("unauthorized" in low or code == 400)
                        ):
                            warns.append("Yescribe: thử POST lần 2 sau khi server có thể đã gửi JSESSIONID.")
                            continue
                        break
                    d = data.get("data")
                    if not isinstance(d, dict):
                        break
                    ts = d.get("tranScript") or d.get("transcript") or d.get("tran_script")
                    if not isinstance(ts, list) or not ts:
                        break
                    lines: list[str] = []
                    for item in ts[:1200]:
                        if not isinstance(item, dict):
                            continue
                        text = str(item.get("text") or "").strip()
                        if not text:
                            continue
                        start = item.get("start")
                        try:
                            st = float(start)
                            mm = int(st // 60)
                            ss = int(st % 60)
                            prefix = f"{mm:02d}:{ss:02d} "
                        except Exception:
                            prefix = ""
                        lines.append(prefix + text)
                    body = "\n".join(lines).strip()
                    if len(body) >= 80:
                        warns.append("Đã lấy transcript từ Yescribe.")
                        return body, warns
                    break

    warns.append(
        "Không lấy được transcript từ Yescribe (thiếu phiên cookie/uniqueid, API key không hợp lệ, hoặc không có transcript)."
    )
    return "", warns


def _wb_to_text(xlsx_bytes: bytes, *, max_cells: int = 2500) -> str:
    wb = load_workbook(filename=io.BytesIO(xlsx_bytes), data_only=True)  # type: ignore[name-defined]
    parts: list[str] = []
    cells = 0
    for ws in wb.worksheets[:8]:
        parts.append(f"=== SHEET: {ws.title} ===")
        for row in ws.iter_rows(values_only=True):
            if cells >= max_cells:
                parts.append("[... TRUNCATED ...]")
                return "\n".join(parts).strip()
            vals = []
            for v in row:
                if v is None:
                    vals.append("")
                else:
                    s = str(v).strip()
                    vals.append(s)
            line = " | ".join(x for x in vals if x != "")
            if line.strip():
                parts.append(line)
            cells += 1
    return "\n".join(parts).strip()


def fetch_report_text(report_url: str) -> tuple[str, list[str]]:
    url = (report_url or "").strip()
    warnings: list[str] = []
    if not url:
        return "", ["Thiếu link báo cáo (sẽ chỉ đánh giá video nếu có dữ liệu)."]
    if is_google_docs_url(url) and not is_google_sheet_url(url):
        try:
            return fetch_google_doc_plain_text(url), warnings
        except Exception as e:
            return "", [f"Lỗi đọc Google Docs: {e}"]
    if is_google_sheet_url(url):
        try:
            return fetch_google_sheet_plain_text(url), warnings
        except Exception as e:
            return "", [f"Lỗi đọc Google Sheets: {e}"]

    # Excel URL (.xlsx)
    if re.search(r"\.xlsx(\?|$)", url, flags=re.I):
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                r = client.get(url, headers={"User-Agent": "AgentEdu/1.0"})
            r.raise_for_status()
            raw = r.content or b""
            if not raw:
                return "", ["Link Excel trả về rỗng."]
            return _wb_to_text(raw), warnings
        except Exception as e:
            return "", [f"Lỗi tải/đọc Excel: {e}"]

    return "", ["Link báo cáo chưa hỗ trợ (cần Google Docs/Sheets hoặc URL .xlsx)."]


def grade_group_activity(params: GroupGradeParams) -> dict[str, Any]:
    report_text, warns = fetch_report_text(params.report_url)
    video_url = (params.video_url or "").strip()
    video_notes = (params.video_notes or "").strip()
    transcript_source = "none"
    if video_url and not video_notes:
        t2, w2 = fetch_yescribe_transcript_text(
            video_url,
            api_token=params.yescribe_token,
            uniqueid=params.yescribe_uniqueid,
            cookie=params.yescribe_cookie,
        )
        warns.extend(w2)
        if t2:
            video_notes = t2
            transcript_source = "yescribe"
        else:
            t, w = fetch_youtube_transcript_text(video_url)
            warns.extend(w)
            if t:
                video_notes = t
                transcript_source = "youtube_timedtext"

    user_parts = [
        {
            "type": "text",
            "text": (
                "BÁO CÁO (text trích):\n"
                + (report_text.strip() or "(trống/không đọc được)")
                + "\n\nLINK VIDEO:\n"
                + (video_url or "(trống)")
                + "\n\nGHI CHÚ VIDEO (nếu có):\n"
                + (video_notes or "(không có)")
                + ("\n\nCẢNH BÁO:\n" + "\n".join(warns) if warns else "")
            ),
        }
    ]

    text, _ = complete_chat_raw(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user_parts}],
        model=params.model,
        temperature=0.2,
        max_tokens=650,
        timeout_s=300.0,
    )
    try:
        blob = parse_llm_json(text)
        if isinstance(blob, dict):
            blob.setdefault("_fetch_warnings", warns)
            blob.setdefault("_transcript_source", transcript_source)
            blob.setdefault("_transcript_chars", len(video_notes or ""))
            return blob
    except Exception:
        try:
            # fallback: đôi khi provider trả hẳn dict ở dạng string Python-ish hoặc rác
            blob2 = json.loads((text or "").strip())
            if isinstance(blob2, dict):
                blob2.setdefault("_fetch_warnings", warns)
                blob2.setdefault("_transcript_source", transcript_source)
                blob2.setdefault("_transcript_chars", len(video_notes or ""))
                return blob2
        except Exception:
            pass
    return {
        "score": 0,
        "comment": "Không chấm được do model không trả JSON hợp lệ.",
        "video_evidence": "thieu",
        "leader_activity_ok": "khong_ro",
        "leader_report_match": "khong_ro",
        "notes": (text or "")[:1200],
        "_fetch_warnings": warns,
        "_transcript_source": transcript_source,
        "_transcript_chars": len(video_notes or ""),
    }

