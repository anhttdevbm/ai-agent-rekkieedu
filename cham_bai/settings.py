from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _bootstrap_dotenv() -> None:
    """Ưu tiên .env cạnh EXE (PyInstaller), sau đó cwd và thư mục gốc project."""
    bases: list[Path] = []
    if getattr(sys, "frozen", False):
        bases.append(Path(sys.executable).resolve().parent)
    bases.append(Path.cwd())
    bases.append(Path(__file__).resolve().parent.parent)
    seen: set[str] = set()
    for base in bases:
        p = (base / ".env").resolve()
        if p.is_file():
            key = str(p)
            if key in seen:
                continue
            seen.add(key)
            load_dotenv(p)


_bootstrap_dotenv()

DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _embedded_openrouter_key() -> str:
    try:
        from cham_bai import _embedded_key as emb
    except ImportError:
        return ""
    return (getattr(emb, "OPENROUTER_API_KEY_EMBEDDED", "") or "").strip()


def api_key() -> str:
    # Khi chạy server/Docker: luôn ưu tiên biến môi trường (.env / compose).
    # Key nhúng chỉ dành cho bản EXE (PyInstaller).
    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not key:
        key = _embedded_openrouter_key()
    if not key:
        raise RuntimeError(
            "Thiếu OPENROUTER_API_KEY. Với EXE: build lại sau khi chạy scripts/embed_key_from_env.py "
            "với .env có key. Khi dev: tạo .env hoặc đặt biến môi trường."
        )
    return key


def model(override: str | None = None) -> str:
    if override and override.strip():
        return override.strip()
    return (os.getenv("OPENROUTER_MODEL") or DEFAULT_MODEL).strip()


def http_referer() -> str | None:
    v = (os.getenv("OPENROUTER_HTTP_REFERER") or "").strip()
    return v or None


def app_title() -> str | None:
    v = (os.getenv("OPENROUTER_APP_TITLE") or "").strip()
    return v or None
