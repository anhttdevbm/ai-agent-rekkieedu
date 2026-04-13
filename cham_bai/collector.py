from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_IGNORE_DIR_NAMES = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "dist",
        "build",
        "target",
        ".idea",
        ".vs",
        ".vscode",
        "vendor",
        ".gradle",
        ".nuget",
        ".cursor",
    }
)

DEFAULT_IGNORE_SUFFIXES = frozenset(
    {
        ".pyc",
        ".pyo",
        ".so",
        ".dll",
        ".exe",
        ".bin",
        ".o",
        ".a",
        ".lib",
        ".obj",
        ".class",
        ".jar",
        ".war",
        ".zip",
        ".7z",
        ".rar",
        ".gz",
        ".tar",
        ".bz2",
        ".xz",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".pdf",
        ".mp4",
        ".mp3",
        ".wav",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".sqlite",
        ".db",
    }
)

# Ưu tiên mở rộng hay gặp trong bài đại học; file khác vẫn thử đọc text nếu nhỏ.
CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".ipynb",
        ".java",
        ".c",
        ".h",
        ".cpp",
        ".cc",
        ".cxx",
        ".hpp",
        ".cs",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".kt",
        ".swift",
        ".scala",
        ".m",
        ".mm",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".vue",
        ".svelte",
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".bat",
        ".cmd",
        ".md",
        ".txt",
        ".rst",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".xml",
        ".gradle",
        ".properties",
        ".env.example",
        ".gitignore",
    }
)


@dataclass
class CollectedBundle:
    root: Path
    files: list[tuple[str, str]] = field(default_factory=list)
    truncated: bool = False
    skipped_binary: list[str] = field(default_factory=list)
    skipped_large: list[str] = field(default_factory=list)


def _is_ignored_dir(name: str) -> bool:
    if name in DEFAULT_IGNORE_DIR_NAMES:
        return True
    if name.startswith(".") and name not in {".gitignore", ".env.example"}:
        # Ẩn .foo nhưng giữ .gitignore nếu nằm trong list file — thực tế .gitignore là file
        pass
    return False


def collect_sources(
    root: str | Path,
    *,
    max_total_chars: int = 450_000,
    max_file_chars: int = 120_000,
    max_files: int = 400,
) -> CollectedBundle:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"Không phải thư mục: {root_path}")

    bundle = CollectedBundle(root=root_path)
    total = 0

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        dp = Path(dirpath)
        # prune ignored dirs
        dirnames[:] = [d for d in dirnames if not _is_ignored_dir(d)]

        rel_dir = dp.relative_to(root_path)
        for fn in sorted(filenames):
            fp = dp / fn
            if not fp.is_file():
                continue
            rel = str(rel_dir / fn).replace("\\", "/")
            if rel.startswith("./"):
                rel = rel[2:]

            suf = fp.suffix.lower()
            name_lower = fp.name.lower()
            if suf in DEFAULT_IGNORE_SUFFIXES:
                continue
            if fp.name.startswith(".") and fp.name not in {".gitignore", ".env.example"}:
                continue

            try:
                raw = fp.read_bytes()
            except OSError:
                continue

            if b"\x00" in raw[:8192]:
                bundle.skipped_binary.append(rel)
                continue

            if suf in CODE_EXTENSIONS or name_lower in {"dockerfile", "makefile", "gemfile"}:
                pass
            elif len(raw) > 512_000:
                bundle.skipped_large.append(rel)
                continue

            text = _decode_text(raw)
            if text is None:
                bundle.skipped_binary.append(rel)
                continue

            if len(text) > max_file_chars:
                text = text[: max_file_chars] + "\n\n[... TRUNCATED FILE ...]\n"
            block = f"===== FILE: {rel} =====\n{text}\n"
            if total + len(block) > max_total_chars:
                bundle.truncated = True
                break
            bundle.files.append((rel, text))
            total += len(block)
            if len(bundle.files) >= max_files:
                bundle.truncated = True
                break

    return bundle


def _decode_text(raw: bytes) -> str | None:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def format_bundle_for_prompt(bundle: CollectedBundle) -> str:
    chunks: list[str] = []
    for rel, text in bundle.files:
        chunks.append(f"===== FILE: {rel} =====\n{text.rstrip()}\n")
    body = "\n".join(chunks)
    if bundle.truncated:
        body += "\n[NOTE: Một số file đã bị cắt bớt do giới hạn kích thước.]\n"
    if bundle.skipped_binary:
        body += "\n[NOTE: Bỏ qua file nhị phân / không đọc được: "
        body += ", ".join(bundle.skipped_binary[:40])
        if len(bundle.skipped_binary) > 40:
            body += ", ..."
        body += "]\n"
    if bundle.skipped_large:
        body += "\n[NOTE: Bỏ qua file quá lớn: "
        body += ", ".join(bundle.skipped_large[:20])
        body += "]\n"
    return body
