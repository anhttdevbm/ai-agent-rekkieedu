"""Quiz Session 02 đầu giờ — 30 BÀI CŨ (S01) + 15 BÀI MỚI (toán tử & if/elif)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_corrected_session_warmup_quiz import (  # noqa: E402
    _INTRO_FORBIDDEN_IN_CODE,
    _code_row,
    _row,
)
from cham_bai.quiz_excel import (  # noqa: E402
    ensure_session_warmup_quiz_example_template,
    fill_template_session_warmup_quiz,
)
from cham_bai.quiz_gen import (  # noqa: E402
    _session_quiz_blob_has_fluff,
    _validate_session_quiz_block_forbidden_question_styles,
)
from cham_bai.session_warmup_plan import apply_session_warmup_plan  # noqa: E402

_STORY_FLUFF = re.compile(
    r"\bNam\b|theo\s+kịch\s+bản|Shopee|phí\s+ship|câu\s+chuyện\s+về|PLACEHOLDER",
    re.I | re.UNICODE,
)


def _prev_rows() -> list[dict[str, object]]:
    """30 câu BÀI CŨ — cài đặt + ôn S01, giảm lặp PATH/Interpreter."""
    r: list[dict[str, object]] = []

    # PATH / cài đặt (~4 câu)
    r.append(
        _row(
            "Lệnh nào dùng để kiểm tra Python đã được cài đặt thành công trong Terminal?",
            ("python --version", "python --check", "python -install", "python --path"),
            (
                "Đây là lệnh chính xác để kiểm tra phiên bản Python trong Terminal.",
                "Không phải lệnh hợp lệ để kiểm tra Python.",
                "Không phải lệnh kiểm tra, đây là lệnh không tồn tại.",
                "Không phải lệnh kiểm tra phiên bản Python.",
            ),
            1,
        )
    )
    r.append(
        _row(
            "Khi cài Python trên Windows, bước nào giúp lệnh `python` chạy được trong Terminal?",
            (
                "Tích chọn 'Add Python to PATH'",
                "Chọn 'Install for all users'",
                "Tích chọn 'Create shortcut on Desktop'",
                "Chọn thư mục cài đặt tùy chỉnh",
            ),
            (
                "Thiếu bước này khiến hệ điều hành không tìm thấy lệnh python.",
                "Tùy chọn này không ảnh hưởng đến việc chạy lệnh python trong Terminal.",
                "Shortcut desktop không liên quan đến biến môi trường PATH.",
                "Thư mục cài đặt không phải nguyên nhân gây lỗi 'not recognized'.",
            ),
            1,
        )
    )
    r.append(
        _row(
            "PATH Variable là gì?",
            (
                "Danh sách các thư mục mà hệ điều hành tìm kiếm khi gõ lệnh trong Terminal",
                "Tên file cấu hình của Python Interpreter",
                "Biến lưu trữ phiên bản Python đang dùng",
                "Đường dẫn đến file mã nguồn Python",
            ),
            (
                "Đúng: PATH là danh sách thư mục hệ điều hành dùng để tìm lệnh khi gõ vào Terminal.",
                "File cấu hình không phải định nghĩa của PATH Variable.",
                "PATH không lưu thông tin phiên bản Python.",
                "PATH không chỉ trỏ đến file mã nguồn cụ thể.",
            ),
            1,
        )
    )
    r.append(
        _row(
            "Lỗi 'python' is not recognized as an internal or external command thường do?",
            (
                "Chưa cài Python hoặc chưa cấu hình biến môi trường PATH",
                "VS Code chưa được cài đặt extension Python",
                "File mã nguồn bị lỗi cú pháp",
                "Python 2.x không tương thích với hệ điều hành",
            ),
            (
                "Đúng: Thiếu Interpreter hoặc chưa thêm vào PATH gây ra lỗi này.",
                "Extension VS Code không liên quan đến lỗi nhận diện lệnh python trong Terminal.",
                "Lỗi cú pháp không gây ra lỗi 'not recognized'.",
                "Phiên bản Python không phải nguyên nhân của lỗi này.",
            ),
            1,
        )
    )

    # Interpreter (~2 câu, diễn đạt mềm)
    r.append(
        _row(
            "Python Interpreter có vai trò gì?",
            (
                "Đọc và thực thi chương trình Python, giúp chạy code trên máy",
                "Biên dịch toàn bộ mã nguồn sang mã máy rồi mới chạy",
                "Chuyển code Python thành ngôn ngữ C++ để thực thi",
                "Lưu trữ mã nguồn Python dưới dạng văn bản",
            ),
            (
                "Đúng: Interpreter đọc và chạy chương trình Python.",
                "Đây là mô tả của Compiler, không phải Interpreter.",
                "Interpreter không chuyển sang C++.",
                "Lưu trữ văn bản là chức năng của trình soạn thảo, không phải Interpreter.",
            ),
            1,
        )
    )
    r.append(
        _row(
            "Vì sao máy tính không thể hiểu trực tiếp file .py mà cần Interpreter?",
            (
                "Máy tính chỉ hiểu mã nhị phân (0 và 1), Python là ngôn ngữ bậc cao",
                "Máy tính chỉ hiểu ngôn ngữ C, không hiểu Python",
                "Python dùng ký tự Unicode mà CPU không xử lý được",
                "Python cần kết nối internet để chạy",
            ),
            (
                "Đúng: Máy chỉ hiểu nhị phân; Python là ngôn ngữ bậc cao cần thông dịch.",
                "Máy tính không giới hạn chỉ hiểu C; đây không phải lý do được nêu.",
                "Unicode không phải lý do được nêu.",
                "Python không cần internet để chạy.",
            ),
            1,
        )
    )

    # VS Code / thực hành
    r.append(_row("IDE là viết tắt của cụm từ nào?", (
        "Integrated Development Environment", "Internal Debug Extension",
        "Interpreted Data Engine", "Installed Development Extension",
    ), (
        "Đúng: IDE = Integrated Development Environment.",
        "Không phải nghĩa của IDE.", "Không phải nghĩa của IDE.", "Không phải nghĩa của IDE.",
    ), 1))
    r.append(_row(
        "Extension Python by Microsoft trong VS Code có tác dụng gì?",
        (
            "Hỗ trợ viết/chạy Python: gợi ý code, phát hiện lỗi, chạy file .py",
            "Cài đặt Python Interpreter vào máy tính",
            "Tự động tải thư viện Python từ internet",
            "Chuyển đổi file .py sang file .exe",
        ),
        (
            "Đúng: Extension nâng cấp hỗ trợ Python trong VS Code.",
            "Extension không cài Interpreter; tải từ python.org.",
            "Extension không tự động tải thư viện.",
            "Chuyển .py sang .exe không phải chức năng của extension này.",
        ), 1))
    r.append(_row(
        "Notepad không phù hợp lập trình Python vì?",
        (
            "Chỉ soạn văn bản, không chạy/debug code, không gợi ý cú pháp",
            "Không hỗ trợ UTF-8",
            "Không thể mở file .py",
            "Tốc độ xử lý quá chậm",
        ),
        (
            "Đúng: Notepad thiếu tính năng IDE.",
            "Vấn đề mã hóa không phải lý do chính trong bài.",
            "Notepad có thể mở .py nhưng thiếu tính năng lập trình.",
            "Tốc độ không phải lý do được nêu.",
        ), 1))
    r.append(_row(
        "Phím tắt mở Command Palette để chọn Python Interpreter trong VS Code?",
        ("Ctrl + Shift + P", "Ctrl + Alt + P", "Ctrl + Shift + I", "Alt + F4"),
        (
            "Đúng: Ctrl + Shift + P mở Command Palette.",
            "Không phải phím tắt được đề cập.",
            "Không phải phím tắt được đề cập.",
            "Alt + F4 đóng cửa sổ.",
        ), 1))
    r.append(_row(
        "Linter/Formatter trong extension Python có chức năng gì?",
        (
            "Tự động phát hiện lỗi cú pháp và căn chỉnh code",
            "Biên dịch code Python sang mã máy",
            "Quản lý phiên bản Python được cài đặt",
            "Tải và cài đặt thư viện Python tự động",
        ),
        (
            "Đúng: Linter phát hiện lỗi; Formatter căn chỉnh code.",
            "Biên dịch sang mã máy không phải chức năng của Linter/Formatter.",
            "Quản lý phiên bản là chức năng khác.",
            "Cài thư viện là chức năng của pip.",
        ), 1))
    r.append(_row(
        "Để chạy file .py trong VS Code, thao tác nào đúng?",
        (
            "Chuột phải file > Run Python File in Terminal",
            "Nhấn F5 để bật chế độ debug",
            "Gõ lệnh compile ten_file.py trong Terminal",
            "Kéo thả file vào cửa sổ Terminal",
        ),
        (
            "Đúng: Run Python File in Terminal.",
            "F5 không được đề cập là cách chạy file cơ bản.",
            "Lệnh compile không tồn tại.",
            "Kéo thả không phải cách được mô tả.",
        ), 1))
    r.append(_row(
        "Phần mở rộng (extension) của file chương trình Python thường là?",
        (".py", ".python", ".exe", ".txt"),
        (
            "Đúng: file Python dùng đuôi .py.",
            ".python không phải quy ước chuẩn.",
            ".exe là file thực thi, không phải mã nguồn.",
            ".txt là văn bản thuần.",
        ), 1))
    r.append(_row(
        "Phiên bản Python nào không nên cài đặt?",
        ("Python 2.x", "Python 3.x", "Python 3.11", "Python 3.12"),
        (
            "Đúng: Python 2.x đã nghỉ hưu.",
            "Python 3.x là dòng được khuyến nghị.",
            "Python 3.11 thuộc dòng 3.x.",
            "Python 3.12 thuộc dòng 3.x.",
        ), 1))
    r.append(_row(
        "Trang web chính thức để tải Python Interpreter?",
        ("python.org/downloads", "python.com/downloads", "github.com/python", "pypi.org/downloads"),
        (
            "Đúng: python.org/downloads.",
            "python.com không phải trang chính thức được đề cập.",
            "GitHub không phải nơi tải Interpreter chính thức.",
            "PyPI là kho thư viện.",
        ), 1))
    r.append(_row(
        "Khi máy có nhiều phiên bản Python, cách rõ ràng nhất để VS Code chọn đúng bản?",
        (
            "Ctrl + Shift + P > chọn Python: Select Interpreter",
            "Xóa các phiên bản cũ khỏi máy",
            "Chỉnh sửa trực tiếp biến PATH",
            "Cài lại extension Python by Microsoft",
        ),
        (
            "Đúng: Command Palette để chọn Interpreter trong VS Code.",
            "Không bắt buộc xóa phiên bản cũ.",
            "PATH có thể ảnh hưởng Terminal, nhưng trong VS Code nên chọn Interpreter trực tiếp.",
            "Cài lại extension không thay cho việc chọn Interpreter.",
        ), 1))
    r.append(_row(
        "Lỗi phổ biến nhất khiến lệnh `python` không chạy trong Terminal?",
        ("Quên tích Add Python to PATH khi cài", "Cài Python 3 thay vì 2", "Chưa cài extension VS Code", "Chưa mở VS Code"),
        (
            "Đúng: quên Add PATH là lỗi phổ biến nhất.",
            "Python 3.x là bản nên dùng.",
            "Extension không ảnh hưởng lệnh python trong Terminal.",
            "Terminal hoạt động độc lập VS Code.",
        ), 1))
    r.append(_row(
        "Để cài extension Python trong VS Code, vào mục nào?",
        (
            "Extensions (biểu tượng 4 ô vuông)",
            "Settings (biểu tượng bánh răng)",
            "Terminal (biểu tượng dấu >_)",
            "Explorer (biểu tượng trang giấy)",
        ),
        (
            "Đúng: mục Extensions.",
            "Settings để cấu hình, không cài extension.",
            "Terminal để chạy lệnh.",
            "Explorer để quản lý file.",
        ), 1))
    r.append(_row(
        "Integrated Terminal trong VS Code dùng để làm gì?",
        (
            "Chạy lệnh (vd. python, pip) và xem kết quả ngay trong editor",
            "Chỉ xem log lỗi, không gõ lệnh được",
            "Chỉ dùng để cài extension",
            "Thay thế hoàn toàn Python Interpreter",
        ),
        (
            "Đúng: Terminal tích hợp để chạy lệnh và xem output.",
            "Terminal vẫn nhận lệnh từ người dùng.",
            "Cài extension qua mục Extensions.",
            "Interpreter là chương trình chạy Python, không phải Terminal.",
        ), 1))
    r.append(_row(
        "Phím tắt mở Integrated Terminal trong VS Code (Windows) thường là?",
        ("Ctrl + `", "Ctrl + T", "Ctrl + Shift + T", "Alt + ~"),
        (
            "Đúng: Ctrl + ` mở/ẩn Terminal.",
            "Không phải phím tắt mặc định cho Terminal.",
            "Không phải phím tắt mặc định cho Terminal.",
            "Không phải phím tắt mặc định cho Terminal.",
        ), 1))

    # Ôn S01 L03–L06
    r.append(_row(
        "Đặc điểm 'Dynamic Typing' trong Python có nghĩa là gì?",
        (
            "Không cần khai báo kiểu trước; Python tự xác định khi chạy",
            "Phải khai báo kiểu trước khi dùng biến",
            "Kiểu được xác định lúc biên dịch",
            "Chỉ một kiểu dữ liệu trong chương trình",
        ),
        (
            "Đúng: Python tự xác định kiểu khi chạy.",
            "Sai: kiểu tĩnh như C/Java.",
            "Sai: Python không biên dịch riêng cho kiểu.",
            "Sai: Python hỗ trợ nhiều kiểu.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        'print("Hello")',
        ("Hello", '"Hello"', 'print("Hello")', "Lỗi"),
        (
            "Đúng: print in nội dung chuỗi, không kèm dấu nháy.",
            "Sai: dấu nháy chỉ có trong mã nguồn, không in ra màn hình.",
            "Sai: đây là câu lệnh, không phải kết quả in.",
            "Sai: cú pháp hợp lệ, không báo lỗi.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        "x = 5\nprint(x)",
        ("5", "x", '"5"', "Lỗi"),
        (
            "Đúng: print(x) in giá trị biến x là 5.",
            "Sai: in giá trị biến, không in tên biến.",
            "Sai: không in kèm dấu nháy.",
            "Sai: gán và in hợp lệ.",
        ), 1))
    r.append(_row(
        "Hàm nào hiển thị nội dung ra màn hình trong Python?",
        ("print()", "display()", "show()", "output()"),
        (
            "Đúng: print() là hàm chuẩn để in ra màn hình.",
            "Sai: display() không phải hàm chuẩn của Python.",
            "Sai: show() không phải hàm chuẩn của Python.",
            "Sai: output() không phải hàm chuẩn của Python.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        'name = "An"\nprint(f"Xin chao {name}")',
        ("Xin chao An", "Xin chao name", 'f"Xin chao An"', "Lỗi"),
        (
            "Đúng: f-string thay {name} bằng giá trị An.",
            "Sai: {name} được thay bằng giá trị, không giữ nguyên chữ name.",
            "Sai: đây là cú pháp trong code, không phải output.",
            "Sai: f-string hợp lệ.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        'n = int("7")\nprint(n)',
        ("7", '"7"', "int", "Lỗi"),
        (
            "Đúng: int(\"7\") thành số 7, print in 7.",
            "Sai: sau ép kiểu là số, không còn dấu nháy.",
            "Sai: int là tên hàm, không phải kết quả in.",
            "Sai: ép kiểu và in hợp lệ.",
        ), 1))
    r.append(_row(
        "VS Code được phân loại là loại IDE nào?",
        ("Lightweight IDE", "Full-stack IDE", "Heavy IDE", "Cloud-based IDE"),
        (
            "VS Code là Lightweight IDE.",
            "Không dùng thuật ngữ Full-stack IDE.",
            "Không gọi là Heavy IDE.",
            "Không đề cập Cloud-based IDE.",
        ), 1))
    r.append(_row(
        "Người mới học Python thường gặp khó khăn khi thiếu?",
        (
            "Python Interpreter và IDE/editor phù hợp",
            "Chưa học đủ cú pháp",
            "Dùng sai Python 3.x",
            "Không có tài liệu",
        ),
        (
            "Đúng: cần Interpreter và môi trường phát triển.",
            "Cú pháp học dần.",
            "Python 3.x được khuyến nghị.",
            "Tài liệu không phải điểm nghẽn chính.",
        ), 1))
    r.append(_row(
        "Sau khi cài Python, lệnh `python --version` thường hiển thị?",
        ("Python 3.x.x", "Python is ready", "Interpreter loaded", "python --version OK"),
        (
            "Đúng: dạng Python 3.x.x.",
            "Không có thông báo này.",
            "Không có thông báo này.",
            "Đây là lệnh gõ vào, không phải kết quả.",
        ), 1))
    r.append(_row(
        "Nếu chỉ dùng Notepad thay vì IDE, hậu quả thường gặp?",
        (
            "Khó chạy/debug code, mất thời gian tìm lỗi cú pháp",
            "Code chạy chậm hơn",
            "Máy báo lỗi PATH khi lưu file",
            "Interpreter không nhận .py",
        ),
        (
            "Đúng: Notepad thiếu tính năng lập trình.",
            "Tốc độ không phụ thuộc editor.",
            "PATH không liên quan Notepad.",
            "Interpreter vẫn chạy file .py.",
        ), 1))

    assert len(r) == 30
    return r


def _current_rows() -> list[dict[str, object]]:
    """15 câu BÀI MỚI — toán tử, if/elif; chỉ 1 câu match-case (L04)."""
    r: list[dict[str, object]] = []

    r.append(_code_row(
        "Đoạn code sau in ra gì?", "print(10 + 5)", ("15", "105", "10 + 5", "Lỗi"),
        (
            "Đúng: 10 + 5 = 15, print in ra 15.",
            "Sai: 105 là nối chuỗi, không phải phép cộng số.",
            "Sai: print in kết quả tính, không in nguyên biểu thức.",
            "Sai: phép cộng hai số hợp lệ.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?", "print(5 > 3)", ("True", "False", "5", "Lỗi"),
        (
            "Đúng: 5 > 3 đúng nên biểu thức cho True.",
            "Sai: 5 lớn hơn 3 nên không ra False.",
            "Sai: in kết quả so sánh True/False, không in số 5.",
            "Sai: so sánh hợp lệ.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?", "print(True and False)", ("False", "True", "0", "Lỗi"),
        (
            "Đúng: True and False cần cả hai đúng nên kết quả là False.",
            "Sai: có False trong and nên không ra True.",
            "Sai: kết quả là bool False, không phải số 0.",
            "Sai: toán tử and hợp lệ.",
        ), 1))
    r.append(_row(
        "Từ khóa `elif` là viết tắt của?", ("Else If", "Else In", "Else Import", "End If"),
        (
            "Đúng: elif = else if, nhánh điều kiện thay thế sau if.",
            "Sai: không viết tắt Else In.",
            "Sai: không liên quan import.",
            "Sai: không phải End If.",
        ), 1))
    r.append(_row(
        "Dùng `=` thay vì `==` trong điều kiện if gây vấn đề vì?",
        ("`=` là gán, không phải so sánh", "Python tự đổi thành ==", "Cả hai đều được", "Chỉ sai với chuỗi"),
        (
            "Đúng: `=` gán giá trị; so sánh phải dùng `==`.",
            "Sai: Python không tự đổi `=` thành `==`.",
            "Sai: trong if cần biểu thức điều kiện, không phải gán.",
            "Sai: nhầm `=`/`==` sai với mọi kiểu, không chỉ chuỗi.",
        ), 1))
    r.append(_row(
        "Khối `else` trong if-elif-else có vai trò gì?",
        (
            "Xử lý mọi trường hợp còn lại", "Kiểm tra điều kiện bổ sung", "Thay thế elif", "Bắt buộc phải có",
        ),
        (
            "Đúng: else chạy khi không nhánh if/elif nào đúng.",
            "Sai: else không kiểm tra điều kiện mới.",
            "Sai: elif kiểm tra điều kiện; else không thay elif.",
            "Sai: else tùy chọn, không bắt buộc.",
        ), 1))
    r.append(_row(
        "Match-case trong Python có từ phiên bản nào?",
        ("Python 3.10", "Python 3.8", "Python 3.6", "Python 2.7"),
        (
            "Đúng: match-case có từ Python 3.10.",
            "Sai: Python 3.8 chưa có match-case.",
            "Sai: Python 3.6 chưa có match-case.",
            "Sai: Python 2.7 đã nghỉ hưu và không có match-case.",
        ), 1))
    r.append(_row(
        "Đặt điều kiện rộng (vd. `x > 0`) lên đầu if-elif thì sao?",
        (
            "Nhánh đó có thể chạy trước, bỏ qua nhánh chi tiết sau", "Python báo lỗi cú pháp",
            "Tất cả elif vẫn luôn được kiểm tra", "Chạy mọi nhánh cùng lúc",
        ),
        (
            "Đúng: Python dừng ở nhánh đúng đầu tiên, nhánh sau có thể không chạy.",
            "Sai: thứ tự nhánh không gây lỗi cú pháp.",
            "Sai: gặp nhánh đúng thì dừng, không kiểm tra hết elif.",
            "Sai: mỗi lần chỉ chạy một nhánh.",
        ), 1))
    r.append(_row(
        "Boolean Expression là gì?",
        ("Biểu thức chỉ cho True hoặc False", "Biểu thức cộng trừ", "Biểu thức gán", "Biểu thức có vòng lặp"),
        (
            "Đúng: biểu thức bool dùng trong if, ví dụ x > 0, a and b.",
            "Sai: cộng trừ cho số, không nhất thiết True/False.",
            "Sai: gán dùng `=`, khác biểu thức điều kiện.",
            "Sai: vòng lặp là cấu trúc khác, không định nghĩa bool expression.",
        ), 1))
    r.append(_row(
        "Dấu `:` sau if/elif/else trong Python?",
        ("Bắt buộc về cú pháp", "Tùy chọn", "Kết thúc khối", "Thay cho { }"),
        (
            "Đúng: thiếu `:` sau if/elif/else sẽ lỗi cú pháp.",
            "Sai: `:` bắt buộc, không tùy chọn.",
            "Sai: `:` mở khối lệnh; kết thúc nhờ thụt dòng.",
            "Sai: Python dùng thụt dòng, không dùng { } như C/Java.",
        ), 1))
    r.append(_row(
        "Thụt lề (indentation) trong khối if có tác dụng gì?",
        (
            "Cho Python biết lệnh thuộc nhánh nào", "Chỉ để code đẹp", "Thay dấu :", "Bắt buộc chỉ dùng Tab",
        ),
        (
            "Đúng: cùng mức thụt = cùng khối thuộc if/elif/else.",
            "Sai: thụt dòng là cú pháp, không chỉ trang trí.",
            "Sai: vẫn cần `:` sau if; thụt dòng không thay `:`.",
            "Sai: dùng space hoặc tab nhất quán, không bắt buộc chỉ Tab.",
        ), 1))
    r.append(_row(
        "Control Flow (luồng điều khiển) là gì?",
        (
            "Cách điều hướng thứ tự thực thi các dòng lệnh", "Tốc độ chương trình",
            "Số lượng biến", "Quản lý bộ nhớ",
        ),
        (
            "Đúng: if/elif/else quyết định nhánh nào được chạy.",
            "Sai: tốc độ không phải định nghĩa control flow.",
            "Sai: số biến không mô tả luồng điều khiển.",
            "Sai: quản lý bộ nhớ là chủ đề khác.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        "diem = 8\nif diem >= 5:\n    print(\"Dat\")\nelse:\n    print(\"Khong dat\")",
        ("Dat", "Khong dat", "8", "Lỗi"),
        (
            "Đúng: diem = 8 thỏa diem >= 5 nên in \"Dat\".",
            "Sai: nhánh else chỉ chạy khi điểm < 5.",
            "Sai: print in chuỗi kết quả, không in số 8.",
            "Sai: if/else hợp lệ.",
        ), 1))
    r.append(_row(
        "Python kiểm tra các nhánh elif theo thứ tự nào?",
        (
            "Từ trên xuống, dừng ở nhánh đúng đầu tiên", "Từ dưới lên", "Kiểm tra hết rồi chọn cuối", "Ngẫu nhiên",
        ),
        (
            "Đúng: elif được xét lần lượt; gặp điều kiện đúng thì dừng.",
            "Sai: Python không xét elif từ dưới lên.",
            "Sai: không cần kiểm tra hết mới chọn.",
            "Sai: thứ tự kiểm tra xác định, không ngẫu nhiên.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        'status = "OK"\nresult = "Pass" if status == "OK" else "Fail"\nprint(result)',
        ("Pass", "Fail", "OK", "Lỗi"),
        (
            "Đúng: status == \"OK\" nên biểu thức ba ngôi cho \"Pass\".",
            "Sai: điều kiện đúng nên không chọn \"Fail\".",
            "Sai: OK là giá trị status, không phải chuỗi in ra.",
            "Sai: cú pháp toán tử ba ngôi hợp lệ.",
        ), 1))

    assert len(r) == 15
    return r


def build_rows() -> list[dict[str, object]]:
    rows = _prev_rows() + _current_rows()
    assert len(rows) == 45
    apply_session_warmup_plan(rows, prev_count=30)
    return rows


def _validate(rows: list[dict[str, object]]) -> None:
    for i, r in enumerate(rows):
        q = str(r["question_content"])
        if "PLACEHOLDER" in q.upper():
            raise SystemExit(f"Câu {i + 1}: còn PLACEHOLDER")
        if _STORY_FLUFF.search(q):
            raise SystemExit(f"Câu {i + 1}: fluff — {q[:70]}")
        hit = _session_quiz_blob_has_fluff(q)
        if hit:
            raise SystemExit(f"Câu {i + 1}: fluff — {hit[0]}")
        if i < 30 and "Code:" in q:
            code = q.split("Code:", 1)[1]
            if _INTRO_FORBIDDEN_IN_CODE.search(code):
                raise SystemExit(f"Câu {i + 1} BÀI CŨ: toán tử chưa học S01")


def main() -> None:
    rows = build_rows()
    _validate(rows)
    _validate_session_quiz_block_forbidden_question_styles(
        [{"question_content": r["question_content"]} for r in rows], [],
    )
    out = ROOT / "output" / "Quizz_Session02_Dau_Gio_da_sua.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    fill_template_session_warmup_quiz(ensure_session_warmup_quiz_example_template(), out, rows)
    print(f"Đã ghi {len(rows)} câu → {out}")


if __name__ == "__main__":
    main()
