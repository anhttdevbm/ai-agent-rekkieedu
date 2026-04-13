from __future__ import annotations

from pathlib import Path

from cham_bai.docx_reader import DocxContent, extract_docx, github_urls_from_plain_text
from cham_bai.gdocs_reader import fetch_google_doc_plain_text, is_google_docs_url


def load_assignment(ref: str) -> DocxContent:
    """
    Đề bài: file .docx trên máy hoặc link Google Docs (xem được công khai / anyone with link).
    """
    s = (ref or "").strip()
    if not s:
        raise ValueError("Chưa chỉ định đề bài.")

    if is_google_docs_url(s):
        plain = fetch_google_doc_plain_text(s)
        urls = github_urls_from_plain_text(plain)
        return DocxContent(plain_text=plain, github_repo_urls=urls)

    p = Path(s)
    if p.is_file() and p.suffix.lower() == ".docx":
        return extract_docx(str(p.resolve()))

    raise ValueError(
        "Đề bài cần là file .docx hợp lệ hoặc link Google Docs "
        "(https://docs.google.com/document/d/...)."
    )
