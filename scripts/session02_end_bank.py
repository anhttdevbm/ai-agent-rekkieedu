"""45 câu quiz cuối giờ Session 02 — toán tử & điều kiện (không kịch bản ship/đơn hàng)."""
from __future__ import annotations

from build_corrected_session_warmup_quiz import _code_row, _row


def build_session02_end_rows() -> list[dict[str, object]]:
    r: list[dict[str, object]] = []

    r.append(_row(
        "Toán tử `and` trả về `True` khi nào?",
        (
            "Khi tất cả các biểu thức thành phần đều đúng",
            "Khi ít nhất một biểu thức thành phần đúng",
            "Khi tất cả các biểu thức thành phần đều sai",
            "Khi biểu thức đầu tiên đúng bất kể biểu thức sau",
        ),
        (
            "Đúng: and chỉ True khi mọi thành phần đều True.",
            "Sai: đó là hành vi của or.",
            "Sai: tất cả sai thì and trả False.",
            "Sai: and yêu cầu tất cả đúng, không chỉ đầu tiên.",
        ), 1))
    r.append(_row(
        "Toán tử `or` trả về `False` chỉ khi nào?",
        (
            "Khi tất cả các biểu thức thành phần đều sai",
            "Khi ít nhất một biểu thức thành phần sai",
            "Khi biểu thức đầu tiên sai",
            "Khi tất cả các biểu thức thành phần đều đúng",
        ),
        (
            "Đúng: or chỉ False khi mọi thành phần đều False.",
            "Sai: or vẫn True nếu còn một thành phần đúng.",
            "Sai: biểu thức sau có thể đúng, or vẫn True.",
            "Sai: tất cả đúng thì or trả True.",
        ), 1))
    r.append(_row(
        "Toán tử `not` có tác dụng gì?",
        (
            "Đảo ngược giá trị logic hiện tại",
            "Kết hợp hai điều kiện lại với nhau",
            "Kiểm tra hai điều kiện có bằng nhau không",
            "Trả về True nếu ít nhất một điều kiện đúng",
        ),
        (
            "Đúng: not đảo ngược True thành False và ngược lại.",
            "Sai: đó là vai trò của and/or.",
            "Sai: so sánh bằng dùng ==.",
            "Sai: đó là hành vi của or.",
        ), 1))
    r.append(_row(
        "`ok_user = True`, `ok_pass = False`. Kết quả `ok_user and ok_pass`?",
        ("False", "True", "None", "Lỗi"),
        (
            "Đúng: and cần cả hai True; ok_pass là False.",
            "Sai: and chỉ True khi cả hai đều True.",
            "Sai: and trả bool, không trả None.",
            "Sai: biểu thức hợp lệ.",
        ), 1))
    r.append(_row(
        "Trong `if-elif-else`, Python kiểm tra các nhánh theo thứ tự nào?",
        (
            "Từ trên xuống, dừng ở nhánh đầu tiên đúng",
            "Kiểm tra tất cả rồi chọn nhánh đúng cuối cùng",
            "Ngẫu nhiên chọn một nhánh",
            "Kiểm tra else trước if",
        ),
        (
            "Đúng: duyệt từ trên xuống, dừng ở nhánh đầu thỏa.",
            "Sai: dừng ngay khi gặp nhánh đúng đầu tiên.",
            "Sai: thứ tự kiểm tra cố định.",
            "Sai: else luôn sau cùng.",
        ), 1))
    r.append(_row(
        "Đặt điều kiện rộng (vd. `x > 0`) lên đầu chuỗi if-elif thì sao?",
        (
            "Nhánh đó có thể chạy trước, bỏ qua nhánh chi tiết phía sau",
            "Python tự sắp xếp lại điều kiện",
            "Chương trình báo lỗi cú pháp",
            "Các nhánh elif vẫn luôn được kiểm tra hết",
        ),
        (
            "Đúng: nhánh đúng đầu tiên chạy, elif sau có thể không xét.",
            "Sai: Python không tự sắp xếp điều kiện.",
            "Sai: không lỗi cú pháp, chỉ logic dễ sai.",
            "Sai: gặp nhánh đúng thì dừng.",
        ), 1))
    r.append(_row(
        "Cú pháp toán tử ba ngôi (ternary) trong Python?",
        ("giá_trị_A if điều_kiện else giá_trị_B", "điều_kiện ? A : B", "if điều_kiện then A else B", "điều_kiện if A else B"),
        (
            "Đúng: `A if condition else B`.",
            "Sai: cú pháp C/JavaScript, không phải Python.",
            "Sai: Python không dùng then.",
            "Sai: thứ tự sai.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        'x = 7\nket_qua = "Lon" if x > 5 else "Be"\nprint(ket_qua)',
        ("Lon", "Be", "7", "Lỗi"),
        (
            "Đúng: x > 5 nên toán tử ba ngôi chọn \"Lon\".",
            "Sai: điều kiện đúng nên không chọn \"Be\".",
            "Sai: in chuỗi kết quả, không in 7.",
            "Sai: cú pháp toán tử ba ngôi hợp lệ.",
        ), 1))
    r.append(_row(
        "Match-case trong Python có từ phiên bản nào?",
        ("Python 3.10", "Python 3.8", "Python 3.6", "Python 2.7"),
        (
            "Đúng: match-case từ Python 3.10.",
            "Sai: 3.8 chưa có match-case.",
            "Sai: 3.6 chưa có match-case.",
            "Sai: 2.7 đã nghỉ hưu.",
        ), 1))
    r.append(_row(
        "Nested if (if lồng nhau) phù hợp khi?",
        (
            "Điều kiện con chỉ xét sau khi điều kiện cha đúng",
            "Mọi điều kiện độc lập, không liên quan",
            "Thay cho mọi phép and",
            "Chỉ để in một dòng print",
        ),
        (
            "Đúng: logic phân cấp — cha rồi mới đến con.",
            "Sai: điều kiện độc lập dùng if/elif phẳng.",
            "Sai: and bổ sung, không bị thay hoàn toàn.",
            "Sai: nested không chỉ cho print một dòng.",
        ), 1))
    r.append(_row(
        "Lồng quá nhiều tầng if trong một đoạn code thường gây vấn đề gì?",
        (
            "Code khó đọc và khó sửa khi logic thay đổi",
            "Python tự chạy nhanh hơn",
            "Bắt buộc dùng match-case",
            "Không thể dùng elif",
        ),
        (
            "Đúng: if lồng sâu dễ rối, khó bảo trì.",
            "Sai: số tầng if không làm Python nhanh hơn.",
            "Sai: không bắt buộc match-case.",
            "Sai: vẫn có thể dùng elif hoặc gộp điều kiện.",
        ), 1))
    r.append(_row(
        "Trong Python, ký hiệu so sánh bằng và phép gán lần lượt là gì?",
        ("== và =", "= và ==", "=== và =", ":= và =="),
        (
            "Đúng: == dùng để so sánh bằng, còn = dùng để gán giá trị.",
            "Sai: = là phép gán, không phải so sánh bằng.",
            "Sai: Python không dùng === để so sánh bằng.",
            "Sai: := là toán tử gán biểu thức, không phải phép gán cơ bản trong bài.",
        ), 1))
    r.append(_row(
        "Thiếu dấu `:` sau `if`/`elif`/`else` thì sao?",
        (
            "Python báo lỗi cú pháp",
            "Python tự thêm `:`",
            "Chương trình chạy nhưng bỏ qua nhánh",
            "Python chuyển sang match-case",
        ),
        (
            "Đúng: thiếu `:` là SyntaxError.",
            "Sai: Python không tự sửa cú pháp.",
            "Sai: lỗi cú pháp, không chạy được.",
            "Sai: không tự đổi cấu trúc.",
        ), 1))
    r.append(_row(
        "Khi nào nên dùng if-else thay vì toán tử ba ngôi?",
        (
            "Khi điều kiện phức tạp, if-else dễ đọc hơn",
            "Khi gán giá trị đơn giản một dòng",
            "Khi cần chạy nhanh hơn",
            "Chỉ khi dùng Python dưới 3.6",
        ),
        (
            "Đúng: phức tạp nên tách if-else cho rõ.",
            "Sai: gán đơn giản phù hợp ternary.",
            "Sai: tốc độ không khác đáng kể.",
            "Sai: ternary không phụ thuộc 3.6.",
        ), 1))
    r.append(_row(
        "Kết quả `True or False` và `False and True` lần lượt?",
        ("True và False", "False và True", "True và True", "False và False"),
        (
            "Đúng: or có True → True; and có False → False.",
            "Sai: True or False là True.",
            "Sai: False and True là False.",
            "Sai: cả hai kết quả như trên.",
        ), 1))
    r.append(_row(
        "Khối `else` trong if-elif-else có vai trò gì?",
        (
            "Xử lý mọi trường hợp còn lại",
            "Kiểm tra thêm một điều kiện cụ thể",
            "Bắt buộc phải có",
            "Chạy song song với if",
        ),
        (
            "Đúng: else khi mọi if/elif đều sai.",
            "Sai: kiểm tra điều kiện là elif.",
            "Sai: else tùy chọn.",
            "Sai: chỉ một nhánh chạy tuần tự.",
        ), 1))
    r.append(_row(
        "Match-case khác if-elif ở điểm nào?",
        (
            "Match-case khớp giá trị cụ thể; if-elif so sánh biểu thức điều kiện",
            "Match-case so sánh lớn/nhỏ; if-elif khớp giá trị",
            "Match-case luôn nhanh hơn",
            "Match-case có từ Python 2.7",
        ),
        (
            "Đúng: match đối soát pattern/giá trị; if-elif dùng điều kiện bool.",
            "Sai: ngược lại.",
            "Sai: bài không nhấn hiệu năng.",
            "Sai: match-case từ 3.10.",
        ), 1))
    r.append(_row(
        "Thụt lề (indentation) trong khối if có tác dụng gì?",
        (
            "Xác định lệnh thuộc nhánh if/elif/else nào",
            "Chỉ để code đẹp, không ảnh hưởng logic",
            "Thay cho dấu `:`",
            "Giúp Python chạy nhanh hơn",
        ),
        (
            "Đúng: indentation xác định khối lệnh.",
            "Sai: ảnh hưởng logic, không chỉ thẩm mỹ.",
            "Sai: cần cả `:` và thụt dòng.",
            "Sai: không liên quan tốc độ.",
        ), 1))
    r.append(_row(
        "Boolean Expression là gì?",
        (
            "Biểu thức cho kết quả True hoặc False",
            "Biểu thức cộng trừ số",
            "Biểu thức gán biến",
            "Biểu thức bắt buộc có and/or",
        ),
        (
            "Đúng: ví dụ x > 0, a and b.",
            "Sai: số học trả số, không bool.",
            "Sai: gán dùng =.",
            "Sai: có thể chỉ dùng so sánh >, <.",
        ), 1))
    r.append(_row(
        "Control Flow (luồng điều khiển) là gì?",
        (
            "Cách điều hướng thứ tự thực thi các dòng lệnh",
            "Tốc độ xử lý chương trình",
            "Số lượng biến trong chương trình",
            "Cơ chế nhập dữ liệu",
        ),
        (
            "Đúng: if/elif quyết định nhánh chạy.",
            "Sai: không phải định nghĩa tốc độ.",
            "Sai: không liên quan số biến.",
            "Sai: I/O khác control flow.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        "print(3 > 2 and 4 < 5)",
        ("True", "False", "3", "Lỗi"),
        (
            "Đúng: cả hai so sánh đúng nên and là True.",
            "Sai: có đủ điều kiện True.",
            "Sai: in bool, không in số 3.",
            "Sai: cú pháp hợp lệ.",
        ), 1))
    r.append(_row(
        "Toán tử `or` phù hợp khi?",
        (
            "Chỉ cần một trong các điều kiện đúng",
            "Mọi điều kiện phải đúng cùng lúc",
            "Chỉ dùng với số nguyên",
            "Đảo ngược giá trị bool",
        ),
        (
            "Đúng: or True nếu ít nhất một vế True.",
            "Sai: tất cả đúng là and.",
            "Sai: or dùng với mọi kiểu bool.",
            "Sai: đảo ngược là not.",
        ), 1))
    r.append(_row(
        "`a = True`, `b = False`. Kết quả `a or b`?",
        ("True", "False", "None", "Lỗi cú pháp"),
        (
            "Đúng: or có một vế True nên True.",
            "Sai: or chỉ False khi cả hai False.",
            "Sai: or trả bool.",
            "Sai: cú pháp hợp lệ.",
        ), 1))
    r.append(_row(
        "Khi nào nên dùng match-case thay vì if-elif?",
        (
            "Khi đối soát nhiều giá trị cụ thể (vd. mã trạng thái)",
            "Khi so sánh khoảng lớn hơn/nhỏ hơn",
            "Khi lồng nhiều tầng if phụ thuộc",
            "Khi gán giá trị một dòng đơn giản",
        ),
        (
            "Đúng: match-case cho danh sách giá trị rõ ràng.",
            "Sai: khoảng số dùng if-elif.",
            "Sai: lồng if là nested if.",
            "Sai: gán một dòng là ternary.",
        ), 1))
    r.append(_row(
        "Toán tử ba ngôi có làm chương trình chạy nhanh hơn if-else không?",
        ("Không, chủ yếu giúp viết ngắn gọn", "Có, vì một dòng", "Có, Python tối ưu riêng", "Không, và chậm hơn"),
        (
            "Đúng: syntactic sugar, không đổi tốc độ đáng kể.",
            "Sai: số dòng không quyết định tốc độ.",
            "Sai: không có tối ưu riêng như vậy.",
            "Sai: bài không nói chậm hơn.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        "print(False or True)",
        ("True", "False", "None", "Lỗi"),
        (
            "Đúng: or có một vế True nên kết quả là True.",
            "Sai: or chỉ False khi cả hai vế đều False.",
            "Sai: kết quả là bool, không phải None.",
            "Sai: cú pháp hợp lệ.",
        ), 1))
    r.append(_row(
        "Không dùng if/elif để chọn một nhánh, chỉ gán tuần tự nhiều lần thì?",
        (
            "Kết quả cuối phụ thuộc lệnh gán/in chạy sau cùng",
            "Python báo lỗi cú pháp ngay",
            "Mọi biến tự xóa",
            "Chương trình không chạy được",
        ),
        (
            "Đúng: không rẽ nhánh thì các lệnh có thể chạy hết, ghi đè kết quả.",
            "Sai: không phải lỗi cú pháp.",
            "Sai: biến không tự xóa.",
            "Sai: vẫn chạy, chỉ logic sai.",
        ), 1))
    r.append(_row(
        "Để giảm if lồng quá sâu, nên?",
        (
            "Gộp điều kiện bằng and/or thay vì lồng if quá sâu",
            "Tăng số tầng if lồng nhau",
            "Lồng nhiều toán tử ba ngôi",
            "Bỏ hết else",
        ),
        (
            "Đúng: gộp điều kiện giảm tầng lồng.",
            "Sai: tăng tầng làm tệ hơn.",
            "Sai: lồng ternary cũng khó đọc.",
            "Sai: else vẫn hữu ích.",
        ), 1))
    r.append(_row(
        "Cần cả `diem >= 0` và `diem <= 10` đồng thời, nên dùng?",
        ("and", "or", "not", "="),
        (
            "Đúng: cả hai điều kiện phải đúng → and.",
            "Sai: or chỉ cần một đúng.",
            "Sai: not đảo ngược.",
            "Sai: = là gán.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        "print(7 > 3 and 2 > 5)",
        ("False", "True", "7", "Lỗi"),
        (
            "Đúng: 7>3 đúng nhưng 2>5 sai nên and là False.",
            "Sai: cần cả hai vế đúng mới True.",
            "Sai: in bool, không in 7.",
            "Sai: cú pháp hợp lệ.",
        ), 1))
    r.append(_row(
        "`elif` khác `if` độc lập ngay sau `if` đầu ở điểm nào?",
        (
            "elif chỉ xét khi các nhánh if/elif trước đều sai",
            "elif luôn chạy dù if trước đúng",
            "elif không cần dấu `:`",
            "elif bắt buộc đi kèm else",
        ),
        (
            "Đúng: elif là nhánh tiếp theo trong cùng chuỗi.",
            "Sai: if độc lập luôn được kiểm tra.",
            "Sai: elif vẫn cần `:`.",
            "Sai: elif không bắt buộc else.",
        ), 1))
    r.append(_row(
        "Kết quả `not True`?",
        ("False", "True", "None", "0"),
        (
            "Đúng: not đảo True thành False.",
            "Sai: not đảo ngược.",
            "Sai: trả bool, không None.",
            "Sai: không trả số 0.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        "diem = 85\nif diem >= 80:\n    if diem >= 90:\n        print(\"A\")\n    else:\n        print(\"B\")\nelse:\n    print(\"C\")",
        ("B", "A", "C", "Lỗi"),
        (
            "Đúng: >=80 đúng nhưng >=90 sai nên in B.",
            "Sai: 85 chưa đủ 90.",
            "Sai: vẫn vào nhánh >=80.",
            "Sai: nested if hợp lệ.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        "diem = 70\nif diem >= 80:\n    if diem >= 90:\n        print(\"A\")\n    else:\n        print(\"B\")\nelse:\n    print(\"C\")",
        ("C", "A", "B", "Lỗi"),
        (
            "Đúng: 70 < 80 nên vào else ngoài, in C.",
            "Sai: không vào nhánh >=80.",
            "Sai: không in B.",
            "Sai: cú pháp hợp lệ.",
        ), 1))
    r.append(_row(
        "`diem = 75`. Biểu thức `ket_qua = 'Dat' if diem >= 50 else 'Chua dat'`. `ket_qua` là?",
        ("Dat", "Chua dat", "True", "50"),
        (
            "Đúng: 75 >= 50 nên chọn 'Dat'.",
            "Sai: điều kiện đúng.",
            "Sai: ternary trả chuỗi, không bool.",
            "Sai: 50 là ngưỡng, không phải kết quả.",
        ), 1))
    r.append(_row(
        "`diem = 40`. `ket_qua = 'Dat' if diem >= 50 else 'Chua dat'`. `ket_qua` là?",
        ("Chua dat", "Dat", "False", "None"),
        (
            "Đúng: 40 < 50 nên lấy nhánh else.",
            "Sai: điều kiện sai.",
            "Sai: trả chuỗi.",
            "Sai: else có giá trị.",
        ), 1))
    r.append(_row(
        "Trong match-case, nếu không case nào khớp và có `case _:` thì?",
        ("Nhánh `case _` chạy", "SyntaxError", "Chạy case đầu tiên", "Chạy elif cuối"),
        (
            "Đúng: `_` là nhánh mặc định.",
            "Sai: không phải SyntaxError.",
            "Sai: không tự chọn case đầu.",
            "Sai: elif không thuộc match.",
        ), 1))
    r.append(_row(
        "Điều nào SAI về match-case?",
        (
            "Match-case thay thế mọi phép so sánh > < >= <=",
            "Match-case khớp giá trị/pattern cụ thể",
            "Match-case có từ Python 3.10",
            "Match-case phù hợp nhiều mã cố định",
        ),
        (
            "Đúng (đây là đáp án sai): match không thay so sánh khoảng.",
            "Sai: đúng về match-case.",
            "Sai: đúng về phiên bản.",
            "Sai: đúng về use case.",
        ), 1))
    r.append(_row(
        "Lạm dụng toán tử ba ngôi với điều kiện phức tạp?",
        (
            "Khó đọc, nên dùng if-else rõ ràng hơn",
            "Luôn chạy chậm hơn if-else",
            "Không hỗ trợ chuỗi",
            "Chỉ dùng được với số nguyên",
        ),
        (
            "Đúng: toán tử ba ngôi phù hợp điều kiện ngắn, đơn giản; phức tạp nên dùng if-else.",
            "Sai: tốc độ không phải lý do chính.",
            "Sai: hỗ trợ mọi kiểu.",
            "Sai: không giới hạn int.",
        ), 1))
    r.append(_row(
        "Nested Conditionals là?",
        (
            "Đặt if bên trong khối if/elif/else khác",
            "Nhiều and trên một dòng",
            "Nhiều if độc lập không liên quan",
            "match lồng trong vòng lặp",
        ),
        (
            "Đúng: điều kiện con nằm trong điều kiện cha.",
            "Sai: and trên một dòng là logic phẳng.",
            "Sai: if liên tiếp độc lập khác nested.",
            "Sai: không định nghĩa như vậy.",
        ), 1))
    r.append(_row(
        "Khi đổi ngưỡng điều kiện ngoài cùng trong nested if, lợi ích là?",
        (
            "Chỉ sửa một chỗ ở if ngoài",
            "Phải sửa mọi dòng trong file",
            "Python tự cập nhật điều kiện con",
            "Không cần nested if nữa",
        ),
        (
            "Đúng: tập trung điều kiện cha, dễ bảo trì.",
            "Sai: nested giúp giảm sửa rải rác.",
            "Sai: Python không tự sửa.",
            "Sai: vẫn cần cấu trúc phù hợp.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        'loai = "B"\nif loai == "A":\n    print(1)\nelif loai == "B":\n    print(2)\nelse:\n    print(0)',
        ("2", "1", "0", "B"),
        (
            "Đúng: loai == B nên in 2.",
            "Sai: A không khớp.",
            "Sai: else khi không khớp.",
            "Sai: in số, không in tên biến.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        "print(10 + 5 > 12)",
        ("True", "False", "15", "Lỗi"),
        (
            "Đúng: 10+5=15, 15>12 là True.",
            "Sai: 15 > 12 đúng.",
            "Sai: in kết quả bool, không in 15.",
            "Sai: ưu tiên toán tử đúng.",
        ), 1))
    r.append(_code_row(
        "Đoạn code sau in ra gì?",
        'status = "OK"\nresult = "Pass" if status == "OK" else "Fail"\nprint(result)',
        ("Pass", "Fail", "OK", "Lỗi"),
        (
            "Đúng: status == OK nên Pass.",
            "Sai: điều kiện đúng.",
            "Sai: OK là giá trị status.",
            "Sai: ternary hợp lệ.",
        ), 1))
    r.append(_row(
        "Kết quả `not False`?",
        ("True", "False", "None", "0"),
        (
            "Đúng: not đảo False thành True.",
            "Sai: not đảo ngược giá trị logic.",
            "Sai: not trả bool, không phải None.",
            "Sai: not trả True, không phải số 0.",
        ), 1))

    assert len(r) == 45
    return r
