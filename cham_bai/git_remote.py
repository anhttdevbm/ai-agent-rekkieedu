from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import httpx

from cham_bai.collector import CollectedBundle, collect_sources

# https://github.com/o/r, có thể kèm /tree/branch/...
_GITHUB_PREFIX = re.compile(
    r"^https?://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)",
    re.I,
)
_GIT_SSH = re.compile(
    r"^git@github\.com:(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?$",
    re.I,
)
_OWNER_SLASH_REPO = re.compile(r"^(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)$")


def normalize_github_repo_url(user_input: str) -> str | None:
    """
    Trả về dạng https://github.com/owner/repo (không có .git, không path phụ).
    None nếu không nhận dạng được.
    """
    s = (user_input or "").strip()
    if not s:
        return None
    s = s.replace("git@github.com:", "https://github.com/")
    if s.startswith("github.com/"):
        s = "https://" + s
    m = _GITHUB_PREFIX.match(s)
    if m:
        return f"https://github.com/{m.group('owner')}/{m.group('repo')}"
    m = _GIT_SSH.match(s.strip())
    if m:
        return f"https://github.com/{m.group('owner')}/{m.group('repo')}"
    m = _OWNER_SLASH_REPO.match(s.strip())
    if m and not s.startswith(("http", "/", "\\")) and ":" not in s:
        return f"https://github.com/{m.group('owner')}/{m.group('repo')}"
    return None


def git_shallow_clone(repo_https_root: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    url = repo_https_root.rstrip("/") + ".git"
    subprocess.run(
        ["git", "clone", "--depth", "1", url, str(dest)],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _download_github_zip(normalized_repo_https: str, dest_zip: Path, *, github_token: str | None) -> None:
    """
    Tải zip repo từ GitHub mà không cần git.
    Dùng /archive/HEAD.zip để lấy default branch.
    """
    url = normalized_repo_https.rstrip("/") + "/archive/HEAD.zip"
    headers = {"User-Agent": "AgentEdu/1.0"}
    t = (github_token or "").strip()
    if t:
        headers["Authorization"] = f"Bearer {t}"
        headers["Accept"] = "application/vnd.github+json"
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        r = client.get(url, headers=headers)
        r.raise_for_status()
        dest_zip.write_bytes(r.content)


def _extract_zip_to_dir(zip_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
    subs = [p for p in out_dir.iterdir() if p.is_dir()]
    if len(subs) == 1:
        return subs[0]
    return out_dir


def fetch_repo_sources_bundle(
    repo_https_root: str,
    *,
    github_token: str | None = None,
    max_total_chars: int = 450_000,
    max_file_chars: int = 120_000,
    max_files: int = 400,
    include_docx_text: bool = False,
    docx_out_warnings: list[str] | None = None,
) -> tuple[CollectedBundle | None, str | None]:
    """
    Clone nhẹ repo rồi thu thập mã nguồn. Trả về (bundle, lỗi).
    """
    normalized = normalize_github_repo_url(repo_https_root)
    if not normalized:
        return None, "Link GitHub không hợp lệ (chỉ hỗ trợ github.com / git@github.com)."

    tmp = Path(tempfile.mkdtemp(prefix="cham_bai_sub_"))
    try:
        git_shallow_clone(normalized, tmp / "repo")
        root = tmp / "repo"
        if not root.is_dir():
            return None, "Clone thất bại: thư mục repo không tồn tại."
        bundle = collect_sources(
            root,
            max_total_chars=max_total_chars,
            max_file_chars=max_file_chars,
            max_files=max_files,
        )
        if include_docx_text:
            from cham_bai.docx_reader import append_docx_plaintext_from_repo_to_bundle

            append_docx_plaintext_from_repo_to_bundle(
                root, bundle, out_warnings=docx_out_warnings
            )
        return bundle, None
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or "").strip() or str(e)
        return None, f"git clone bài nộp lỗi: {err}"
    except FileNotFoundError:
        # Fallback: tải zip (không cần git)
        try:
            zip_p = tmp / "repo.zip"
            _download_github_zip(normalized, zip_p, github_token=github_token)
            root = _extract_zip_to_dir(zip_p, tmp / "repo_zip")
            if not root.is_dir():
                return None, "Tải zip thất bại: thư mục repo không tồn tại."
            bundle = collect_sources(
                root,
                max_total_chars=max_total_chars,
                max_file_chars=max_file_chars,
                max_files=max_files,
            )
            if include_docx_text:
                from cham_bai.docx_reader import append_docx_plaintext_from_repo_to_bundle

                append_docx_plaintext_from_repo_to_bundle(
                    root, bundle, out_warnings=docx_out_warnings
                )
            return bundle, None
        except httpx.HTTPStatusError as e:
            return None, f"Tải zip repo lỗi: {e.response.status_code} {e.response.text[:400]}"
        except Exception as e:
            return None, f"Tải zip repo thất bại: {e}"
    except subprocess.TimeoutExpired:
        return None, "git clone bài nộp quá thời gian chờ."
    finally:
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except OSError:
            pass
