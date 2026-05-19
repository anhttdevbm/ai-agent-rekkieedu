"""45 câu quiz cuối giờ Session 01 — L01–L06, khác bộ đầu giờ."""
from __future__ import annotations

from build_corrected_session_warmup_quiz import _code_row, _row


def build_intro_lesson_end_rows() -> list[dict[str, object]]:
    """45 câu kỹ thuật cuối giờ (không trùng đề với build_intro_lesson_rows)."""
    rows: list[dict[str, object]] = []

    rows.append(_row(
        "Python được xếp vào nhóm ngôn ngữ nào?",
        ("Ngôn ngữ bậc cao", "Ngôn ngữ máy", "Ngôn ngữ hợp ngữ", "Ngôn ngữ Assembly"),
        (
            "Đúng: Python là ngôn ngữ bậc cao, gần với tư duy người.",
            "Sai: Ngôn ngữ máy là mã nhị phân.",
            "Sai: Hợp ngữ gần phần cứng hơn Python.",
            "Sai: Assembly không phải Python.",
        ), 1))
    rows.append(_row(
        "Điều nào KHÔNG bắt buộc khi viết chương trình Python đơn giản in ra màn hình?",
        (
            "Khai báo hàm main() trước khi chạy",
            "Cài Python Interpreter",
            "Lưu file với đuôi .py",
            "Dùng lệnh print()",
        ),
        (
            "Đúng: Python không bắt buộc main() như Java/C.",
            "Sai: Cần Interpreter để chạy file .py.",
            "Sai: Quy ước file Python là .py.",
            "Sai: print() là cách in cơ bản trong bài.",
        ), 1))
    rows.append(_row(
        "Khi gán `student_id = 2025001`, kiểu dữ liệu thường là gì?",
        ("int", "str", "float", "bool"),
        (
            "Đúng: 2025001 là số nguyên (int).",
            "Sai: str cần dấu nháy quanh chuỗi.",
            "Sai: float thường có phần thập phân.",
            "Sai: bool chỉ True/False.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'print("IT205 Python")',
        ("IT205 Python", '"IT205 Python"', 'print("IT205 Python")', "Lỗi"),
        (
            "Đúng: print in chuỗi, không kèm dấu nháy.",
            "Sai: Dấu nháy không xuất hiện trên màn hình.",
            "Sai: Không in lại cả câu lệnh.",
            "Sai: Cú pháp hợp lệ.",
        ), 1))
    rows.append(_row(
        "Máy tính cần Python Interpreter để làm gì với file .py?",
        (
            "Đọc và thực thi mã nguồn Python",
            "Chỉ mở file như văn bản",
            "Tự động biên dịch sang .exe trước khi chạy",
            "Chuyển .py sang .java",
        ),
        (
            "Đúng: Interpreter đọc và chạy chương trình Python.",
            "Sai: Mở văn bản không đủ để chạy code.",
            "Sai: Python không bắt buộc tạo .exe như C.",
            "Sai: Không chuyển sang Java.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        "a = 2\nb = 3\nprint(b)",
        ("3", "2", "b", "Lỗi"),
        (
            "Đúng: b = 3 nên print(b) in 3.",
            "Sai: a là 2, không phải kết quả in.",
            "Sai: In giá trị biến, không in tên b.",
            "Sai: Gán và in hợp lệ.",
        ), 1))
    rows.append(_row(
        "Kiểu dữ liệu bool trong Python lưu giá trị nào?",
        ("True hoặc False", "Số nguyên dương", "Chuỗi ký tự", "Số thực"),
        (
            "Đúng: bool chỉ nhận True/False.",
            "Sai: Số nguyên là int.",
            "Sai: Chuỗi là str.",
            "Sai: Số thực là float.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'city = "HN"\nprint(city)',
        ("HN", "city", '"HN"', "Lỗi"),
        (
            "Đúng: print in giá trị chuỗi đã gán.",
            "Sai: Không in tên biến.",
            "Sai: Dấu nháy không in ra.",
            "Sai: Code hợp lệ.",
        ), 1))
    rows.append(_row(
        "So với C/Java, Python giúp viết chương trình ngắn hơn vì?",
        (
            "Không bắt buộc khai báo kiểu và cú pháp gọn",
            "Bắt buộc dùng nhiều dấu { }",
            "Phải khai báo main() dài",
            "Chỉ cho phép một kiểu dữ liệu",
        ),
        (
            "Đúng: kiểu động và cú pháp gọn giúp code ngắn.",
            "Sai: Python dùng indentation, không dùng { }.",
            "Sai: Python không bắt buộc main().",
            "Sai: Python hỗ trợ nhiều kiểu.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        "print(7)",
        ("7", '"7"', "print(7)", "Lỗi"),
        (
            "Đúng: print in số 7.",
            "Sai: Số không in kèm dấu nháy.",
            "Sai: Không in lại câu lệnh.",
            "Sai: Cú pháp hợp lệ.",
        ), 1))
    rows.append(_row(
        'Dòng `# print("test")` trong Python có tác dụng gì?',
        (
            "Là chú thích, không thực thi lệnh print",
            "In ra test",
            "Báo lỗi cú pháp",
            "Ép kiểu sang chuỗi",
        ),
        (
            "Đúng: # làm cả dòng thành comment.",
            "Sai: Comment không chạy print.",
            "Sai: Cú pháp comment hợp lệ.",
            "Sai: Không liên quan ép kiểu.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'print("Một", "Hai")',
        ("Một Hai", "MộtHai", "Một, Hai", "Lỗi"),
        (
            "Đúng: print nhiều đối số, mặc định cách bằng khoảng trắng.",
            "Sai: Không nối liền.",
            "Sai: Dấu phẩy không in ra.",
            "Sai: Cú pháp hợp lệ.",
        ), 1))
    rows.append(_row(
        "Tên biến nào hợp lệ trong Python?",
        ("score_1", "1score", "score-1", "class"),
        (
            "Đúng: chữ/số/_; không bắt đầu bằng số.",
            "Sai: Không bắt đầu tên biến bằng số.",
            "Sai: Dấu - không dùng trong tên biến.",
            "Sai: class là từ khóa, không nên đặt tên biến.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'topic = "Lập trình"\nprint(topic)',
        ("Lập trình", "topic", '"Lập trình"', "Lỗi"),
        (
            "Đúng: in giá trị biến topic.",
            "Sai: Không in tên biến.",
            "Sai: Dấu nháy không in ra.",
            "Sai: Code hợp lệ.",
        ), 1))
    rows.append(_row(
        "Khi gán `active = True`, kiểu dữ liệu của active là gì?",
        ("bool", "int", "str", "float"),
        (
            "Đúng: True thuộc kiểu bool.",
            "Sai: True không phải int trong Python.",
            "Sai: True không phải chuỗi.",
            "Sai: True không phải float.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'print("2025")',
        ("2025", '"2025"', "int(2025)", "Lỗi"),
        (
            "Đúng: trong dấu nháy là chuỗi, in 2025.",
            "Sai: Dấu nháy không in ra.",
            "Sai: Không gọi int() trong code.",
            "Sai: Cú pháp hợp lệ.",
        ), 1))
    rows.append(_row(
        "Ép kiểu `int(\"12\")` trong Python cho kết quả gì?",
        ("Số nguyên 12", "Chuỗi \"12\"", "Số thực 12.0", "Lỗi"),
        (
            "Đúng: int() chuyển chuỗi số thành int.",
            "Sai: Sau ép kiểu là số, không còn là chuỗi.",
            "Sai: int() không tạo float.",
            "Sai: \"12\" ép kiểu int hợp lệ.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'code = "PY"\nprint(code)',
        ("PY", "code", '"PY"', "Lỗi"),
        (
            "Đúng: print in giá trị chuỗi PY.",
            "Sai: Không in tên biến.",
            "Sai: Dấu nháy không in ra.",
            "Sai: Code hợp lệ.",
        ), 1))
    rows.append(_row(
        "Python khác ngôn ngữ dùng { } ở điểm nào khi viết khối lệnh?",
        (
            "Dùng thụt dòng (indentation)",
            "Dùng dấu ; cuối dòng",
            "Dùng từ khóa repeat/until",
            "Bắt buộc dùng ngoặc vuông [ ]",
        ),
        (
            "Đúng: Python dùng indentation thay { }.",
            "Sai: ; không thay { }.",
            "Sai: repeat/until không phải cú pháp Python cơ bản.",
            "Sai: [ ] dùng cho list, không thay khối lệnh.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        "units = 4\nprint(units)",
        ("4", "units", '"4"', "Lỗi"),
        (
            "Đúng: print in giá trị 4.",
            "Sai: Không in tên biến.",
            "Sai: Không in kèm dấu nháy.",
            "Sai: Code hợp lệ.",
        ), 1))
    rows.append(_row(
        "Kiểu dữ liệu nào dùng để lưu văn bản như \"Hello\"?",
        ("str", "int", "float", "bool"),
        (
            "Đúng: chuỗi ký tự là str.",
            "Sai: int chỉ cho số nguyên.",
            "Sai: float cho số thực.",
            "Sai: bool cho True/False.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'print("X", "Y", "Z")',
        ("X Y Z", "XYZ", "X,Y,Z", "Lỗi"),
        (
            "Đúng: ba đối số cách nhau bằng khoảng trắng.",
            "Sai: Không nối liền.",
            "Sai: Dấu phẩy không in ra.",
            "Sai: Cú pháp hợp lệ.",
        ), 1))
    rows.append(_row(
        "Hàm int() dùng để làm gì?",
        (
            "Chuyển giá trị sang số nguyên",
            "Chuyển sang chuỗi",
            "In ra màn hình",
            "Viết chú thích",
        ),
        (
            "Đúng: int() ép kiểu sang số nguyên.",
            "Sai: Sang chuỗi dùng str().",
            "Sai: In màn hình dùng print().",
            "Sai: Comment dùng #.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'level = "Cơ bản"\nprint(level)',
        ("Cơ bản", "level", '"Cơ bản"', "Lỗi"),
        (
            "Đúng: in giá trị biến level.",
            "Sai: Không in tên biến.",
            "Sai: Dấu nháy không in ra.",
            "Sai: Code hợp lệ.",
        ), 1))
    rows.append(_row(
        "Triết lý \"đơn giản – dễ đọc\" của Python hướng tới điều gì?",
        (
            "Giảm rào cản cho người mới và dễ bảo trì code",
            "Bắt buộc code chạy nhanh nhất",
            "Tăng số dòng code tối đa",
            "Loại bỏ hoàn toàn Interpreter",
        ),
        (
            "Đúng: dễ học, dễ đọc, dễ bảo trì.",
            "Sai: Tốc độ không phải mục tiêu chính trong bài intro.",
            "Sai: Python không khuyến khích code dài dòng.",
            "Sai: Vẫn cần Interpreter để chạy.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'print("Học", "Python")',
        ("Học Python", "HọcPython", "Học, Python", "Lỗi"),
        (
            "Đúng: hai chuỗi in cách nhau bằng khoảng trắng.",
            "Sai: Không nối liền.",
            "Sai: Dấu phẩy không in ra.",
            "Sai: Cú pháp hợp lệ.",
        ), 1))
    rows.append(_row(
        "Câu lệnh `print()` thuộc nhóm chức năng nào?",
        ("Xuất dữ liệu ra màn hình", "Nhập dữ liệu từ bàn phím", "Ép kiểu số", "Khai báo biến"),
        (
            "Đúng: print hiển thị kết quả ra màn hình.",
            "Sai: Nhập bàn phím thường dùng input() (ngoài phạm vi câu này).",
            "Sai: Ép kiểu dùng int(), str(), float().",
            "Sai: Gán biến dùng dấu =.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'version = "3.12"\nprint(version)',
        ("3.12", "version", '"3.12"', "Lỗi"),
        (
            "Đúng: in chuỗi phiên bản đã gán.",
            "Sai: Không in tên biến.",
            "Sai: Dấu nháy không in ra.",
            "Sai: Code hợp lệ.",
        ), 1))
    rows.append(_row(
        "Nếu không có Python Interpreter, file .py sẽ?",
        (
            "Không chạy được như chương trình Python",
            "Tự chạy khi double-click",
            "Biên dịch sang C++ tự động",
            "Chỉ chạy trong Notepad",
        ),
        (
            "Đúng: cần Interpreter để thực thi .py.",
            "Sai: Hệ điều hành không tự chạy .py.",
            "Sai: Không tự biên dịch sang C++.",
            "Sai: Notepad chỉ soạn thảo.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        "hours = 3\nprint(hours)",
        ("3", "hours", '"3"', "Lỗi"),
        (
            "Đúng: print in giá trị 3.",
            "Sai: Không in tên biến.",
            "Sai: Không in kèm dấu nháy.",
            "Sai: Code hợp lệ.",
        ), 1))
    rows.append(_row(
        "Khi gán `rate = 4.5`, kiểu dữ liệu thường là gì?",
        ("float", "int", "str", "bool"),
        (
            "Đúng: 4.5 có phần thập phân là float.",
            "Sai: int không có phần thập phân.",
            "Sai: str cần dấu nháy.",
            "Sai: bool là True/False.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'user = "Lan"\nprint(f"Xin chao {user}")',
        ("Xin chao Lan", "Xin chao user", 'f"Xin chao Lan"', "Lỗi"),
        (
            "Đúng: f-string thay {user} bằng Lan.",
            "Sai: Không in nguyên văn tên biến.",
            "Sai: Không in cả cú pháp f-string.",
            "Sai: f-string hợp lệ.",
        ), 1))
    rows.append(_row(
        "Cú pháp gán biến đúng trong Python là?",
        ('items = 10', 'int items = 10', 'items == 10', '10 = items'),
        (
            "Đúng: tên_biến = giá_trị.",
            "Sai: Python không dùng int items = …",
            "Sai: == là so sánh, không phải gán.",
            "Sai: Không gán vào literal bên trái.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'n = int("8")\nprint(n)',
        ("8", '"8"', "int", "Lỗi"),
        (
            "Đúng: int(\"8\") thành 8, print in 8.",
            "Sai: Sau ép kiểu là số.",
            "Sai: int là tên hàm, không phải output.",
            "Sai: Ép kiểu hợp lệ.",
        ), 1))
    rows.append(_row(
        "Chuỗi `'Python'` và `\"Python\"` trong Python?",
        (
            "Cùng là chuỗi str, chỉ khác loại dấu nháy",
            "Khác kiểu dữ liệu",
            "Chỉ nháy kép mới hợp lệ",
            "Chỉ nháy đơn mới hợp lệ",
        ),
        (
            "Đúng: cả hai đều tạo str.",
            "Sai: Cùng kiểu str.",
            "Sai: Nháy đơn cũng hợp lệ.",
            "Sai: Nháy kép cũng hợp lệ.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'print("A")\nprint("B")',
        ("A và B trên hai dòng", "A B trên một dòng", "AB", "Lỗi"),
        (
            "Đúng: mỗi print() xuống dòng mặc định.",
            "Sai: Hai lệnh print riêng, không gộp một dòng.",
            "Sai: Không tự nối AB.",
            "Sai: Hai lệnh print hợp lệ.",
        ), 1))
    rows.append(_row(
        "Hàm str() dùng để làm gì?",
        ("Chuyển giá trị sang chuỗi", "Chuyển sang số nguyên", "In ra file", "Tạo vòng lặp"),
        (
            "Đúng: str() ép kiểu sang chuỗi.",
            "Sai: Số nguyên dùng int().",
            "Sai: Ghi file không phải str() cơ bản.",
            "Sai: Vòng lặp là for/while (chưa học).",
        ), 1))
    rows.append(_row(
        "Điểm mạnh của Python trong bài giới thiệu thường nhấn mạnh?",
        (
            "Hệ sinh thái thư viện phong phú và cộng đồng lớn",
            "Bắt buộc quản lý bộ nhớ thủ công",
            "Chỉ chạy trên Windows",
            "Không cần cài Interpreter",
        ),
        (
            "Đúng: thư viện và cộng đồng là điểm mạnh.",
            "Sai: Python không yêu cầu quản lý bộ nhớ thủ công.",
            "Sai: Python đa nền tảng.",
            "Sai: Cần Interpreter để chạy.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'title = "Dev"\nprint(title)',
        ("Dev", "title", '"Dev"', "Lỗi"),
        (
            "Đúng: print in giá trị title.",
            "Sai: Không in tên biến.",
            "Sai: Dấu nháy không in ra.",
            "Sai: Code hợp lệ.",
        ), 1))
    rows.append(_row(
        "Dynamic Typing cho phép?",
        (
            "Gán giá trị mà không khai báo kiểu trước",
            "Bỏ qua mọi lỗi cú pháp",
            "Không dùng biến",
            "Chỉ dùng một biến trong chương trình",
        ),
        (
            "Đúng: Python tự suy ra kiểu khi gán.",
            "Sai: Lỗi cú pháp vẫn báo.",
            "Sai: Vẫn dùng biến bình thường.",
            "Sai: Có thể nhiều biến.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'print("K25")',
        ("K25", '"K25"', "str(K25)", "Lỗi"),
        (
            "Đúng: in chuỗi K25.",
            "Sai: Dấu nháy không in ra.",
            "Sai: Không gọi str() trong code.",
            "Sai: Cú pháp hợp lệ.",
        ), 1))
    rows.append(_row(
        "Lỗi IndentationError thường xảy ra khi?",
        (
            "Thụt dòng sai trong khối lệnh",
            "Quên cài Python",
            "Dùng sai tên hàm print",
            "File không có đuôi .py",
        ),
        (
            "Đúng: sai indentation gây IndentationError.",
            "Sai: Liên quan cài đặt, không phải thụt dòng.",
            "Sai: print sai tên là NameError khác.",
            "Sai: Đuôi file không gây IndentationError.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        "mark = 10\nprint(mark)",
        ("10", "mark", '"10"', "Lỗi"),
        (
            "Đúng: print in giá trị 10.",
            "Sai: Không in tên biến.",
            "Sai: Không in kèm dấu nháy.",
            "Sai: Code hợp lệ.",
        ), 1))
    rows.append(_row(
        "Interpreter khác Compiler ở điểm nào (theo bài intro)?",
        (
            "Interpreter đọc và chạy từng phần, không cần biên dịch cả file trước",
            "Interpreter luôn tạo file .exe",
            "Compiler không cần mã nguồn",
            "Interpreter chỉ dùng cho C",
        ),
        (
            "Đúng: Python chạy qua interpreter, phù hợp chạy thử nhanh.",
            "Sai: Interpreter không bắt buộc tạo .exe.",
            "Sai: Compiler cần mã nguồn.",
            "Sai: Interpreter của Python, không phải C.",
        ), 1))
    rows.append(_code_row(
        "Đoạn code sau in ra gì?",
        'sem = "HK1"\nprint(sem)',
        ("HK1", "sem", '"HK1"', "Lỗi"),
        (
            "Đúng: in giá trị chuỗi HK1.",
            "Sai: Không in tên biến.",
            "Sai: Dấu nháy không in ra.",
            "Sai: Code hợp lệ.",
        ), 1))

    assert len(rows) == 45
    return rows
