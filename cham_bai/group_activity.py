from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
import io
import html as _html
from openpyxl import load_workbook

from cham_bai.gdocs_reader import (
    fetch_google_doc_plain_text,
    fetch_google_sheet_plain_text,
    is_google_docs_url,
    is_google_sheet_url,
)
from cham_bai.openrouter import complete_chat_raw
from cham_bai.schemas import parse_llm_json


@dataclass
class GroupGradeParams:
    report_url: str
    video_url: str
    video_notes: str
    yescribe_token: str
    model: str


_SYSTEM = """Bạn là giảng viên chấm HOẠT ĐỘNG NHÓM.

Đầu vào gồm:
- BÁO CÁO (từ Google Docs/Excel đã trích text)
- LINK VIDEO (chỉ là link)
- GHI CHÚ VIDEO (nếu có): có thể là transcript/tóm tắt do người chấm cung cấp

Nguyên tắc:
1) Tuyệt đối KHÔNG bịa nội dung video nếu chỉ có link mà không có transcript/ghi chú. Khi thiếu dữ liệu video, phải ghi rõ trong kết quả.
2) Đánh giá 2 phần:
   - Hoạt động nhóm trong video: mức độ phối hợp, phân công, nhóm trưởng điều phối.
   - Báo cáo: nhóm trưởng có báo cáo đúng/đủ theo nội dung nhóm đã làm (đối chiếu theo ghi chú video nếu có).
3) Ngôn ngữ: tiếng Việt, ngắn gọn, thực tế.

CHỈ trả về một JSON hợp lệ theo schema:
{
  "score": 0-100,
  "comment": "2-4 câu tiếng Việt, không bullet, không markdown",
  "video_evidence": "du" | "thieu",
  "leader_activity_ok": true|false|"khong_ro",
  "leader_report_match": true|false|"khong_ro",
  "notes": "1-2 câu nếu thiếu dữ liệu video/report"
}
"""

_YT_ID_RE = re.compile(r"(?:v=|/shorts/|youtu\.be/)(?P<id>[A-Za-z0-9_-]{6,})", re.I)


def _extract_youtube_id(url: str) -> str | None:
    m = _YT_ID_RE.search(url or "")
    return (m.group("id").strip() if m else None)


def _strip_xml_tags(s: str) -> str:
    # keep only text nodes content (very basic)
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def fetch_youtube_transcript_text(video_url: str) -> tuple[str, list[str]]:
    """
    Best-effort: dùng timedtext public endpoint. Nếu video không có caption public -> trả rỗng.
    """
    warns: list[str] = []
    vid = _extract_youtube_id(video_url)
    if not vid:
        return "", []
    # thử tiếng Việt trước, rồi fallback English + auto
    candidates = [
        f"https://www.youtube.com/api/timedtext?lang=vi&v={vid}",
        f"https://www.youtube.com/api/timedtext?lang=en&v={vid}",
        f"https://www.youtube.com/api/timedtext?v={vid}",
    ]
    headers = {"User-Agent": "AgentEdu/1.0"}
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for u in candidates:
            try:
                r = client.get(u, headers=headers)
                if r.status_code != 200:
                    continue
                t = (r.text or "").strip()
                if not t or "<transcript" not in t.lower():
                    continue
                text = _strip_xml_tags(t)
                # timedtext thường rất ngắn nếu không có caption
                if len(text) >= 200:
                    if "lang=vi" in u:
                        warns.append("Đã lấy transcript YouTube (vi) từ timedtext.")
                    elif "lang=en" in u:
                        warns.append("Đã lấy transcript YouTube (en) từ timedtext.")
                    else:
                        warns.append("Đã lấy transcript YouTube từ timedtext.")
                    return text, warns
            except Exception:
                continue
    warns.append("Không lấy được transcript YouTube (video không có caption public hoặc bị chặn).")
    return "", warns


def fetch_yescribe_transcript_text(
    video_url: str, *, yescribe_token: str = ""
) -> tuple[str, list[str]]:
    """
    Lấy transcript qua API yescribe.ai (nếu có token/khả dụng).
    Endpoint người dùng đưa: /api/v1/yescribe/record/getVideoDetail
    """
    warns: list[str] = []
    u = (video_url or "").strip()
    if not u:
        return "", warns
    vid = _extract_youtube_id(u)
    payloads: list[dict[str, Any]] = []
    # best-effort nhiều key vì không có docs chính thức
    payloads.append({"videoUrl": u})
    if vid:
        payloads.append({"videoId": vid})
        payloads.append({"url": u, "videoId": vid})
    payloads.append({"url": u})

    headers = {"User-Agent": "AgentEdu/1.0", "Content-Type": "application/json"}
    t = (yescribe_token or "").strip()
    if t:
        headers["Authorization"] = t if t.lower().startswith("bearer ") else ("Bearer " + t)

    endpoint = "https://api.yescribe.ai/api/v1/yescribe/record/getVideoDetail"
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for p in payloads:
            try:
                r = client.post(endpoint, headers=headers, json=p)
                if r.status_code != 200:
                    continue
                data = r.json()
            except Exception:
                continue
            try:
                if int(data.get("code", 0)) != 200:
                    continue
            except Exception:
                continue
            d = data.get("data")
            if not isinstance(d, dict):
                continue
            ts = d.get("tranScript") or d.get("transcript") or d.get("tran_script")
            if not isinstance(ts, list) or not ts:
                continue
            lines: list[str] = []
            for item in ts[:1200]:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                start = item.get("start")
                try:
                    st = float(start)
                    mm = int(st // 60)
                    ss = int(st % 60)
                    prefix = f"{mm:02d}:{ss:02d} "
                except Exception:
                    prefix = ""
                lines.append(prefix + text)
            body = "\n".join(lines).strip()
            if len(body) >= 200:
                warns.append("Đã lấy transcript từ Yescribe.")
                return body, warns
            break

    warns.append("Không lấy được transcript từ Yescribe (thiếu token, không hỗ trợ video, hoặc bị chặn).")
    return "", warns


def _wb_to_text(xlsx_bytes: bytes, *, max_cells: int = 2500) -> str:
    wb = load_workbook(filename=io.BytesIO(xlsx_bytes), data_only=True)  # type: ignore[name-defined]
    parts: list[str] = []
    cells = 0
    for ws in wb.worksheets[:8]:
        parts.append(f"=== SHEET: {ws.title} ===")
        for row in ws.iter_rows(values_only=True):
            if cells >= max_cells:
                parts.append("[... TRUNCATED ...]")
                return "\n".join(parts).strip()
            vals = []
            for v in row:
                if v is None:
                    vals.append("")
                else:
                    s = str(v).strip()
                    vals.append(s)
            line = " | ".join(x for x in vals if x != "")
            if line.strip():
                parts.append(line)
            cells += 1
    return "\n".join(parts).strip()


def fetch_report_text(report_url: str) -> tuple[str, list[str]]:
    url = (report_url or "").strip()
    warnings: list[str] = []
    if not url:
        return "", ["Thiếu link báo cáo (sẽ chỉ đánh giá video nếu có dữ liệu)."]
    if is_google_docs_url(url) and not is_google_sheet_url(url):
        try:
            return fetch_google_doc_plain_text(url), warnings
        except Exception as e:
            return "", [f"Lỗi đọc Google Docs: {e}"]
    if is_google_sheet_url(url):
        try:
            return fetch_google_sheet_plain_text(url), warnings
        except Exception as e:
            return "", [f"Lỗi đọc Google Sheets: {e}"]

    # Excel URL (.xlsx)
    if re.search(r"\.xlsx(\?|$)", url, flags=re.I):
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                r = client.get(url, headers={"User-Agent": "AgentEdu/1.0"})
            r.raise_for_status()
            raw = r.content or b""
            if not raw:
                return "", ["Link Excel trả về rỗng."]
            return _wb_to_text(raw), warnings
        except Exception as e:
            return "", [f"Lỗi tải/đọc Excel: {e}"]

    return "", ["Link báo cáo chưa hỗ trợ (cần Google Docs/Sheets hoặc URL .xlsx)."]


def grade_group_activity(params: GroupGradeParams) -> dict[str, Any]:
    report_text, warns = fetch_report_text(params.report_url)
    video_url = (params.video_url or "").strip()
    video_notes = (params.video_notes or "").strip()
    if video_url and not video_notes:
        t2, w2 = fetch_yescribe_transcript_text(video_url, yescribe_token=params.yescribe_token)
        warns.extend(w2)
        if t2:
            video_notes = t2
        else:
            t, w = fetch_youtube_transcript_text(video_url)
            warns.extend(w)
            if t:
                video_notes = t

    user_parts = [
        {
            "type": "text",
            "text": (
                "BÁO CÁO (text trích):\n"
                + (report_text.strip() or "(trống/không đọc được)")
                + "\n\nLINK VIDEO:\n"
                + (video_url or "(trống)")
                + "\n\nGHI CHÚ VIDEO (nếu có):\n"
                + (video_notes or "(không có)")
                + ("\n\nCẢNH BÁO:\n" + "\n".join(warns) if warns else "")
            ),
        }
    ]

    text, _ = complete_chat_raw(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user_parts}],
        model=params.model,
        temperature=0.2,
        max_tokens=650,
        timeout_s=300.0,
    )
    try:
        blob = parse_llm_json(text)
        if isinstance(blob, dict):
            return blob
    except Exception:
        try:
            # fallback: đôi khi provider trả hẳn dict ở dạng string Python-ish hoặc rác
            blob2 = json.loads((text or "").strip())
            if isinstance(blob2, dict):
                return blob2
        except Exception:
            pass
    return {
        "score": 0,
        "comment": "Không chấm được do model không trả JSON hợp lệ.",
        "video_evidence": "thieu",
        "leader_activity_ok": "khong_ro",
        "leader_report_match": "khong_ro",
        "notes": (text or "")[:1200],
    }

