from __future__ import annotations

import re


def youtube_video_id_from_url(url: str) -> str | None:
    u = (url or "").strip()
    if not u:
        return None
    m = re.search(
        r"(?:youtu\.be/|youtube\.com/watch\?v=|youtube\.com/embed/"
        r"|youtube\.com/shorts/|youtube\.com/live/)([\w-]{11})",
        u,
        re.I,
    )
    if m:
        return m.group(1)
    m = re.search(r"youtube\.com/watch\?.*[&?]v=([\w-]{11})", u, re.I)
    return m.group(1) if m else None


def fetch_youtube_transcript_plain(url: str, *, max_chars: int = 14000) -> tuple[str | None, str]:
    """
    Lấy phụ đề YouTube dạng văn bản (không có hình).
    Trả về (text, lỗi): nếu thành công, lỗi là chuỗi rỗng.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore[import-untyped]
    except ImportError:
        return None, (
            "Chưa cài thư viện youtube-transcript-api. Chạy: pip install youtube-transcript-api"
        )

    vid = youtube_video_id_from_url(url)
    if not vid:
        return None, "Không nhận diện được ID video YouTube. Dùng link dạng youtube.com/watch?v=... hoặc youtu.be/..."

    try:
        data = YouTubeTranscriptApi.get_transcript(vid, languages=["vi", "en"])
    except Exception as e:
        return None, (
            f"Không lấy được phụ đề (video cần có phụ đề việt hoặc anh, không tắt transcript): {e}"
        )

    lines = [str(item.get("text", "")).strip() for item in data if item.get("text")]
    text = "\n".join(lines).strip()
    if not text:
        return None, "Phụ đề rỗng."

    if len(text) > max_chars:
        text = text[: max_chars - 80] + " … [Đoạn phụ đề đã rút gọn để gửi model — ưu tiên phần đầu video]."

    return text, ""
