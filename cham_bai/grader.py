from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
import re

from cham_bai.collector import CollectedBundle, format_bundle_for_prompt
from cham_bai.docx_reader import DocxContent
from cham_bai.github_template import format_template_context
from cham_bai.openrouter import ChatMessage, complete_chat
from cham_bai.schemas import GradePayload, coalesce_grade, parse_llm_json


_SYSTEM_PROMPT_HEAD = """Bạn là trợ giảng chấm bài lập trình bậc đại học.

Phạm vi ĐIỂM và NHẬN XÉT (bắt buộc):
• Chỉ dựa trên (A) **bài tập đầu giờ** — mã trong khối «MÃ NGUỒN HỌC VIÊN — BÀI TẬP ĐẦU GIỜ» (bài nộp chính), và (B) **báo cáo** — văn bản trong khối «BÁO CÁO» (GitHub: DOCX trích / repo; Google Docs: nội dung export; OneDrive/SharePoint: văn bản trích từ Word chia sẻ) hoặc trong đề bài nếu có.
• Nếu **không có** mã bài tập đầu giờ (khối đó rỗng) thì `score` và `comment` **chỉ** theo **báo cáo** (và vẫn xử lý `mini_project_present` từ repo báo cáo nếu có).
• **Bài tập đầu giờ quan trọng hơn báo cáo:** khi cả hai đều có đủ dữ liệu để chấm, trọng số gợi ý khoảng **65–75%** cho bài tập đầu giờ và **25–35%** cho báo cáo (làm tròn thành một số điểm 0–100 nguyên). Nếu chỉ có một phần thì toàn bộ `score` phản ánh phần đó; nếu thiếu báo cáo khi đề bắt buộc thì phản ánh trong điểm/comment phần báo cáo, không bịa.
• **Mini project:** KHÔNG tính vào `score`, KHÔNG được đánh giá chất lượng trong `comment`. Chỉ kết luận `mini_project_present` là **có**, **không**, hoặc **không_rõ** dựa trên **đề bài** và bằng chứng trong **repo báo cáo** (mã kèm repo) nếu có — không dùng để chấm điểm.

Chấm lỏng tay: ưu tiên chạy được và đáp ứng ý chính; không hạ điểm mạnh vì lệch nhãn chủ đề khi đề và template khác nhau mà sinh viên làm đúng theo template (xem mục 5).

Quy tắc:
1) Đọc “ĐỀ BÀI” (.docx / Google Docs). Khối «BÁO CÁO» (nếu có): nội dung báo cáo (Google Docs đã export văn bản; OneDrive/SharePoint đã trích từ Word); với GitHub, phần `_docx_text/` và văn bản báo cáo dùng cho điểm; mã mini trong repo chỉ hỗ trợ `mini_project_present`, không vào `score`/`comment`.
2) Báo cáo DOCX: đánh giá mức vừa phải — bài toán, thiết kế/triển khai, kết quả, hạn chế; không soi văn phong hoàn hảo. Nếu không có trích DOCX thì không bịa.
3) Chỉ chấm phần đề nêu rõ; không bịa thêm hạng mục. Nếu đề chỉ yêu cầu (ví dụ) sửa và xóa thì không trừ vì không có thêm / danh sách đầy đủ trừ khi đề ghi rõ.
4) Không soi chữ trong alert / thông báo: nếu cùng ý (xác nhận xóa, báo thành công cập nhật/xóa) thì chấp nhận; không trừ nặng vì khác vài từ so với đề nếu logic đúng.
5) Đề vs template vs bài nộp (chấm lỏng tay): Khi đề nói một chủ đề (ví dụ quản lý sản phẩm) nhưng template GitHub là chủ đề khác (ví dụ danh bạ, contact) và sinh viên làm giống template thì coi là bài hợp lệ theo khung mẫu. Không coi là sai chủ đề nghiêm trọng. Ánh xạ tương đương giữa các trường dữ liệu và validate. Với bài chạy ổn, có sửa/xóa và validate đúng hướng theo cách làm đó, điểm mục tiêu khoảng 65–78, thường quanh 70 (ví dụ 68–74); chỉ dưới 50 khi thiếu hẳn phần cốt lõi đề yêu cầu hoặc lỗi nặng — áp dụng cho **phần bài tập đầu giờ** khi tách nhận định.
6) Template không thay thế đề khi **xung đột chức năng** (đề bắt buộc tính năng X mà code không có). Khi xung đột chỉ là **tên miền / nhãn** (sản phẩm vs contact) nhưng trên thực tế cùng một bài tập template → áp mục 5, chấm rộng.
7) File .md / README do sinh viên tự thêm: không dùng để mở rộng phạm vi đề; không trừ vì “tài liệu khác đề” trừ khi đề bắt nộp. Có thể ghi nhẹ trong integrity_notes nếu liên quan AI.
"""

_RULE8_COMMENT_DEFAULT = """8) Trường "comment": một đoạn văn ngắn duy nhất (2–4 câu, tối đa khoảng 600 ký tự), tiếng Việt. Cấm gạch đầu dòng và cấm định dạng markdown. Chỉ tóm tắt **bài tập đầu giờ** và **báo cáo** (đạt/chưa đạt); **cấm** nhắc chất lượng mini project, **cấm** dùng comment để thay thế `mini_project_present`.
"""

_RULE8_COMMENT_HACKATHON = """8) Trường "comment" (chấm Hackathon / đề thực hành có **câu hỏi đánh số** trong đề):
- Bắt buộc đối chiếu theo **số thứ tự câu trong đề** (vd. "1.", "2.", … hoặc đúng cách đề đánh số). Với mỗi câu có yêu cầu hành động rõ (CREATE/INSERT/UPDATE/DELETE/SELECT…), ghi **một dòng** theo mẫu: `Câu <số>: đúng | sai | thiếu | không đối chiếu được — <một cụm ngắn>` (cụm ngắn: vì sao sai, thiếu phần nào, hoặc vì sao không tìm thấy trong bài nộp — không bịa nếu không có bằng chứng).
- **Cấm** mở bài bằng kiểu tóm tắt chung chung hoặc khen lan man, ví dụ: "Bài làm hoàn thành tốt phần …", "Hoàn thành tốt …", "Làm tốt phần …", "Nhìn chung …", "Đã làm đầy đủ các phần …" rồi mới vào chi tiết. **Không** viết đoạn dạng liệt kê năng lực chung (tạo bảng/chèn/UPDATE/DELETE/SELECT…) trước khi nêu từng câu theo số đề.
- Ưu tiên liệt kê **các câu sai hoặc thiếu hoặc không đối chiếu được**; chỉ khi đã đối chiếu đủ và các câu còn lại đều đúng, được kết bằng **một câu ngắn**: "Các câu còn lại: đúng theo đề."
- Phần **báo cáo** (nếu đề có yêu cầu và có khối BÁO CÁO để chấm): sau các dòng câu hỏi thực hành, thêm **tối đa 1 dòng**: `Báo cáo: đúng | thiếu | không đối chiếu được — ...` (không mô tả chất lượng mini project).
- Tiếng Việt; cho phép xuống dòng; **tối đa 1200 ký tự** (hệ thống sẽ cắt nếu vượt); không markdown (không ```, không ##).
"""

_SYSTEM_PROMPT_TAIL = """9) Cho điểm 0–100 (số nguyên), phù hợp mức độ lỏng tay ở mục 3–6 và trọng số bài tập đầu giờ ưu tiên hơn báo cáo.

10) integrity_verdict:
   - "pass": không có dấu hiệu đáng kể cho thấy bài được tạo bởi công cụ AI thay cho học viên (chấp nhận tra cứu tài liệu, snippet ngắn).
   - "suspicious": có một số dấu hiệu mâu thuẫn / quá đồng nhất / giống văn bản AI nhưng KHÔNG đủ để kết luận.
   - "likely_ai": có nhiều dấu hiệu mạnh (ví dụ: toàn bộ file giống văn phong tutorial, over-comment kiểu giảng viên AI, cấu trúc không khớp trình độ, trùng khớp bất thường với template ngoài đề, v.v.). Lưu ý: đây chỉ là đánh giá heuristic, không phải bằng chứng pháp lý.
11) integrity_confidence_0_100: độ tin cậy (0–100) cho verdict. Nếu pass thì thường thấp–trung; chỉ cao khi có lý do rõ.
12) integrity_notes: danh sách ngắn các lý do (tiếng Việt), tối đa 3 mục.

CHỈ trả về một JSON hợp lệ duy nhất, không thêm markdown ngoài JSON. Schema:
{
  "score": <0-100>,
  "comment": "<nhận xét tiếng Việt — chỉ bài tập đầu giờ + báo cáo>",
  "mini_project_present": "có" | "không" | "không_rõ",
  "integrity_verdict": "pass" | "suspicious" | "likely_ai",
  "integrity_confidence_0_100": <0-100>,
  "integrity_notes": ["...", "..."],
  "rubric": { "tieu_chi": diem, ... }
}
Trong đó rubric là tùy chọn; nếu không chắc hãy dùng {} hoặc bỏ trường (dùng {} an toàn hơn). Trường mini_project_present là bắt buộc (một trong ba chuỗi trên).
"""


def system_prompt_for_comment_style(comment_style: str) -> str:
    cs = (comment_style or "hackathon_per_question").strip().lower()
    if cs not in ("default", "hackathon_per_question"):
        cs = "hackathon_per_question"
    r8 = _RULE8_COMMENT_HACKATHON if cs == "hackathon_per_question" else _RULE8_COMMENT_DEFAULT
    return _SYSTEM_PROMPT_HEAD + r8 + _SYSTEM_PROMPT_TAIL


# Giữ tên hằng để tương thích đọc mã; bằng chế độ mặc định hiện tại (nhận xét theo từng câu đề).
SYSTEM_PROMPT = system_prompt_for_comment_style("hackathon_per_question")


@dataclass
class GradeOutcome:
    payload: GradePayload
    final_score: int
    final_comment: str
    applied_ai_penalty: bool
    raw_model_text: str
    openrouter_meta: dict[str, Any]


DOMAIN_MISMATCH_SCORE_CAP = 20


def _looks_domain_mismatch(comment: str) -> bool:
    s = (comment or "").lower()
    if not s:
        return False
    # Chỉ coi là sai đề nghiêm trọng khi có các cụm phủ định mạnh.
    strong_markers = [
        r"sai\s+ch[uủ]\s+đ[eề]",
        r"kh[oô]ng\s+li[êe]n\s+quan\s+[đd][ếe]n\s+đ[eề]",
        r"kh[aá]c\s+ho[àa]n\s+to[aà]n\s+so\s+v[ớo]i\s+đ[eề]",
        r"ho[aà]n\s+to[aà]n\s+kh[aá]c\s+(đ[eề]|y[êe]u\s*c[ầa]u)",
        r"kh[oô]ng\s+th[uự]c\s+hi[eệ]n\s+theo\s+đ[eề]",
        r"kh[oô]ng\s+l[aà]m\s+theo\s+đ[eề]",
        r"kh[oô]ng\s+[đd][úu]ng\s+entity",
        r"sai\s+entity",
        r"kh[oô]ng\s+đ[uủ]\s+entity",
        r"nh[aầ]m\s+đ[eề]",
    ]
    if any(re.search(p, s, re.I) for p in strong_markers):
        return True

    # Fallback chặt: phải có đồng thời "thay vì ... theo đề" + ngữ cảnh phủ định mạnh.
    has_instead = bool(re.search(r"thay\s+v[ìi]\s+.*\s+theo\s+đ[eề]", s, re.I))
    has_negative = bool(
        re.search(
            r"(kh[oô]ng\s+th[uự]c\s+hi[eệ]n|kh[oô]ng\s+[đd][áa]p\s+[ứu]ng|kh[oô]ng\s+c[oó]\s+b[aà]i|to[aà]n\s+b[oộ]\s+kh[oô]ng)",
            s,
            re.I,
        )
    )
    if has_instead and has_negative:
        return True

    # Nếu nhận xét tổng thể tích cực/đầy đủ thì không cap 20 chỉ vì vài cụm "không khớp đề" cục bộ.
    positive_markers = [
        r"b[aà]i\s+l[aà]m\s+(kh[aá]|r[aấ]t\s+)?(đ[aầ]y\s+đ[uủ]|ho[aà]n\s+chỉnh|t[ốo]t)",
        r"h[ầa]u\s+h[eế]t\s+(đ[uú]ng|ch[ií]nh\s+x[aá]c)",
        r"ph[ầa]n\s+l[ớo]n\s+(đ[uú]ng|ch[ií]nh\s+x[aá]c)",
    ]
    if any(re.search(p, s, re.I) for p in positive_markers):
        return False
    return False


def build_user_prompt(
    doc: DocxContent,
    submission_bundle: CollectedBundle,
    template_bundle: CollectedBundle | None,
    *,
    template_error: str | None,
    report_bundle: CollectedBundle | None = None,
    comment_style: str = "hackathon_per_question",
) -> str:
    assignment_plain_text = doc.plain_text.strip()
    urls = doc.github_repo_urls
    submission_context = format_bundle_for_prompt(submission_bundle)
    template_context_text = format_template_context(template_bundle)

    parts: list[str] = []
    parts.append("## ĐỀ BÀI (trích từ file .docx hoặc Google Docs)\n")
    parts.append(assignment_plain_text)
    parts.append("\n\n## LINK GITHUB TÌM ĐƯỢC TRONG ĐỀ\n")
    if urls:
        parts.append("\n".join(urls))
    else:
        parts.append("(Không tìm thấy link github.com rõ ràng.)")

    if template_error:
        parts.append("\n\n## GHI CHÚ TEMPLATE\n")
        parts.append(f"(Không dùng được template tự động: {template_error})")
    parts.append("\n\n## TEMPLATE / KHUNG THAM CHIẾU (nếu có)\n")
    parts.append(template_context_text)
    parts.append(
        "\n\n## MÃ NGUỒN HỌC VIÊN — BÀI TẬP ĐẦU GIỜ (bài nộp chính — chấm điểm, ưu tiên)\n"
    )
    if submission_context.strip():
        parts.append(submission_context)
    else:
        parts.append(
            "(Không có mã nguồn bài tập đầu giờ cho lượt chấm này — chỉ chấm báo cáo / mini_project_present theo khối repo báo cáo nếu có.)"
        )

    if report_bundle is not None:
        parts.append(
            "\n\n## BÁO CÁO (GitHub: mã + DOCX trích văn bản; Google Docs: export; OneDrive/SharePoint: Word chia sẻ — chấm báo cáo; mã mini chỉ cho mini_project_present)\n"
        )
        rs = format_bundle_for_prompt(report_bundle).strip()
        parts.append(rs if rs else "(Repo không có nội dung file text thu thập được.)")

    _pcs = (comment_style or "hackathon_per_question").strip().lower()
    cs = _pcs if _pcs in ("default", "hackathon_per_question") else "hackathon_per_question"
    comment_line = (
        "- `comment` (Hackathon): **theo từng số câu trong đề**, mỗi câu một dòng `Câu k: đúng|sai|thiếu|...`; cấm mở bài kiểu «hoàn thành tốt phần …» / khen chung chung trước khi liệt kê câu — xem SYSTEM mục 8.\n"
        if cs == "hackathon_per_question"
        else "- `comment`: một đoạn ngắn, không bullet, không markdown.\n"
    )
    parts.append(
        "\n\n## HƯỚNG DẪN CHẤM (bắt buộc)\n"
        "- `score` và `comment` chỉ phản ánh **bài tập đầu giờ** (khối trên) và **báo cáo** (khối BÁO CÁO: GitHub, Google Docs hoặc OneDrive/SharePoint nếu có). Nếu khối bài tập đầu giờ rỗng thì chỉ báo cáo. Ưu tiên bài tập đầu giờ trong tổng điểm khi cả hai có dữ liệu.\n"
        "- `mini_project_present`: **có** / **không** / **không_rõ** — chỉ bằng chứng nộp / đối chiếu đề; không dùng để cộng trừ `score`, không mô tả chất lượng mini trong `comment`.\n"
        "- Chấm lỏng tay (đề vs template): không trừ nặng vì đề nói “sản phẩm” mà bài làm theo template “danh bạ/contact”; nếu logic sửa/xóa/validate tương đương thì điểm bài tập đầu giờ quanh mức hợp lý (~70) theo SYSTEM.\n"
        "- Không soi chữ trong alert nếu đúng ý; không bịa yêu cầu không có trong đề.\n"
        + comment_line
        + "- Rubric (tuỳ chọn) có thể tách tiêu chí cho bài tập đầu giờ và báo cáo; vẫn một `score` tổng hợp 0–100."
    )
    return "\n".join(parts)


def grade_submission(
    doc: DocxContent,
    submission_bundle: CollectedBundle,
    template_bundle: CollectedBundle | None,
    *,
    model: str,
    template_error: str | None = None,
    strict_ai_penalty: bool = True,
    ai_penalty_min_confidence: int = 75,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    report_bundle: CollectedBundle | None = None,
    comment_style: str = "hackathon_per_question",
) -> GradeOutcome:
    _cs = (comment_style or "hackathon_per_question").strip().lower()
    cs = _cs if _cs in ("default", "hackathon_per_question") else "hackathon_per_question"
    user_prompt = build_user_prompt(
        doc,
        submission_bundle,
        template_bundle,
        template_error=template_error,
        report_bundle=report_bundle,
        comment_style=cs,
    )
    messages = [
        ChatMessage(role="system", content=system_prompt_for_comment_style(cs)),
        ChatMessage(role="user", content=user_prompt),
    ]

    raw_text, meta = complete_chat(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    try:
        blob = parse_llm_json(raw_text)
        payload = coalesce_grade(blob)
    except Exception as e:
        raise RuntimeError(
            "Model không trả về JSON hợp lệ. Thử tăng max_tokens hoặc đổi model.\n"
            f"Chi tiết: {e}\n---\n{raw_text[:4000]}"
        ) from e

    applied = False
    final_score = payload.score
    final_comment = payload.comment

    # Nếu AI đã nêu rõ sai chủ đề/entity chính, chặn trần điểm ở mức vừa.
    if _looks_domain_mismatch(final_comment):
        final_score = min(final_score, DOMAIN_MISMATCH_SCORE_CAP)

    if strict_ai_penalty and (
        payload.integrity_verdict == "likely_ai"
        and payload.integrity_confidence_0_100 >= ai_penalty_min_confidence
    ):
        applied = True
        final_score = 0
        final_comment = "dùng AI"

    return GradeOutcome(
        payload=payload,
        final_score=final_score,
        final_comment=final_comment,
        applied_ai_penalty=applied,
        raw_model_text=raw_text,
        openrouter_meta=meta,
    )


def outcome_to_json_dict(outcome: GradeOutcome, *, include_raw: bool = False) -> dict[str, Any]:
    base = outcome.payload.to_public_dict(
        applied_penalty=outcome.applied_ai_penalty,
        final_comment=outcome.final_comment,
        final_score=outcome.final_score,
    )
    extra = {
        "model": (outcome.openrouter_meta.get("model") if outcome.openrouter_meta else None),
        "usage": outcome.openrouter_meta.get("usage") if outcome.openrouter_meta else None,
    }
    out = {**base, **{k: v for k, v in extra.items() if v is not None}}
    if include_raw:
        out["raw_model_text"] = outcome.raw_model_text
        if outcome.openrouter_meta:
            out["openrouter_response"] = outcome.openrouter_meta
    return out


def dump_outcome_json(outcome: GradeOutcome, *, include_raw: bool = False) -> str:
    return json.dumps(
        outcome_to_json_dict(outcome, include_raw=include_raw),
        ensure_ascii=False,
        indent=2,
    )
