from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from cham_bai.collector import CollectedBundle, collect_sources, format_bundle_for_prompt
from cham_bai.git_remote import git_shallow_clone, normalize_github_repo_url


def fetch_template_bundle(repo_url: str) -> tuple[CollectedBundle | None, str | None]:
    """
    Clone nhẹ repo mẫu (depth 1). Trả về (bundle, lỗi).
    """
    normalized = normalize_github_repo_url(repo_url)
    if not normalized:
        return None, "URL GitHub không hợp lệ để clone."

    tmp = Path(tempfile.mkdtemp(prefix="cham_bai_tpl_"))
    try:
        git_shallow_clone(normalized, tmp / "repo")
        root = tmp / "repo"
        if not root.is_dir():
            return None, "Clone thất bại: thư mục repo không tồn tại."
        bundle = collect_sources(
            root,
            max_total_chars=200_000,
            max_file_chars=80_000,
            max_files=200,
        )
        return bundle, None
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or "").strip() or str(e)
        return None, f"git clone lỗi: {err}"
    except FileNotFoundError:
        return None, "Không tìm thấy lệnh 'git' trên PATH."
    except subprocess.TimeoutExpired:
        return None, "git clone quá thời gian chờ."
    finally:
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except OSError:
            pass


def format_template_context(bundle: CollectedBundle | None) -> str:
    if not bundle or not bundle.files:
        return "(Không có nội dung template hoặc template rỗng.)"
    return format_bundle_for_prompt(bundle)
