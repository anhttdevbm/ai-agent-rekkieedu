from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

import cham_bai.settings  # noqa: F401 — load .env via settings bootstrap

LARK_OPEN_API_BASE = (os.getenv("LARK_OPEN_API_BASE") or "https://open.larksuite.com/open-apis").rstrip("/")

# Base mặc định (Chấm hoạt động nhóm) — có thể ghi đè qua form / env
DEFAULT_BITABLE_APP_TOKEN = (os.getenv("LARK_BITABLE_APP_TOKEN") or "QumebR4fVa8pjHszEetlqpEOgkd").strip()
DEFAULT_BITABLE_TABLE_ID = (os.getenv("LARK_BITABLE_TABLE_ID") or "tblDcfxiZ9YVdy8D").strip()

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_YOUTUBE_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s#<>\"']+|youtube\.com/(?:embed|shorts|live)/[\w-]{6,}[^\s#<>\"']*|youtu\.be/[\w-]{6,}[^\s#<>\"']*)",
    re.IGNORECASE,
)


def _lark_app_credentials() -> tuple[str, str]:
    app_id = (os.getenv("LARK_APP_ID") or "").strip()
    secret = (os.getenv("LARK_APP_SECRET") or "").strip()
    if not app_id or not secret:
        raise RuntimeError(
            "Thiếu LARK_APP_ID hoặc LARK_APP_SECRET trong .env. "
            "Hoặc dùng chế độ session: dán User Access Token / Cookie từ trình duyệt (tab Chấm hoạt động nhóm)."
        )
    return app_id, secret


def get_tenant_access_token() -> str:
    app_id, app_secret = _lark_app_credentials()
    url = f"{LARK_OPEN_API_BASE}/auth/v3/tenant_access_token/internal"
    with httpx.Client(timeout=45.0) as client:
        r = client.post(url, json={"app_id": app_id, "app_secret": app_secret})
        r.raise_for_status()
        data = r.json()
    if int(data.get("code") or -1) != 0:
        raise RuntimeError(f"Lark token: {data.get('msg') or data}")
    token = (data.get("tenant_access_token") or "").strip()
    if not token:
        raise RuntimeError("Lark không trả tenant_access_token.")
    return token


def normalize_session_bearer_and_cookie(
    session_authorization: str | None,
    session_cookie: str | None,
) -> tuple[str | None, str | None]:
    """Chuẩn hoá dán từ DevTools (có thể là cả dòng 'Authorization: Bearer …' hoặc 'Cookie: …')."""
    raw_b = (session_authorization or "").strip()
    if raw_b:
        first_line = raw_b.split("\n", 1)[0].strip()
        raw_b = first_line
    if raw_b.lower().startswith("authorization:"):
        raw_b = raw_b.split(":", 1)[1].strip()
    if raw_b.lower().startswith("bearer "):
        raw_b = raw_b[7:].strip()
    if not raw_b:
        raw_b = None

    raw_c = (session_cookie or "").strip()
    if raw_c:
        first_line = raw_c.split("\n", 1)[0].strip()
        # Nhiều dòng cookie: ghép lại
        if "\n" in (session_cookie or ""):
            raw_c = "; ".join(x.strip() for x in (session_cookie or "").splitlines() if x.strip())
        else:
            raw_c = first_line
    if raw_c.lower().startswith("cookie:"):
        raw_c = raw_c.split(":", 1)[1].strip()
    if not raw_c:
        raw_c = None

    return raw_b, raw_c


def build_auth_headers(
    *,
    tenant_access_token: str | None = None,
    user_access_token: str | None = None,
    cookie: str | None = None,
    use_browser_ua: bool = False,
) -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json; charset=utf-8"}
    if tenant_access_token:
        h["Authorization"] = f"Bearer {tenant_access_token}"
    elif user_access_token:
        h["Authorization"] = f"Bearer {user_access_token}"
    if cookie:
        h["Cookie"] = cookie
    if use_browser_ua:
        h.setdefault("User-Agent", _BROWSER_UA)
    if not h.get("Authorization") and not h.get("Cookie"):
        raise RuntimeError("Thiếu cách xác thực Lark (token hoặc cookie).")
    return h


def _extract_youtube_urls_from_scalar(val: Any, out: list[str], seen: set[str]) -> None:
    if val is None:
        return
    if isinstance(val, str):
        for m in _YOUTUBE_URL_RE.finditer(val):
            u = m.group(0).rstrip(").,;]")
            if u not in seen:
                seen.add(u)
                out.append(u)
        return
    if isinstance(val, dict):
        for k in ("link", "url", "href", "text"):
            if k in val:
                _extract_youtube_urls_from_scalar(val.get(k), out, seen)
        if "value" in val and isinstance(val["value"], (list, dict, str)):
            _extract_youtube_urls_from_scalar(val.get("value"), out, seen)
        return
    if isinstance(val, list):
        for x in val:
            _extract_youtube_urls_from_scalar(x, out, seen)


def extract_youtube_urls_from_lark_field(val: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    _extract_youtube_urls_from_scalar(val, out, seen)
    return out


def _raise_lark_data(data: dict[str, Any], ctx: str) -> None:
    code = int(data.get("code") if data.get("code") is not None else -1)
    if code != 0:
        msg = data.get("msg") or json.dumps(data, ensure_ascii=False)[:500]
        raise RuntimeError(f"{ctx}: {msg}")


def search_records_page(
    *,
    app_token: str,
    table_id: str,
    body: dict[str, Any],
    page_token: str | None,
    auth_headers: dict[str, str],
) -> dict[str, Any]:
    url = f"{LARK_OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
    payload = {**body, "page_size": min(int(body.get("page_size") or 500), 500)}
    if page_token:
        payload["page_token"] = page_token
    headers = dict(auth_headers)
    headers.setdefault("Content-Type", "application/json; charset=utf-8")
    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    _raise_lark_data(data, "Lark Bitable search")
    return data.get("data") or {}


def iter_today_records(
    *,
    app_token: str,
    table_id: str,
    date_field_name: str,
    field_names: list[str] | None,
    auth_headers: dict[str, str],
) -> list[dict[str, Any]]:
    """Lọc đúng “hôm nay” theo múi giờ của Base (Lark: value Today)."""
    filt = {
        "conjunction": "and",
        "conditions": [
            {
                "field_name": date_field_name.strip(),
                "operator": "is",
                "value": ["Today"],
            }
        ],
    }
    body: dict[str, Any] = {"filter": filt, "automatic_fields": False}
    if field_names:
        body["field_names"] = field_names

    items: list[dict[str, Any]] = []
    page_token: str | None = None
    for _ in range(200):
        chunk = search_records_page(
            app_token=app_token,
            table_id=table_id,
            body=body,
            page_token=page_token,
            auth_headers=auth_headers,
        )
        items.extend(chunk.get("items") or [])
        if not chunk.get("has_more"):
            break
        page_token = (chunk.get("page_token") or "").strip() or None
        if not page_token:
            break
    return items


def _resolve_auth_headers(
    session_authorization: str | None,
    session_cookie: str | None,
) -> dict[str, str]:
    ub, ck = normalize_session_bearer_and_cookie(session_authorization, session_cookie)
    if ub or ck:
        return build_auth_headers(user_access_token=ub, cookie=ck, use_browser_ua=True)
    tok = get_tenant_access_token()
    return build_auth_headers(tenant_access_token=tok, use_browser_ua=False)


def fetch_today_youtube_links(
    *,
    app_token: str,
    table_id: str,
    date_field_name: str,
    video_field_name: str,
    session_authorization: str | None = None,
    session_cookie: str | None = None,
) -> tuple[list[str], int]:
    """
    Trả về (danh_sách_url_youtube_theo_thứ_tự, số_bản_ghi_hôm_nay).

    Nếu có `session_authorization` hoặc `session_cookie`: gọi Open API như trình duyệt
    (User Access Token thường bắt đầu bằng `u-`; cookie hay cần kèm Bearer).
    Ngược lại: dùng tenant_access_token (LARK_APP_ID / SECRET).
    """
    auth_headers = _resolve_auth_headers(session_authorization, session_cookie)
    video_field_name = video_field_name.strip()
    items = iter_today_records(
        app_token=app_token.strip(),
        table_id=table_id.strip(),
        date_field_name=date_field_name.strip(),
        field_names=[video_field_name] if video_field_name else None,
        auth_headers=auth_headers,
    )
    urls: list[str] = []
    seen: set[str] = set()
    for it in items:
        fields = it.get("fields") if isinstance(it.get("fields"), dict) else {}
        raw = fields.get(video_field_name)
        for u in extract_youtube_urls_from_lark_field(raw):
            if u not in seen:
                seen.add(u)
                urls.append(u)
    return urls, len(items)
