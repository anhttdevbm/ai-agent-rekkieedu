from __future__ import annotations

import base64
import re
from urllib.parse import urlparse

import httpx

from cham_bai.docx_reader import extract_docx_bytes

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
}


def is_onedrive_share_url(url: str) -> bool:
    """Link chia sẻ OneDrive / SharePoint (thường dạng 1drv.ms/...)."""
    u = (url or "").strip().lower()
    if not u.startswith(("http://", "https://")):
        return False
    try:
        host = urlparse(u).hostname or ""
    except ValueError:
        return False
    if not host:
        return False
    if host in {"1drv.ms", "1drv.com", "373p.com"}:
        return True
    if host.endswith(".1drv.ms") or host.endswith(".1drv.com"):
        return True
    if host in {"onedrive.live.com", "onedrive.com"} or host.endswith(".onedrive.com"):
        return True
    if host.endswith("sharepoint.com") or host.endswith("sharepoint.de"):
        return True
    return False


def _graph_encoded_share_token(sharing_url: str) -> str:
    """Chuỗi shareId dạng u!... cho Microsoft Graph /shares/.../root/content."""
    b64 = base64.urlsafe_b64encode(sharing_url.encode("utf-8")).decode("ascii").rstrip("=")
    return "u!" + b64


def _plain_from_office_bytes(data: bytes, content_type: str) -> str | None:
    if not data or len(data) < 4:
        return None
    if data[:2] != b"PK":
        return None
    ct = (content_type or "").lower()
    if "html" in ct or data[:200].lstrip().startswith(b"<!"):
        return None
    try:
        dc = extract_docx_bytes(data)
        t = (dc.plain_text or "").strip()
        return t or None
    except Exception:
        return None


def _unescape_json_url(s: str) -> str:
    s = s.replace("\\/", "/").replace("\\u002f", "/").replace("\\u002F", "/")
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s


def _download_urls_from_embed_html(html: str) -> list[str]:
    out: list[str] = []
    for pat in (
        r'"downloadUrl"\s*:\s*"((?:\\.|[^"\\])*)"',
        r'"@content\.downloadUrl"\s*:\s*"((?:\\.|[^"\\])*)"',
        r'"originalDownloadUrl"\s*:\s*"((?:\\.|[^"\\])*)"',
    ):
        for m in re.finditer(pat, html, re.I):
            u = _unescape_json_url(m.group(1))
            if u.startswith("https://") or u.startswith("http://"):
                out.append(u)
    # Một số trang nhúng dùng URL thẳng tới *.1drv.com
    for m in re.finditer(
        r"https://[a-z0-9.-]+\.1drv\.com/[^\"'\\s<>]+",
        html,
        re.I,
    ):
        u = m.group(0).rstrip("\\")
        if u not in out:
            out.append(u)
    return out


def fetch_onedrive_share_plain_text(url: str, *, timeout_s: float = 90.0, max_bytes: int = 18_000_000) -> str:
    """
    Tải tài liệu Word chia sẻ OneDrive (1drv.ms, onedrive.live.com, sharepoint.com…)
    và trả về văn bản trích từ .docx. Cần quyền xem qua liên kết (Anyone with the link).
    """
    start = (url or "").strip()
    if not start:
        raise ValueError("URL OneDrive rỗng.")

    with httpx.Client(
        timeout=httpx.Timeout(timeout_s),
        follow_redirects=True,
        headers=_BROWSER_HEADERS,
    ) as client:
        r = client.get(start)
        r.raise_for_status()
        final_url = str(r.url)
        data = r.content
        if len(data) > max_bytes:
            raise RuntimeError(f"File tải về quá lớn (>{max_bytes} byte).")

        plain = _plain_from_office_bytes(data, r.headers.get("content-type", ""))
        if plain:
            return plain

        # Thử ?download=1 (một số link Word Online)
        if "download=" not in final_url.lower():
            sep = "&" if "?" in start else "?"
            r2 = client.get(f"{start}{sep}download=1")
            if r2.is_success:
                plain = _plain_from_office_bytes(r2.content, r2.headers.get("content-type", ""))
                if plain:
                    return plain

        # Microsoft Graph: tải nội dung qua share token (đôi khi hoạt động không cần OAuth với link công khai)
        for share_src in (final_url, start):
            enc = _graph_encoded_share_token(share_src)
            gurl = f"https://graph.microsoft.com/v1.0/shares/{enc}/root/content"
            try:
                rg = client.get(gurl)
                if rg.is_success:
                    plain = _plain_from_office_bytes(rg.content, rg.headers.get("content-type", ""))
                    if plain:
                        return plain
            except httpx.HTTPError:
                pass

        # Trang HTML nhúng: tìm downloadUrl rồi GET
        if "text/html" in (r.headers.get("content-type") or "").lower() or data[:100].lstrip().startswith(b"<"):
            html = r.text or ""
            for dl in _download_urls_from_embed_html(html):
                try:
                    rd = client.get(dl)
                    if rd.is_success:
                        plain = _plain_from_office_bytes(rd.content, rd.headers.get("content-type", ""))
                        if plain:
                            return plain
                except httpx.HTTPError:
                    continue

    raise RuntimeError(
        "Không đọc được nội dung từ link OneDrive/SharePoint. "
        "Kiểm tra link còn hạn, tài liệu là Word (.docx online), và đã bật chia sẻ "
        "«Bất kỳ ai có liên kết có thể xem» (Anyone with the link can view)."
    )
