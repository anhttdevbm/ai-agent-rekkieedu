from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any

import httpx

from cham_bai import settings


@dataclass
class ChatMessage:
    role: str
    content: str


def _chat_headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.api_key()}",
        "Content-Type": "application/json",
    }
    ref = settings.http_referer()
    if ref:
        headers["HTTP-Referer"] = ref
    title = settings.app_title()
    if title:
        headers["X-Title"] = title
    return headers


def post_chat_completions(body: dict[str, Any], *, timeout_s: float = 300.0) -> dict[str, Any]:
    with httpx.Client(timeout=timeout_s) as client:
        r = client.post(settings.OPENROUTER_URL, headers=_chat_headers(), json=body)
        r.raise_for_status()
        return r.json()


def complete_chat(
    messages: list[ChatMessage],
    *,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    timeout_s: float = 300.0,
) -> tuple[str, dict[str, Any]]:
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = post_chat_completions(body, timeout_s=timeout_s)

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Phản hồi OpenRouter không hợp lệ: {data!r}") from e

    if not isinstance(content, str):
        raise RuntimeError(f"Nội dung model không phải chuỗi: {type(content)}")

    return content.strip(), data


def _decode_one_data_url(url: str) -> bytes | None:
    m = re.match(r"data:image/[^;]+;base64,(.+)", url.strip(), re.I | re.DOTALL)
    if not m:
        return None
    raw_b64 = re.sub(r"\s+", "", m.group(1))
    try:
        return base64.b64decode(raw_b64, validate=False)
    except Exception:
        return None


def _bytes_from_image_reference(url: str) -> bytes | None:
    u = (url or "").strip()
    if not u:
        return None
    b = _decode_one_data_url(u)
    if b:
        return b
    if u.startswith(("http://", "https://")):
        try:
            with httpx.Client(timeout=90.0, follow_redirects=True) as client:
                r = client.get(u, headers={"User-Agent": "AgentEdu/1.0"})
            r.raise_for_status()
            data = r.content or b""
            if len(data) < 32:
                return None
            ct = (r.headers.get("content-type") or "").lower()
            if (
                data[:8] == b"\x89PNG\r\n\x1a\n"
                or data[:2] == b"\xff\xd8"
                or data[:6] in (b"GIF87a", b"GIF89a")
                or "image" in ct
            ):
                return data
            return None
        except Exception:
            return None
    return None


def _extract_image_blobs_from_message(msg: dict[str, Any]) -> list[bytes]:
    out: list[bytes] = []

    def take_from_url_field(u: Any) -> None:
        if isinstance(u, str):
            b = _bytes_from_image_reference(u)
            if b:
                out.append(b)

    raw = msg.get("images")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                take_from_url_field(item)
                continue
            if not isinstance(item, dict):
                continue
            nested = item.get("image_url") or item.get("imageUrl")
            if isinstance(nested, dict):
                take_from_url_field(nested.get("url") or nested.get("Url"))
            elif isinstance(nested, str):
                take_from_url_field(nested)
            take_from_url_field(item.get("url"))
            b64 = item.get("b64_json")
            if isinstance(b64, str):
                try:
                    dec = base64.b64decode(re.sub(r"\s+", "", b64), validate=False)
                    if dec:
                        out.append(dec)
                except Exception:
                    pass

    content = msg.get("content")
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            ptype = str(part.get("type", "")).lower()
            if ptype in ("image_url", "image"):
                iu = part.get("image_url") or part.get("imageUrl")
                if isinstance(iu, dict):
                    take_from_url_field(iu.get("url") or iu.get("Url"))
                elif isinstance(iu, str):
                    take_from_url_field(iu)
            if ptype == "text":
                t = part.get("text")
                if isinstance(t, str) and "data:image/" in t:
                    for u in _extract_data_urls_from_string(t):
                        take_from_url_field(u)

    cstr = msg.get("content")
    if isinstance(cstr, str) and "data:image/" in cstr:
        for u in _extract_data_urls_from_string(cstr):
            take_from_url_field(u)

    return out


def _extract_data_urls_from_string(s: str) -> list[str]:
    """Bắt các chuỗi data:image/...;base64,... trong JSON hoặc văn bản nhúng."""
    out: list[str] = []
    pos = 0
    while True:
        i = s.find("data:image/", pos)
        if i < 0:
            break
        j = s.find("base64,", i)
        if j < 0:
            pos = i + 1
            continue
        k = j + 7
        while k < len(s) and s[k] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r \t":
            k += 1
        raw = s[i:k]
        cleaned = re.sub(r"\s+", "", raw)
        if len(cleaned) > 200:
            out.append(cleaned)
        pos = k

    return out


def _deep_scan_response_for_image_blobs(data: Any) -> list[bytes]:
    found_urls: list[str] = []
    seen_u: set[str] = set()

    def walk(o: Any) -> None:
        if isinstance(o, str):
            for u in _extract_data_urls_from_string(o):
                if u not in seen_u:
                    seen_u.add(u)
                    found_urls.append(u)
            return
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    out: list[bytes] = []
    seen_sig: set[bytes] = set()
    for u in found_urls:
        b = _decode_one_data_url(u)
        if not b or len(b) < 80:
            continue
        sig = b[:96]
        if sig in seen_sig:
            continue
        seen_sig.add(sig)
        out.append(b)
    return out


def generate_images_from_prompt(
    prompt: str,
    *,
    model: str,
    timeout_s: float = 180.0,
) -> list[bytes]:
    """
    Gọi OpenRouter với model hỗ trợ output image (xem docs: modalities).
    Trả về danh sách ảnh (bytes PNG/JPEG…); rỗng nếu model/plan không trả ảnh.
    """
    for modalities in (["image", "text"], ["text", "image"], ["image"]):
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": modalities,
            "max_tokens": 4096,
            "temperature": 0.35,
        }
        try:
            data = post_chat_completions(body, timeout_s=timeout_s)
        except httpx.HTTPStatusError:
            continue
        try:
            choice0 = data["choices"][0]
        except (KeyError, IndexError, TypeError):
            continue
        msg = choice0.get("message") if isinstance(choice0, dict) else None
        blobs: list[bytes] = []
        if isinstance(msg, dict):
            blobs = _extract_image_blobs_from_message(msg)
        if not blobs and isinstance(choice0, dict):
            blobs = _extract_image_blobs_from_message(choice0)
        if not blobs:
            blobs = _deep_scan_response_for_image_blobs(data)
        if blobs:
            return blobs
    return []
