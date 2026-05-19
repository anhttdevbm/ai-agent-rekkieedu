"""Tạo Excel quiz session đầu giờ đã sửa (bỏ câu ba lông, giữ câu kỹ thuật đúng)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Phạm vi Lesson 01–06: không dùng toán tử số / if / sep trong khối Code.
_INTRO_FORBIDDEN_IN_CODE = re.compile(
    r"[\+\-\*/%]|//|\bif\s|\belif\b|\bfor\s|\bwhile\s|\bsep\s*=|\bend\s*=|"
    r'["\'][^"\']*["\']\s*\*|\blen\s*\(|\btype\s*\(',
    re.I | re.UNICODE,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cham_bai.quiz_excel import (
    ensure_session_warmup_quiz_example_template,
    fill_template_session_warmup_quiz,
)
from cham_bai.quiz_gen import _session_quiz_blob_has_fluff, _validate_session_quiz_block_forbidden_question_styles
from cham_bai.session_warmup_plan import apply_session_warmup_plan


def _row(
    q: str,
    answers: tuple[str, str, str, str],
    explanations: tuple[str, str, str, str],
    correct: int,
) -> dict[str, object]:
    return {
        "question_content": q,
        "answer_1": answers[0],
        "explanation_answer_1": explanations[0],
        "answer_2": answers[1],
        "explanation_answer_2": explanations[1],
        "answer_3": answers[2],
        "explanation_answer_3": explanations[2],
        "answer_4": answers[3],
        "explanation_answer_4": explanations[3],
        "isCorrect": correct,
        "difficulty": 7,
    }


def _code_row(
    q: str,
    code: str,
    answers: tuple[str, str, str, str],
    explanations: tuple[str, str, str, str],
    correct: int,
) -> dict[str, object]:
    return _row(f"{q}\n\nCode:\n{code}", answers, explanations, correct)


def build_intro_lesson_rows() -> list[dict[str, object]]:
    """45 câu kỹ thuật L01–L06 (chưa gán difficulty/category)."""
    rows: list[dict[str, object]] = []

    rows.append(
        _row(
            "Đặc điểm nào giúp Python phù hợp cho người mới bắt đầu học lập trình?",
            (
                "Cú pháp đơn giản, dễ đọc và gần với ngôn ngữ tự nhiên",
                "Bắt buộc phải khai báo kiểu dữ liệu cho mọi biến",
                "Luôn phải viết chương trình trong hàm main()",
                "Phải dùng dấu ngoặc nhọn { } để xác định khối lệnh",
            ),
            (
                "Đúng: Python có cú pháp rõ ràng, dễ đọc, giúp người học tập trung vào tư duy lập trình.",
                "Sai: Python là ngôn ngữ kiểu động, không bắt buộc khai báo kiểu trước.",
                "Sai: Python không bắt buộc hàm main() như Java/C.",
                "Sai: Python dùng indentation, không dùng { }.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Python xác định khối lệnh bằng cách nào thay vì dùng dấu { }?",
            (
                "Sử dụng khoảng trắng đầu dòng (indentation)",
                "Sử dụng dấu ngoặc đơn ( )",
                "Sử dụng dấu chấm phẩy ;",
                "Sử dụng từ khóa begin/end",
            ),
            (
                "Đúng: Python dùng indentation thay cho { }.",
                "Sai: Dấu ngoặc đơn không xác định khối lệnh.",
                "Sai: Dấu chấm phẩy không xác định khối lệnh.",
                "Sai: Python không dùng begin/end.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Đặc điểm 'Dynamic Typing' trong Python có nghĩa là gì?",
            (
                "Không cần khai báo kiểu dữ liệu trước; Python tự xác định khi chạy",
                "Phải khai báo kiểu dữ liệu trước khi sử dụng biến",
                "Kiểu dữ liệu được xác định lúc biên dịch",
                "Chỉ cho phép dùng một kiểu dữ liệu duy nhất trong chương trình",
            ),
            (
                "Đúng: Python tự xác định kiểu khi chạy.",
                "Sai: Đây là đặc điểm ngôn ngữ kiểu tĩnh.",
                "Sai: Python không cần bước biên dịch riêng cho kiểu.",
                "Sai: Python hỗ trợ nhiều kiểu dữ liệu.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Hàm nào được dùng để hiển thị nội dung ra màn hình trong Python?",
            ("print()", "display()", "show()", "output()"),
            (
                "Đúng: print() hiển thị nội dung ra màn hình.",
                "Sai: display() không phải hàm cơ bản trong bài.",
                "Sai: show() không phải hàm xuất màn hình cơ bản.",
                "Sai: output() không được nhắc trong bài.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau khi chạy sẽ hiển thị gì?",
            'print("Chào mừng bạn đến với khóa học Python!")',
            (
                "Chào mừng bạn đến với khóa học Python!",
                'print("Chào mừng bạn đến với khóa học Python!")',
                '"Chào mừng bạn đến với khóa học Python!"',
                "Không hiển thị gì vì thiếu dấu chấm phẩy",
            ),
            (
                "Đúng: print() in nội dung chuỗi, không kèm dấu ngoặc kép.",
                "Sai: Màn hình không in lại lệnh gọi hàm.",
                "Sai: Dấu ngoặc kép không được in ra.",
                "Sai: Python không yêu cầu dấu chấm phẩy cuối dòng.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Triết lý thiết kế của Python là gì?",
            (
                "Code phải đơn giản – dễ đọc – dễ hiểu",
                "Code phải chạy nhanh nhất có thể",
                "Code phải quản lý bộ nhớ thủ công",
                "Code phải sử dụng nhiều cú pháp phức tạp để tối ưu",
            ),
            (
                "Đúng: triết lý đơn giản, dễ đọc, dễ hiểu.",
                "Sai: Tốc độ không phải triết lý chính trong bài.",
                "Sai: Python không yêu cầu quản lý bộ nhớ thủ công.",
                "Sai: Python hướng đến cú pháp đơn giản.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Python thuộc loại ngôn ngữ nào xét về mức độ trừu tượng?",
            (
                "Ngôn ngữ bậc cao (High-level)",
                "Ngôn ngữ bậc thấp (Low-level)",
                "Ngôn ngữ máy (Machine language)",
                "Ngôn ngữ hợp ngữ (Assembly)",
            ),
            (
                "Đúng: Python là ngôn ngữ bậc cao.",
                "Sai: Ngôn ngữ bậc thấp gần phần cứng.",
                "Sai: Ngôn ngữ máy là mã nhị phân.",
                "Sai: Assembly là bậc thấp.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Python chạy chương trình thông qua cơ chế nào?",
            (
                "Trình thông dịch (Interpreter)",
                "Biên dịch toàn bộ trước khi chạy (Compiler)",
                "Chạy trực tiếp trên phần cứng",
                "Chuyển sang mã máy rồi lưu file thực thi",
            ),
            (
                "Đúng: Python chạy qua trình thông dịch.",
                "Sai: Python không biên dịch toàn bộ trước như C.",
                "Sai: Python không chạy trực tiếp trên phần cứng.",
                "Sai: Python không tạo file .exe như C/C++.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Lợi ích nào của Python so với C/Java khi xây dựng chương trình xử lý dữ liệu đơn giản?",
            (
                "Cú pháp ngắn gọn, không cần khai báo kiểu hay quản lý bộ nhớ phức tạp",
                "Python chạy nhanh hơn C và Java trong mọi trường hợp",
                "Python bắt buộc khai báo kiểu dữ liệu giúp tránh lỗi",
                "Python dùng dấu { } giúp code rõ ràng hơn C",
            ),
            (
                "Đúng: Python tránh khai báo kiểu và cú pháp dài.",
                "Sai: Bài không khẳng định Python nhanh hơn mọi trường hợp.",
                "Sai: Python là kiểu động.",
                "Sai: Python dùng indentation, không dùng { }.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị kết quả gì?",
            'print("Python dễ học")',
            (
                "Python dễ học",
                '"Python dễ học"',
                'print("Python dễ học")',
                "Chương trình báo lỗi",
            ),
            (
                "Đúng: print() in nội dung chuỗi, không kèm dấu ngoặc.",
                "Sai: Dấu ngoặc kép không được in ra.",
                "Sai: Python không in lại cả lệnh.",
                "Sai: Cú pháp hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị kết quả gì?",
            "x = 5\nprint(x)",
            ("5", "x", '"5"', "Chương trình báo lỗi"),
            (
                "Đúng: print(x) in giá trị 5.",
                "Sai: Không in tên biến.",
                "Sai: x là số nguyên, không phải chuỗi.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị kết quả gì?",
            'message = "Xin chào Python"\nprint(message)',
            (
                "Xin chào Python",
                "message",
                '"Xin chào Python"',
                "Chương trình báo lỗi",
            ),
            (
                "Đúng: in giá trị chuỗi trong biến.",
                "Sai: Không in tên biến.",
                "Sai: Dấu ngoặc kép không in ra.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị kết quả gì?",
            'name = "Python"\nprint(name)',
            ("Python", "name", '"Python"', "Chương trình báo lỗi"),
            (
                "Đúng: in giá trị biến name.",
                "Sai: Không in tên biến.",
                "Sai: Dấu ngoặc kép không in ra.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị kết quả gì?",
            'score = 8\nprint("Điểm của bạn là", score)',
            (
                "Điểm của bạn là 8",
                "Điểm của bạn là score",
                '"Điểm của bạn là" 8',
                "Chương trình báo lỗi",
            ),
            (
                "Đúng: print() nối chuỗi và giá trị biến.",
                "Sai: score là biến, in giá trị 8.",
                "Sai: Dấu ngoặc kép không in ra.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Chương trình Python tối thiểu in ra màn hình cần bao nhiêu dòng code?",
            (
                "Một dòng duy nhất",
                "Ít nhất ba dòng: khai báo, xử lý, xuất kết quả",
                "Hai dòng: import thư viện và lệnh in",
                "Bốn dòng vì cần khai báo hàm main()",
            ),
            (
                "Đúng: một dòng print() đã là chương trình hoàn chỉnh.",
                "Sai: Bài không yêu cầu ba bước riêng.",
                "Sai: Không cần import cho ví dụ cơ bản.",
                "Sai: Python không bắt buộc main().",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị kết quả gì?",
            "x = 10\nprint(x)",
            ("10", "x", '"10"', "Chương trình báo lỗi"),
            (
                "Đúng: in giá trị 10.",
                "Sai: Không in tên biến.",
                "Sai: x là số nguyên.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Trong Python, khi tạo biến, lập trình viên cần làm gì với kiểu dữ liệu?",
            (
                "Khai báo kiểu dữ liệu trước khi gán giá trị",
                "Không cần khai báo; Python tự xác định lúc chạy",
                "Chọn kiểu dữ liệu từ danh sách cố định",
                "Khai báo kiểu dữ liệu sau khi gán giá trị",
            ),
            (
                "Sai: Python không bắt buộc khai báo kiểu trước.",
                "Đúng: Python tự xác định kiểu khi chạy (Dynamic Typing).",
                "Sai: Không có bước chọn kiểu từ danh sách cố định.",
                "Sai: Không cần khai báo kiểu sau khi gán.",
            ),
            2,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị kết quả gì?",
            "age = 18\nprint(age)",
            ("18", "age", '"age"', "Chương trình báo lỗi"),
            (
                "Đúng: in giá trị 18.",
                "Sai: Không in tên biến.",
                "Sai: age là số, không phải chuỗi 'age'.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )

    # --- Thay câu 19–20 (lĩnh vực ứng dụng) ---
    rows.append(
        _row(
            "Trong Python, ký hiệu nào dùng để viết chú thích (comment)?",
            ("#", "//", "/*", "--"),
            (
                "Đúng: Python dùng # cho comment.",
                "Sai: // là comment trong C/Java, không phải Python.",
                "Sai: /* */ không dùng cho comment một dòng trong Python.",
                "Sai: -- không phải cú pháp comment Python.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau in ra gì?",
            'print("A", "B")',
            ("A B", "AB", "A,B", "Lỗi cú pháp"),
            (
                "Đúng: print() mặc định cách các đối số bằng khoảng trắng.",
                "Sai: Không nối liền không khoảng.",
                "Sai: Dấu phẩy trong code không in ra.",
                "Sai: Cú pháp hợp lệ.",
            ),
            1,
        )
    )

    # Q21 — thay câu Google/Netflix
    rows.append(
        _row(
            "File chương trình Python thường có phần mở rộng nào?",
            (".py", ".java", ".exe", ".html"),
            (
                "Đúng: file Python dùng đuôi .py.",
                "Sai: .java là Java.",
                "Sai: .exe là file thực thi Windows, không phải mã nguồn Python.",
                "Sai: .html là trang web.",
            ),
            1,
        )
    )

    # Q22 — sửa đáp án đúng
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị nội dung nào ra màn hình?",
            'print("Chào mừng bạn đến với khóa học Python!")',
            (
                "print()",
                '"Chào mừng bạn đến với khóa học Python!"',
                "Chào mừng bạn đến với khóa học Python!",
                "Toàn bộ dòng lệnh kể cả print()",
            ),
            (
                "Sai: print() là hàm, không phải nội dung in ra.",
                "Sai: Dấu ngoặc kép không hiển thị trên màn hình.",
                "Đúng: print() in chuỗi không kèm dấu ngoặc kép.",
                "Sai: Chỉ in nội dung bên trong print().",
            ),
            3,
        )
    )

    rows.append(
        _row(
            "Cú pháp Python gần với ngôn ngữ tự nhiên mang lại lợi ích gì?",
            (
                "Chương trình dễ đọc và dễ hiểu hơn",
                "Chương trình chạy nhanh hơn ngôn ngữ bậc thấp",
                "Không cần trình thông dịch khi chạy",
                "Tự động quản lý bộ nhớ cho lập trình viên",
            ),
            (
                "Đúng: cú pháp gần tự nhiên giúp dễ đọc, dễ hiểu.",
                "Sai: Bài không đề cập tốc độ chạy.",
                "Sai: Python vẫn cần trình thông dịch.",
                "Sai: Bài không đề cập quản lý bộ nhớ.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị kết quả gì?",
            'language = "Python"\nprint(language)',
            ("Python", "language", '"Python"', "Chương trình báo lỗi"),
            (
                "Đúng: in giá trị biến.",
                "Sai: Không in tên biến.",
                "Sai: Dấu ngoặc kép không in ra.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Trình thông dịch của Python cho phép lập trình viên làm gì mà không cần biên dịch phức tạp?",
            (
                "Chạy thử chương trình ngay lập tức",
                "Khai báo kiểu dữ liệu tự động",
                "Sử dụng dấu { } để xác định khối lệnh",
                "Xuất file thực thi (.exe) trực tiếp",
            ),
            (
                "Đúng: interpreter cho phép chạy thử ngay.",
                "Sai: Liên quan Dynamic Typing, không phải interpreter.",
                "Sai: Python dùng indentation.",
                "Sai: Bài không đề cập xuất .exe.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị kết quả gì?",
            'course = "Python cơ bản"\nprint(course)',
            ("Python cơ bản", "course", '"Python cơ bản"', "Chương trình báo lỗi"),
            (
                "Đúng: in giá trị chuỗi trong biến.",
                "Sai: Không in tên biến.",
                "Sai: Dấu ngoặc kép không in ra.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau sẽ hiển thị kết quả gì?",
            'print("Tôi đang học Python")',
            (
                "Tôi đang học Python",
                '"Tôi đang học Python"',
                'print("Tôi đang học Python")',
                "Chương trình báo lỗi",
            ),
            (
                "Đúng: print() in nội dung chuỗi.",
                "Sai: Dấu ngoặc kép không in ra.",
                "Sai: Không in lại cả lệnh.",
                "Sai: Cú pháp hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Trong Python, biến được dùng để làm gì?",
            (
                "Lưu trữ giá trị để sử dụng trong chương trình",
                "Chỉ dùng để hiển thị nội dung ra màn hình",
                "Chỉ dùng để viết chú thích",
                "Dùng để kết thúc chương trình",
            ),
            (
                "Đúng: biến lưu dữ liệu (số, chuỗi…).",
                "Sai: Hiển thị là chức năng print().",
                "Sai: Chú thích dùng #.",
                "Sai: Biến không kết thúc chương trình.",
            ),
            1,
        )
    )

    # --- Thay câu 29–45 vi phạm ---
    rows.append(
        _code_row(
            "Đoạn code sau in ra gì?",
            'weekday = "T2"\nprint(weekday)',
            ("T2", "weekday", '"T2"', "Lỗi"),
            (
                "Đúng: print() in giá trị chuỗi đã gán cho biến.",
                "Sai: Không in tên biến.",
                "Sai: Dấu ngoặc kép không in ra.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Python sử dụng gì để xác định khối lệnh, và điều này khác với đa số ngôn ngữ khác như thế nào?",
            (
                "Dùng khoảng trắng đầu dòng (indentation), thay vì dấu { }",
                "Dùng dấu ; cuối mỗi dòng, thay vì dấu { }",
                "Dùng dấu ( ) bao quanh khối lệnh, thay vì dấu { }",
                "Dùng từ khóa BEGIN/END, thay vì dấu { }",
            ),
            (
                "Đúng: indentation thay cho { }.",
                "Sai: ; không xác định khối lệnh.",
                "Sai: ( ) không xác định khối.",
                "Sai: Python không dùng BEGIN/END.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Khi gán price = 9.99 trong Python, kiểu dữ liệu của price thường là gì?",
            ("float", "int", "str", "bool"),
            (
                "Đúng: số có phần thập phân là float.",
                "Sai: int chỉ cho số nguyên.",
                "Sai: str là chuỗi.",
                "Sai: bool là True/False.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau in ra gì?",
            'print("Hoa", "Mai")',
            ("Hoa Mai", "HoaMai", "Hoa, Mai", "Lỗi"),
            (
                "Đúng: print() nhiều đối số cách nhau bằng khoảng trắng.",
                "Sai: Không nối liền không khoảng.",
                "Sai: Dấu phẩy trong code không in ra.",
                "Sai: Cú pháp hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Nếu thụt lề (indentation) sai trong khối lệnh Python, điều gì thường xảy ra?",
            (
                "Chương trình báo lỗi IndentationError",
                "Chương trình tự sửa thụt lề",
                "Python bỏ qua khối lệnh đó",
                "Chương trình chạy nhưng in sai kết quả",
            ),
            (
                "Đúng: sai thụt lề gây IndentationError.",
                "Sai: Python không tự sửa thụt lề.",
                "Sai: Không âm thầm bỏ qua khối lệnh.",
                "Sai: Thường là lỗi cú pháp, không chạy âm thầm sai.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau in ra gì?",
            'name = "An"\nprint(f"Xin chao {name}")',
            ("Xin chao An", "Xin chao name", "f\"Xin chao An\"", "Lỗi"),
            (
                "Đúng: f-string chèn giá trị biến name vào chuỗi.",
                "Sai: Không in nguyên văn tên biến.",
                "Sai: Không in cả cú pháp f-string.",
                "Sai: f-string hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Phép gán nào hợp lệ trong Python?",
            ('name = "An"', 'int name = "An"', 'name := int("An")', "string name = An"),
            (
                "Đúng: gán chuỗi cho biến không cần khai báo kiểu.",
                "Sai: Python không dùng int name = …",
                "Sai: := và ép kiểu không phải cú pháp intro trong bài.",
                "Sai: string name không phải cú pháp Python.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Trong Python, chuỗi (string) có thể được đặt trong dấu ngoặc nào?",
            (
                "Cả dấu nháy đơn ' ' và nháy kép \" \"",
                "Chỉ dấu nháy kép \" \"",
                "Chỉ dấu nháy đơn ' '",
                "Chỉ dấu ngoặc vuông [ ]",
            ),
            (
                "Đúng: Python chấp nhận cả ' và \".",
                "Sai: Không bắt buộc chỉ một loại.",
                "Sai: Không bắt buộc chỉ một loại.",
                "Sai: [ ] dùng cho list, không phải string.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Hàm str(5) trong Python trả về giá trị nào?",
            ("5", "int", "float", "Lỗi kiểu"),
            (
                "Đúng: str() chuyển số 5 thành chuỗi (hiển thị là 5).",
                "Sai: int là kiểu trước khi ép, không phải kết quả str().",
                "Sai: float là số thực, không phải kết quả str(5).",
                "Sai: str(5) hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Nhận định nào về Python là đúng theo bài giới thiệu?",
            (
                "Python mạnh khi kết hợp hệ sinh thái thư viện phong phú",
                "Python yếu hơn mọi ngôn ngữ vì cú pháp đơn giản",
                "Python chỉ dùng được cho người mới học",
                "Python bắt buộc biên dịch trước khi chạy",
            ),
            (
                "Đúng: bài nhấn mạnh hệ sinh thái thư viện.",
                "Sai: Cú pháp đơn giản không đồng nghĩa yếu.",
                "Sai: Python dùng trong nhiều hệ thống lớn.",
                "Sai: Python dùng interpreter.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau in ra gì?",
            'print("Hi", "there")',
            ("Hi there", "Hithere", "Hi, there", "Lỗi"),
            (
                "Đúng: nhiều chuỗi trong print() cách nhau bằng khoảng trắng.",
                "Sai: Không nối liền.",
                "Sai: Dấu phẩy không in ra.",
                "Sai: Cú pháp hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau in ra gì?",
            'label = "Python"\nprint(label)',
            ("Python", "label", '"Python"', "Lỗi"),
            (
                "Đúng: print() in giá trị chuỗi trong biến.",
                "Sai: Không in tên biến.",
                "Sai: Dấu ngoặc kép không in ra.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau in ra gì?",
            "score = 9\nprint(score)",
            ("9", "score", '"9"', "Lỗi"),
            (
                "Đúng: print() in giá trị số đã gán cho biến.",
                "Sai: Không in tên biến.",
                "Sai: Không in kèm dấu ngoặc.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Đặc điểm nào của Python giúp lập trình viên chạy thử chương trình ngay lập tức?",
            (
                "Chạy thông qua trình thông dịch",
                "Sử dụng indentation thay dấu { }",
                "Kiểu dữ liệu động",
                "Cú pháp gần ngôn ngữ tự nhiên",
            ),
            (
                "Đúng: interpreter cho phép chạy thử ngay.",
                "Sai: Indentation liên quan khối lệnh.",
                "Sai: Dynamic Typing liên quan khai báo biến.",
                "Sai: Cú pháp tự nhiên giúp đọc, không phải chạy thử.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau in ra gì?",
            "count = 12\nprint(count)",
            ("12", "count", '"12"', "Lỗi"),
            (
                "Đúng: print() in giá trị số trong biến.",
                "Sai: Không in tên biến.",
                "Sai: Không in kèm dấu ngoặc.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    rows.append(
        _row(
            "Kỹ thuật dùng khoảng trắng đầu dòng để xác định khối lệnh trong Python gọi là gì?",
            ("Indentation", "Dynamic Typing", "Interpretation", "Compilation"),
            (
                "Đúng: bài gọi là indentation.",
                "Sai: Dynamic Typing liên quan kiểu biến.",
                "Sai: Interpretation là cơ chế chạy.",
                "Sai: Compilation là biên dịch.",
            ),
            1,
        )
    )
    rows.append(
        _code_row(
            "Đoạn code sau in ra gì?",
            "total = 6\nprint(total)",
            ("6", "total", '"6"', "Lỗi"),
            (
                "Đúng: print() in giá trị số đã gán cho biến.",
                "Sai: Không in tên biến.",
                "Sai: Không in kèm dấu ngoặc.",
                "Sai: Code hợp lệ.",
            ),
            1,
        )
    )
    assert len(rows) == 45
    return rows


def build_rows() -> list[dict[str, object]]:
    rows = build_intro_lesson_rows()
    apply_session_warmup_plan(rows, prev_count=0)
    return rows


def _validate_intro_lesson_scope(rows: list[dict[str, object]]) -> None:
    for i, r in enumerate(rows):
        q = str(r.get("question_content") or "")
        if "Code:" not in q:
            continue
        code = q.split("Code:", 1)[1]
        if _INTRO_FORBIDDEN_IN_CODE.search(code):
            raise SystemExit(
                f"Câu {i + 1} vượt phạm vi L01–06 (chỉ print/biến/ép kiểu/f-string): "
                f"{code.strip()[:80]}"
            )


def main() -> None:
    rows = build_rows()
    _validate_intro_lesson_scope(rows)
    for i, r in enumerate(rows):
        q = str(r["question_content"])
        hit = _session_quiz_blob_has_fluff(q)
        if hit:
            raise SystemExit(f"Câu {i + 1} vẫn fluff: {hit[0]} — {q[:80]}")
    _validate_session_quiz_block_forbidden_question_styles(
        [{"question_content": r["question_content"]} for r in rows],
        [],
    )

    out = ROOT / "output" / "Quizz_Session_Dau_Gio_Python_Intro_da_sua.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    tpl = ensure_session_warmup_quiz_example_template()
    fill_template_session_warmup_quiz(tpl, out, rows)
    print(f"Đã ghi {len(rows)} câu → {out}")


if __name__ == "__main__":
    main()
