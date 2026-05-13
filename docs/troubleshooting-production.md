# Xử lý sự cố production (rikkei.rugal.vn)

Tài liệu ghi nhận lỗi thực tế khi sinh **tài liệu đọc** và **quiz session cuối giờ**, nguyên nhân, cách xử lý trong code và việc cần làm sau deploy.

---

## 1. Tài liệu đọc — lỗi tạo ảnh minh họa (OpenRouter 404)

### Triệu chứng

```
Lỗi tạo ảnh minh họa: OpenRouter HTTP 404:
{"error":{"message":"No endpoints found for google/gemini-2.5-flash-image-preview.","code":404},...}
```

Job chạy ~11 phút; có thể vẫn có DOCX/Excel nhưng không có ảnh, hoặc UI hiện lỗi ảnh nếu bản deploy cũ coi lỗi ảnh là fatal.

### Nguyên nhân

| Yếu tố | Chi tiết |
|--------|----------|
| Model slug | `google/gemini-2.5-flash-image-preview` **không có endpoint** trên tài khoản OpenRouter của server (404, không phải timeout). |
| Slug cũ trong UI/cấu hình | Giao diện hoặc request vẫn gửi `-preview` trong khi OpenRouter chỉ expose bản GA. |
| Flux | `black-forest-labs/flux.*` trên OpenRouter thường **không** hỗ trợ modality `image` qua cùng API chat — cũng hay 404 hoặc không trả ảnh. |

### Cách xử lý (code đã có / cần deploy)

1. **Mặc định ảnh**: `google/gemini-2.5-flash-image` (`cham_bai/model_options.py` — `DEFAULT_IMAGE_MODEL`).
2. **Alias**: `resolve_image_model()` map `*-image-preview` → `google/gemini-2.5-flash-image`.
3. **Fallback**: `reading_gen.py` thử lần lượt Gemini 2.5 → Gemini 3.1 preview → Flux; **lỗi từng model không làm fail cả job** (chỉ bỏ ảnh, vẫn xuất văn bản).
4. **UI**: tab Đọc — chọn model ảnh `google/gemini-2.5-flash-image`, tránh slug `-preview`.

### Kiểm tra sau deploy

- `POST /api/reading` → **202** + `job_id`.
- Poll `GET /api/reading/jobs/{id}` đến `status: done`.
- Nếu mọi model ảnh 404: job vẫn `done`, file DOCX không ảnh; progress không còn dừng hẳn với `Lỗi tạo ảnh minh họa` fatal.

### Gợi ý vận hành

- Trong OpenRouter dashboard, xác nhận model có tag **image generation** và account được phép gọi.
- Thử thủ công: `google/gemini-2.5-flash-image`, sau đó `google/gemini-3.1-flash-image-preview`.

---

## 2. Quiz session cuối giờ — block 16–30 (JSON cắt / trùng câu block 1)

### Triệu chứng

- Block 1 (STT 1–15) xong nhanh; **block 2 (16–30)** chạy 13+ phút, nhiều lần thử (vd. kiểm tra 48–54).
- Thông báo lỗi dạng:

```
JSON session cuối giờ bị cắt/sai ở block 16–30. (Đã thử tới 49152 token.)
--- Lỗi kiểm tra/parse cuối: Câu 1 trùng câu đã soạn [#1]: «...» — đổi chủ đề/kịch bản khác hẳn.
```

- Hoặc JSON **cụt giữa câu** (vd. `"Vòng lặ`…) dù `max_tokens` đã 49152.

### Nguyên nhân

| Yếu tố | Chi tiết |
|--------|----------|
| Trùng verbatim block 1 | Model block 2 hay **copy lại câu #1 block 1** (vd. toán tử `and`, Definite Iteration `for`). Validator từ chối → retry tối đa 9 lần. |
| Output quá dài | 15 câu × (câu hỏi + 4 đáp án + 4 explanations) vượt giới hạn thực tế của model/context → JSON không đóng `]`. |
| Nhiệt độ retry thấp | Retry với temperature thấp dễ **lặp lại** cùng một câu sai. |
| Thiếu “danh sách cấm” rõ | Chỉ có digest ngắn, chưa đủ nhấn mạnh **CẤM SAO CHÉP** từng câu block trước. |

### Ví dụ lỗi trùng (thực tế)

**Lần 1 — chủ đề `and` / nested if**

- Block 1 câu 1: *Tại sao dùng quá nhiều toán tử `and` để kiểm tra cùng một điều kiện...*
- Block 2 câu 1: **cùng nguyên văn** → reject.

**Lần 2 — chủ đề vòng lặp**

- Block 1: *Vòng lặp `for` được gọi là Definite Iteration vì lý do gì?*
- Block 2 câu 1: **lại trùng** → reject; đôi khi kèm JSON cắt ở câu 4.

### Cách xử lý (code đã cập nhật)

Trong `cham_bai/quiz_gen.py`:

1. **`_session_quiz_forbidden_digest()`** — liệt kê toàn bộ câu đã soạn với nhãn `[CẤM SAO CHÉP #n]`, inject vào prompt block 2/3 và retry.
2. **Prompt block 16–30** — cảnh báo không copy/rephrase sát; chọn 15 concept khác; rút ngắn explanations (≤ 70 ký tự) để giảm cắt JSON.
3. **Retry temperature** — tăng dần theo attempt (`min(0.58, temp0 + 0.05 * attempt)`) thay vì hạ temperature.
4. **Token output** — lần đầu 32768, retry 49152 (giữ nguyên; nếu vẫn cắt → đổi model context lớn hơn hoặc rút prompt).

### Kiểm tra sau deploy

- Tạo quiz **Session cuối giờ**, theo dõi progress: `Block 2/3: ...` không kẹt 9/9 lần với cùng lỗi trùng #1.
- File Excel đủ 45 câu, block 16–30 không lặp nguyên văn câu 1–15.

### Gợi ý nếu vẫn fail

- Đổi model quiz sang model instruct context lớn (vd. `google/gemma-4-26b-a4b-it` hoặc model trả JSON ổn định hơn).
- Rút trích DOCX mỗi block (đã có `block_excerpt`) — tránh excerpt quá dài làm model “ôm” ít chủ đề.
- Giảm độ dài explanations trong prompt style (đã ≤ 90 ký tự; block 2 nhắc ≤ 70).

---

## 3. Liên quan hạ tầng (đã xử lý trước đó)

| Lỗi | Fix |
|-----|-----|
| Quiz 504 | Job async `POST /api/quiz` → 202, poll job |
| Poll job 404 | Job store trên disk (`QUIZ_JOBS_DIR`), volume Docker |
| Poll ~400 request | Backoff poll trong `app.js` |
| Reading 504 | Cùng pattern async `/api/reading/jobs/...` |

Cần **deploy lại** `docker-compose.prod.yml` + image mới để các fix trên có hiệu lực trên `rikkei.rugal.vn`.

---

## 4. File tham chiếu

| File | Vai trò |
|------|---------|
| `cham_bai/model_options.py` | `DEFAULT_IMAGE_MODEL`, `resolve_image_model`, alias preview |
| `cham_bai/reading_gen.py` | Sinh đọc + ảnh, fallback model |
| `cham_bai/quiz_gen.py` | Session quiz, dedupe, forbidden digest, block loop |
| `cham_bai/web_app.py` | API job quiz/reading |
| `cham_bai/web/static/app.js` | Poll backoff |
| `docker-compose.prod.yml` | Volume `agent_edu_quiz_jobs` |
