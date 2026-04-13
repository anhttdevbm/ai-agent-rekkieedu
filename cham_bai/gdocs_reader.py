from __future__ import annotations

import re

import httpx

_DOCS_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)", re.I)


def is_google_docs_url(text: str) -> bool:
    t = (text or "").strip().lower()
    return "docs.google.com/document" in t


def extract_google_document_id(url: str) -> str | None:
    m = _DOCS_ID_RE.search(url)
    return m.group(1) if m else None


def fetch_google_doc_plain_text(url: str, *, timeout_s: float = 60.0) -> str:
    """
    Tải nội dung tài liệu dạng plain text qua export của Google.
    Tài liệu phải cho phép xem ít nhất với 'Anyone with the link' (Viewer),
    nếu không sẽ nhận được trang đăng nhập HTML.
    """
    doc_id = extract_google_document_id(url)
    if not doc_id:
        raise ValueError(
            "Không trích được ID từ URL Google Docs. Dùng link dạng "
            "https://docs.google.com/document/d/.../edit"
        )
    export = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        r = client.get(export, headers=headers)
    r.raise_for_status()
    raw = r.text or ""
    head = raw[:800].lower()
    if "<!doctype html" in head or "<html" in head[:200]:
        raise RuntimeError(
            "Không đọc được nội dung Google Docs (trả về HTML). "
            "Kiểm tra tài liệu đã chia sẻ 'Bất kỳ ai có liên kết' — có thể xem (Viewer) chưa, "
            "hoặc thử tải .docx và chọn file trên máy."
        )
    return raw.strip()
