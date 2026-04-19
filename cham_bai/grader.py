from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from cham_bai.collector import CollectedBundle, format_bundle_for_prompt
from cham_bai.docx_reader import DocxContent
from cham_bai.github_template import format_template_context
from cham_bai.openrouter import ChatMessage, complete_chat
from cham_bai.schemas import GradePayload, coalesce_grade, parse_llm_json


SYSTEM_PROMPT = """Bạn là trợ giảng chấm bài lập trình bậc đại học. Bài có thể gồm lab thông thường, mini project (GitHub), và/hoặc báo cáo (DOCX trong repo). Tổng hợp một điểm 0–100 thực tế, lỏng tay: ưu tiên chạy được và đáp ứng ý chính; không hạ điểm mạnh vì lệch nhãn chủ đề khi đề và template khác nhau mà sinh viên làm đúng theo template (xem mục 5).

Quy tắc:
1) Đọc “ĐỀ BÀI” (.docx / Google Docs). Nếu có “REPO ĐỀ / YÊU CẦU MINI PROJECT” thì dùng thêm làm yêu cầu / rubric cho phần mini project. Nếu có “REPO BÁO CÁO & MINI PROJECT” thì chấm cả mã trong repo đó và phần văn bản trích từ DOCX (các file `_docx_text/…`). “MÃ NGUỒN HỌC VIÊN” là bài nộp chính; nếu trùng nội dung với repo báo cáo thì không trừ trùng lặp, chỉ nhận xét gọn.
2) Báo cáo DOCX (khi có trích văn bản): đánh giá mức vừa phải — bài toán, thiết kế/triển khai, kết quả, hạn chế; không soi văn phong hoàn hảo. Nếu không có trích DOCX trong dữ liệu thì không bịa; nếu đề bắt buộc báo cáo mà thiếu thì phản ánh trong rubric/comment.
3) Chỉ chấm phần đề (và repo đề project nếu có) nêu rõ; không bịa thêm hạng mục. Nếu đề chỉ yêu cầu (ví dụ) sửa và xóa thì không trừ vì không có thêm / danh sách đầy đủ trừ khi đề ghi rõ.
4) Không soi chữ trong alert / thông báo: nếu cùng ý (xác nhận xóa, báo thành công cập nhật/xóa) thì chấp nhận; không trừ nặng vì khác vài từ so với đề nếu logic đúng.
5) Đề vs template vs bài nộp (chấm lỏng tay): Khi đề nói một chủ đề (ví dụ quản lý sản phẩm) nhưng template GitHub là chủ đề khác (ví dụ danh bạ, contact) và sinh viên làm giống template thì coi là bài hợp lệ theo khung mẫu. Không coi là sai chủ đề nghiêm trọng. Ánh xạ tương đương giữa các trường dữ liệu và validate. Với bài chạy ổn, có sửa/xóa và validate đúng hướng theo cách làm đó, điểm mục tiêu khoảng 65–78, thường quanh 70 (ví dụ 68–74); chỉ dưới 50 khi thiếu hẳn phần cốt lõi đề yêu cầu hoặc lỗi nặng.
6) Template không thay thế đề khi **xung đột chức năng** (đề bắt buộc tính năng X mà code không có). Khi xung đột chỉ là **tên miền / nhãn** (sản phẩm vs contact) nhưng trên thực tế cùng một bài tập template → áp mục 5, chấm rộng.
7) File .md / README do sinh viên tự thêm: không dùng để mở rộng phạm vi đề; không trừ vì “tài liệu khác đề” trừ khi đề bắt nộp. Có thể ghi nhẹ trong integrity_notes nếu liên quan AI.
8) Trường "comment": một đoạn văn ngắn duy nhất (2–4 câu, tối đa khoảng 600 ký tự), tiếng Việt. Cấm gạch đầu dòng và cấm định dạng markdown (in đậm, tiêu đề, danh sách). Tóm tắt đạt/chưa đạt (code + mini project + báo cáo nếu có), không liệt kê dài.
9) Cho điểm 0–100 (số nguyên), phù hợp mức độ lỏng tay ở mục 3–6.

10) integrity_verdict:
   - "pass": không có dấu hiệu đáng kể cho thấy bài được tạo bởi công cụ AI thay cho học viên (chấp nhận tra cứu tài liệu, snippet ngắn).
   - "suspicious": có một số dấu hiệu mâu thuẫn / quá đồng nhất / giống văn bản AI nhưng KHÔNG đủ để kết luận.
   - "likely_ai": có nhiều dấu hiệu mạnh (ví dụ: toàn bộ file giống văn phong tutorial, over-comment kiểu giảng viên AI, cấu trúc không khớp trình độ, trùng khớp bất thường với template ngoài đề, v.v.). Lưu ý: đây chỉ là đánh giá heuristic, không phải bằng chứng pháp lý.
11) integrity_confidence_0_100: độ tin cậy (0–100) cho verdict. Nếu pass thì thường thấp–trung; chỉ cao khi có lý do rõ.
12) integrity_notes: danh sách ngắn các lý do (tiếng Việt), tối đa 3 mục.

CHỈ trả về một JSON hợp lệ duy nhất, không thêm markdown ngoài JSON. Schema:
{
  "score": <0-100>,
  "comment": "<nhận xét tiếng Việt>",
  "integrity_verdict": "pass" | "suspicious" | "likely_ai",
  "integrity_confidence_0_100": <0-100>,
  "integrity_notes": ["...", "..."],
  "rubric": { "tieu_chi": diem, ... }
}
Trong đó rubric là tùy chọn; nếu không chắc hãy dùng {} hoặc bỏ trường (dùng {} an toàn hơn).
"""


@dataclass
class GradeOutcome:
    payload: GradePayload
    final_score: int
    final_comment: str
    applied_ai_penalty: bool
    raw_model_text: str
    openrouter_meta: dict[str, Any]


def build_user_prompt(
    doc: DocxContent,
    submission_bundle: CollectedBundle,
    template_bundle: CollectedBundle | None,
    *,
    template_error: str | None,
    project_spec_bundle: CollectedBundle | None = None,
    report_bundle: CollectedBundle | None = None,
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

    if project_spec_bundle is not None:
        parts.append("\n\n## REPO ĐỀ / YÊU CẦU MINI PROJECT (GitHub — tham chiếu)\n")
        ps = format_bundle_for_prompt(project_spec_bundle).strip()
        parts.append(ps if ps else "(Repo không có nội dung file text thu thập được.)")

    if template_error:
        parts.append("\n\n## GHI CHÚ TEMPLATE\n")
        parts.append(f"(Không dùng được template tự động: {template_error})")
    parts.append("\n\n## TEMPLATE / KHUNG THAM CHIẾU (nếu có)\n")
    parts.append(template_context_text)
    parts.append("\n\n## MÃ NGUỒN HỌC VIÊN (bài nộp chính)\n")
    parts.append(submission_context)

    if report_bundle is not None:
        parts.append("\n\n## REPO BÁO CÁO & MINI PROJECT (GitHub — mã nguồn + trích DOCX nếu có)\n")
        rs = format_bundle_for_prompt(report_bundle).strip()
        parts.append(rs if rs else "(Repo không có nội dung file text thu thập được.)")

    parts.append(
        "\n\n## HƯỚNG DẪN CHẤM (bắt buộc)\n"
        "- Chấm lỏng tay: không trừ nặng vì đề nói “sản phẩm” mà bài làm theo template “danh bạ/contact”; nếu logic sửa/xóa/validate tương đương thì cho điểm bình thường, mục tiêu quanh 70.\n"
        "- Nếu có mini project / báo cáo: rubric có thể tách nhẹ (vd. code, báo cáo) nhưng `score` là tổng hợp một số 0–100.\n"
        "- Không soi chữ trong alert nếu đúng ý; không bịa yêu cầu không có trong đề.\n"
        "- Comment: một đoạn ngắn, không bullet, không markdown.\n"
        "- Nếu đề có rubric, phản ánh trong rubric; vẫn giữ comment ngắn."
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
    project_spec_bundle: CollectedBundle | None = None,
    report_bundle: CollectedBundle | None = None,
) -> GradeOutcome:
    user_prompt = build_user_prompt(
        doc,
        submission_bundle,
        template_bundle,
        template_error=template_error,
        project_spec_bundle=project_spec_bundle,
        report_bundle=report_bundle,
    )
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
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
