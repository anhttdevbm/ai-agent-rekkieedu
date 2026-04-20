# Agent Edu (OpenRouter)

Đầu vào: **đề bài** (file **.docx** hoặc **link Google Docs** xem được qua liên kết) + **bài nộp** (thư mục hoặc GitHub).  
Đầu ra: **điểm /100**, **nhận xét**, và **đánh giá toàn vẹn** (có thể giảm về 0 điểm nếu cấu hình).

## Cài đặt

```bash
cd E:\Project\Tool_cham_bai
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Tạo file `.env` từ `.env.example` và điền `OPENROUTER_API_KEY`.

## Giao diện (GUI)

Sau khi `pip install -e .`:

```bash
agent-edu-gui
```

Hoặc: `python launch_gui.py`

- **Đề bài:** file `.docx` hoặc dán URL Google Docs (`https://docs.google.com/document/d/.../edit`). Tài liệu cần đặt quyền **Bất kỳ ai có liên kết — Xem** (Anyone with the link — Viewer). **Bài nộp:** ô nhiều dòng — **mỗi dòng một** thư mục hoặc link GitHub (cùng một đề, chấm lần lượt); **có thể để trống** dòng đó nếu cùng dòng bên «Repo báo cáo» có link (chỉ chấm báo cáo). Nút **Thêm thư mục…** chèn thêm một dòng. **Báo cáo + mini (tuỳ chọn):** ô nhiều dòng — link **GitHub**, **Google Docs** (bài chỉ nộp Docs), hoặc **OneDrive/SharePoint** (ví dụ `https://1drv.ms/w/...` — file Word chia sẻ xem được), **dòng i khớp bài nộp dòng i**. **Kết quả:** điểm + nhận xét + mini project (có/không) trong log. Muốn JSON dùng CLI `--submission-list` và `--out`.
- **Quiz đầu giờ (tab riêng):** nút chính **tự tạo file Excel** (`quiz_<lesson>_<session>_<thời gian>.xlsx`) trong **cùng thư mục với file mẫu**; có thể dùng **Tạo và chọn nơi lưu** nếu muốn chỉ đường dẫn. Chọn file **Excel mẫu** (hàng 1 = tiêu đề cột; có thể dùng nút tạo/mở mẫu mặc định — **7 cột:** STT, Mức độ, Mục tiêu, Câu hỏi, Các đáp án, Kết quả, Giải thích). Với mẫu này, tool luôn tạo **đúng 5 câu** theo thứ tự mức độ/mục tiêu cố định (Thông hiểu → … → Phân tích sơ bộ), **4 hàng mỗi câu** (A–D), merge cột meta + câu hỏi như bảng mẫu. **Bắt buộc:** lesson, session. **Tuỳ chọn:** DOCX. Mẫu kiểu **một hàng một câu** (Đáp án A…D) vẫn dùng được với ô “Số câu hỏi”.
- **API key:** không nhập trên GUI. Chạy bằng **Python** dùng `.env` (hoặc biến môi trường). **EXE** đã build lấy key **nhúng lúc build** từ `.env` (mục “Đóng gói EXE”).

## Giao diện web

```bash
agent-edu-web
```

Mở **http://127.0.0.1:8765** — cùng chức năng tab Chấm bài / Quiz / Bài đọc. Tab Chấm bài: đề bài nhập **đường dẫn .docx trên server** hoặc **Google Docs** (không upload đề); repo báo cáo nhiều dòng khớp chỉ số với bài nộp.

## Docker

```bash
docker compose up --build -d
```

Trình duyệt: **http://localhost:8765**. Biến môi trường lấy từ file `.env` (xem `docker-compose.yml`).

**Production / deploy:** dùng `docker-compose.prod.yml` (workers Uvicorn, giới hạn CPU/RAM, log xoay vòng, `restart: always`, user non-root trong image). Ví dụ:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up --build -d
```

Biến tuỳ chọn: `AGENT_EDU_PUBLISH`, `AGENT_EDU_IMAGE`, `AGENT_EDU_TAG`, `UVICORN_WORKERS`, `AGENT_EDU_MEM_LIMIT`, … (xem comment trong file).

## Đóng gói EXE (Windows)

Cần **Git** trên máy build nếu muốn tính năng clone template (người dùng EXE cũng cần Git trên PATH khi bật “Clone template”).

Đặt `OPENROUTER_API_KEY` trong **`.env`** ở thư mục project. `build_windows.ps1` chạy `python scripts/embed_key_from_env.py` để nhúng key vào `cham_bai/_embedded_key.py` rồi build — **EXE không cần .env cạnh file chạy**.

**Cảnh báo:** key trong EXE có thể bị trích. Sau build có thể `git checkout cham_bai/_embedded_key.py` trước khi commit.

```powershell
cd E:\Project\Tool_cham_bai
.\build_windows.ps1
```

File ra lệnh: `dist\AgentEdu.exe` (một file, không cửa sổ console).

Build dùng PyInstaller (`pip install -e ".[build]"`).

## Chạy dòng lệnh

```bash
agent-edu --assignment path\to\de_bai.docx --submission path\to\folder_nop_bai --out ket_qua.json
# hoặc đề từ Google Docs:
agent-edu --assignment "https://docs.google.com/document/d/DOC_ID/edit" --submission path\to\folder
# alias cũ vẫn dùng được:
agent-edu --docx de_bai.docx --submission https://github.com/nguoi_dung/ten-repo

# Nhiều bài cùng đề (file danh sách, mỗi dòng một đường dẫn hoặc URL GitHub):
agent-edu --assignment de_bai.docx --submission-list ds_bai_nop.txt --out ket_qua_lo.json
# Cùng lô, mỗi sinh viên một nguồn báo cáo (file mỗi dòng một URL GitHub, Google Docs hoặc OneDrive/SharePoint; dòng i khớp ds_bai_nop dòng i):
agent-edu --assignment de_bai.docx --submission-list ds_bai_nop.txt --report-repo-list ds_bao_cao.txt --out ket_qua_lo.json
```

Nội dung `ds_bai_nop.txt` ví dụ:

```text
E:\nop\sv01
E:\nop\sv02
https://github.com/nguoi_dung/repo-bai-03
```

Tùy chọn: `--no-template`, `--model anthropic/claude-opus-4.6`, `--strict-ai` / `--no-strict-ai`, `--debug` (kèm phản hồi thô).

Trên Windows, CLI tự ép UTF-8 cho stdout/stderr để tiếng Việt và JSON không lỗi mã hóa.

**Quiz đầu giờ (CLI):**

```bash
# Tu dong dat ten file .xlsx canh file mau:
agent-edu-quiz --template path\to\quiz_mau.xlsx --lesson "Lesson 1" --session "Session A"
agent-edu-quiz --template quiz_mau.xlsx --lesson "L1" --session "S1" --docx bai_giang.docx --model anthropic/claude-3.5-sonnet
# Chi dinh file ra:
agent-edu-quiz --template quiz_mau.xlsx --out quiz_out.xlsx --lesson "L1" --session "S1"
```

Khi **build EXE** (`build_windows.ps1`): đóng `AgentEdu.exe` trước khi build — script sẽ cố **tắt tiến trình AgentEdu** nếu đang chạy để tránh `PermissionError` khi ghi đè `dist\AgentEdu.exe`.

**Git:** để tự tải template từ link trong DOCX, máy cần có lệnh `git`. Nếu không, chương trình vẫn chấm được nhưng bỏ qua phần so khung template.

## Lưu ý

“Phát hiện dùng AI” chỉ là **đánh giá heuristic** của mô hình, không phải bằng chứng pháp lý. Nên kết hợp phỏng vấn / kiểm tra trong lớp trước khi kỷ luật học viên.
