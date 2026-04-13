from __future__ import annotations

import re
from dataclasses import dataclass

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT

GITHUB_URL_RE = re.compile(
    r"https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)(?:/(?:tree|blob)/[\w./-]+)?/?",
    re.IGNORECASE,
)
GIT_SSH_RE = re.compile(
    r"git@github\.com:(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?$",
    re.IGNORECASE,
)


@dataclass
class DocxContent:
    plain_text: str
    github_repo_urls: list[str]


def _normalize_repo_url(owner: str, repo: str) -> str:
    owner, repo = owner.strip(), repo.strip().rstrip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"https://github.com/{owner}/{repo}"


def _urls_from_word_hyperlinks(doc: Document) -> list[str]:
    out: list[str] = []
    try:
        for rel in doc.part.rels.values():
            if rel.reltype != RT.HYPERLINK:
                continue
            t = (rel.target_ref or "").strip()
            if t:
                out.append(t)
    except (KeyError, AttributeError, TypeError):
        pass
    return out


def github_urls_from_plain_text(*blobs: str) -> list[str]:
    """Thu thập link GitHub từ một hoặc nhiều chuỗi (đoạn văn, URL...)."""
    seen: set[str] = set()
    urls: list[str] = []
    for blob in blobs:
        _register_github_urls(blob, seen, urls)
    return urls


def _register_github_urls(blob: str, seen: set[str], urls: list[str]) -> None:
    for m in GITHUB_URL_RE.finditer(blob):
        url = _normalize_repo_url(m.group("owner"), m.group("repo"))
        if url not in seen:
            seen.add(url)
            urls.append(url)
    for m in GIT_SSH_RE.finditer(blob.strip()):
        url = _normalize_repo_url(m.group("owner"), m.group("repo"))
        if url not in seen:
            seen.add(url)
            urls.append(url)


def extract_docx(path: str) -> DocxContent:
    doc = Document(path)
    parts: list[str] = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    for table in doc.tables:
        rows: list[str] = []
        for row in table.rows:
            cells = [(c.text or "").strip() for c in row.cells]
            rows.append(" | ".join(cells))
        if rows:
            parts.append("\n".join(rows))

    plain = "\n".join(parts)
    seen: set[str] = set()
    urls: list[str] = []
    for blob in [plain, *_urls_from_word_hyperlinks(doc)]:
        _register_github_urls(blob, seen, urls)

    return DocxContent(plain_text=plain, github_repo_urls=urls)
