from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from cham_bai import __version__
from cham_bai.gdocs_reader import is_google_docs_url
from cham_bai.git_remote import normalize_github_repo_url
from cham_bai.quiz_excel import (
    ensure_default_quiz_template,
    ensure_lesson_quiz_example_template,
    ensure_session_warmup_quiz_example_template,
)
from cham_bai.model_options import IMAGE_MODEL_OPTIONS, MODEL_OPTIONS, QUIZ_KIND_OPTIONS
from cham_bai.session_warmup_plan import session_warmup_distribution_summary_vi
from cham_bai.quiz_gen import (
    QUIZ_KIND_LESSON,
    QUIZ_KIND_SESSION,
    QUIZ_KIND_SESSION_END,
    QUIZ_KIND_SESSION_WARMUP,
    QuizGenParams,
    default_quiz_output_path,
    default_session_end_quiz_output_path,
    default_session_warmup_quiz_output_path,
    normalize_quiz_kind,
    run_quiz_generation,
)
from cham_bai.reading_gen import (
    DEFAULT_LEARNING_GOALS,
    ReadingDocParams,
    default_reading_output_pair,
    reading_output_stem,
    run_reading_generation,
)
from cham_bai.workflow import (
    GradeJobParams,
    GradeJobResult,
    grade_row_label,
    has_grade_slots,
    is_valid_report_source_url,
    normalized_grade_rows,
    run_grade_batch,
)


def _make_log_panel(
    parent: ttk.Frame,
    *,
    grid_row: int,
    grid_columnspan: int = 1,
    height: int = 12,
    set_row_weight: bool = True,
) -> scrolledtext.ScrolledText:
    """
    Khung nhật ký: LabelFrame + thanh công cụ (xóa / sao chép) + vùng cuộn.
    Trả về widget ScrolledText (state=DISABLED mặc định — dùng append qua hàm riêng).
    """
    lf = ttk.LabelFrame(
        parent,
        text="Nhật ký / log — tiến trình, lỗi và kết quả",
        padding=6,
    )
    lf.grid(
        row=grid_row,
        column=0,
        columnspan=grid_columnspan,
        sticky=tk.NSEW,
        pady=(4, 8),
    )
    lf.columnconfigure(0, weight=1)
    lf.rowconfigure(1, weight=1)
    if set_row_weight:
        parent.rowconfigure(grid_row, weight=1)

    bar = ttk.Frame(lf)
    bar.grid(row=0, column=0, sticky=tk.EW)
    bar.columnconfigure(0, weight=1)

    log = scrolledtext.ScrolledText(
        lf,
        height=height,
        wrap=tk.WORD,
        state=tk.DISABLED,
        font=("Consolas", 10),
    )
    log.grid(row=1, column=0, sticky=tk.NSEW, pady=(6, 0))

    top = parent.winfo_toplevel()

    def clear_log() -> None:
        log.configure(state=tk.NORMAL)
        log.delete("1.0", tk.END)
        log.configure(state=tk.DISABLED)

    def copy_all() -> None:
        log.configure(state=tk.NORMAL)
        text = log.get("1.0", tk.END).rstrip("\n")
        log.configure(state=tk.DISABLED)
        top.clipboard_clear()
        top.clipboard_append(text)

    ttk.Button(bar, text="Xóa log", command=clear_log).grid(row=0, column=0, sticky=tk.W)
    ttk.Button(bar, text="Sao chép tất cả", command=copy_all).grid(
        row=0, column=1, sticky=tk.W, padx=(8, 0)
    )
    ttk.Label(
        bar,
        text="Cuộn xem toàn bộ — dùng «Sao chép tất cả» để lấy log vào clipboard.",
        foreground="#555",
    ).grid(row=0, column=2, sticky=tk.E, padx=(16, 0))
    bar.columnconfigure(2, weight=1)

    return log


def _build_grade_tab(main: ttk.Frame, root: tk.Tk) -> None:
    row = 0

    ttk.Label(main, text="Đề bài (.docx hoặc Google Docs)").grid(
        row=row, column=0, sticky=tk.W, pady=2
    )
    assignment_var = tk.StringVar()
    ttk.Entry(main, textvariable=assignment_var, width=70).grid(
        row=row, column=1, sticky=tk.EW, padx=(8, 4), pady=2
    )

    def browse_docx() -> None:
        p = filedialog.askopenfilename(
            title="Chọn file đề DOCX",
            filetypes=[("Word", "*.docx"), ("Tất cả", "*.*")],
        )
        if p:
            assignment_var.set(p)

    ttk.Button(main, text="Chọn…", command=browse_docx).grid(row=row, column=2, pady=2)
    row += 1

    ttk.Label(main, text="Bài nộp (mỗi dòng một bài)").grid(
        row=row, column=0, sticky=tk.NW, pady=2
    )
    sub_box_fr = ttk.Frame(main)
    sub_box_fr.grid(row=row, column=1, columnspan=2, sticky=tk.NSEW, padx=(8, 0), pady=2)
    subs_text = scrolledtext.ScrolledText(sub_box_fr, height=6, width=70, wrap=tk.WORD)
    subs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def browse_sub() -> None:
        p = filedialog.askdirectory(title="Chọn thư mục mã học viên")
        if p:
            subs_text.insert(tk.END, p.strip() + "\n")

    ttk.Button(sub_box_fr, text="Thêm thư mục…", command=browse_sub).pack(
        side=tk.RIGHT, anchor=tk.N, padx=(4, 0)
    )
    row += 1

    ttk.Label(main, text="Báo cáo + mini (tuỳ chọn — GitHub hoặc Google Docs, mỗi dòng một link)").grid(
        row=row, column=0, sticky=tk.NW, pady=2
    )
    report_box_fr = ttk.Frame(main)
    report_box_fr.grid(row=row, column=1, columnspan=2, sticky=tk.NSEW, padx=(8, 0), pady=2)
    report_repos_box = scrolledtext.ScrolledText(report_box_fr, height=4, width=70, wrap=tk.NONE)
    report_repos_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    row += 1

    hint_lf = ttk.LabelFrame(main, text="Cách chấm (tab này)", padding=6)
    hint_lf.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=(2, 6))
    hint_lf.columnconfigure(0, weight=1)
    ttk.Label(
        hint_lf,
        text=(
            "Dòng i repo báo cáo khớp dòng i «Bài nộp» (cả hai đều có thể để trống từng dòng: chỉ bài nộp, chỉ repo, hoặc cả hai). "
            "Có thể chỉ điền repo mà không điền bài nộp cho dòng đó — chỉ chấm báo cáo. Điểm/nhận xét: BT đầu giờ + báo cáo (ưu tiên BT). Mini project: Có/Không/Không rõ."
        ),
        wraplength=720,
        justify=tk.LEFT,
    ).grid(row=0, column=0, sticky=tk.W)
    row += 1

    ttk.Label(main, text="Model OpenRouter").grid(row=row, column=0, sticky=tk.W, pady=2)
    model_var = tk.StringVar(value=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6"))
    ttk.Combobox(
        main,
        textvariable=model_var,
        width=67,
        values=MODEL_OPTIONS,
    ).grid(row=row, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0), pady=2)
    row += 1

    opt_fr = ttk.LabelFrame(main, text="Tùy chọn", padding=8)
    opt_fr.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=10)
    opt_fr.columnconfigure(1, weight=1)

    use_tpl_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(opt_fr, text="Clone template GitHub từ link trong đề", variable=use_tpl_var).grid(
        row=0, column=0, columnspan=2, sticky=tk.W
    )

    strict_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(
        opt_fr,
        text="Trừ 0 điểm + “dùng AI” khi likely_ai (ngưỡng bên dưới)",
        variable=strict_var,
    ).grid(row=1, column=0, columnspan=2, sticky=tk.W)

    ttk.Label(opt_fr, text="Ngưỡng tin cậy AI (0–100)").grid(row=2, column=0, sticky=tk.W, pady=(6, 0))
    conf_var = tk.IntVar(value=75)
    ttk.Spinbox(opt_fr, from_=0, to=100, textvariable=conf_var, width=8).grid(
        row=2, column=1, sticky=tk.W, pady=(6, 0)
    )
    row += 1

    log = _make_log_panel(main, grid_row=row, grid_columnspan=3, height=14)
    main.columnconfigure(1, weight=1)
    row += 1

    btn_fr = ttk.Frame(main)
    btn_fr.grid(row=row, column=0, columnspan=3, sticky=tk.EW)
    run_btn = ttk.Button(btn_fr, text="Chạy chấm bài")
    run_btn.pack(side=tk.LEFT)

    def append_log(msg: str) -> None:
        log.configure(state=tk.NORMAL)
        log.insert(tk.END, msg.rstrip() + "\n")
        log.see(tk.END)
        log.configure(state=tk.DISABLED)

    def set_busy(v: bool) -> None:
        run_btn.configure(state=tk.DISABLED if v else tk.NORMAL)

    def _append_single_result(sub_label: str, res: GradeJobResult) -> None:
        append_log(f"——— {sub_label} ———")
        for w in res.warnings:
            append_log(f"[Cảnh báo] {w}")
        if not res.ok:
            append_log(f"[Lỗi] {res.error_message}")
            return
        append_log("[Xong]")
        if res.json_text:
            try:
                blob = json.loads(res.json_text)
                fs = blob.get("final_score")
                fc = blob.get("final_comment")
                mp = blob.get("mini_project_present")
                append_log(f"Điểm: {fs}")
                append_log(f"Nhận xét: {fc}")
                if mp is not None:
                    append_log(f"Mini project (chỉ có/không): {mp}")
            except Exception as e:
                append_log(f"[Lỗi hiển thị kết quả] {e}")

    def on_grade_batch_done(batch: list[tuple[str, GradeJobResult]]) -> None:
        set_busy(False)
        if not batch:
            return
        ok_n = 0
        for sub, res in batch:
            _append_single_result(sub, res)
            if res.ok:
                ok_n += 1
        if len(batch) == 1 and not batch[0][1].ok:
            messagebox.showerror("Lỗi", batch[0][1].error_message or "Chấm bài thất bại.")
        elif len(batch) == 1:
            messagebox.showinfo("Xong", "Chấm bài hoàn tất. Xem điểm và nhận xét ở khung log bên dưới.")
        else:
            bad = len(batch) - ok_n
            messagebox.showinfo(
                "Xong",
                f"Đã chấm {len(batch)} dòng: thành công {ok_n}, lỗi {bad}.",
            )

    def run_job() -> None:
        d = assignment_var.get().strip()
        subs_lines = [
            (ln.rstrip("\r") or "").strip()
            for ln in subs_text.get("1.0", tk.END).splitlines()
        ]

        if not d:
            messagebox.showwarning(
                "Thiếu đề",
                "Chọn file .docx hoặc dán link Google Docs (định dạng docs.google.com/document/...).",
            )
            return
        p = Path(d)
        ok_docx = p.is_file() and p.suffix.lower() == ".docx"
        ok_gdoc = is_google_docs_url(d)
        if not ok_docx and not ok_gdoc:
            messagebox.showwarning(
                "Đề không hợp lệ",
                "Cần file .docx tồn tại trên máy hoặc URL Google Docs đầy đủ.",
            )
            return

        report_raw = report_repos_box.get("1.0", tk.END)
        if not has_grade_slots(subs_lines, report_raw):
            messagebox.showwarning(
                "Thiếu dữ liệu chấm",
                "Cần ít nhất một dòng có bài nộp (thư mục/GitHub) hoặc link repo báo cáo (hai ô khớp từng dòng).",
            )
            return
        for s in subs_lines:
            if not s:
                continue
            if not normalize_github_repo_url(s) and not Path(s).is_dir():
                messagebox.showwarning(
                    "Bài nộp không hợp lệ",
                    f"Dòng không hợp lệ (cần thư mục tồn tại hoặc link GitHub):\n{s[:120]}",
                )
                return

        report_lines = report_raw.splitlines()
        for ru in report_lines:
            u = ru.strip()
            if u and not is_valid_report_source_url(u):
                messagebox.showwarning(
                    "Báo cáo không hợp lệ",
                    f"Mỗi dòng phải trống hoặc là link GitHub / Google Docs:\n{u[:120]}",
                )
                return

        try:
            from cham_bai.settings import api_key as _need_key

            _need_key()
        except RuntimeError as e:
            messagebox.showwarning("Thiếu API key", str(e))
            return

        norm_subs, _, _ = normalized_grade_rows(subs_lines, report_raw)
        sn = len(norm_subs)
        append_log(f"Đang chấm {sn} dòng (cùng đề, có thể mất vài phút mỗi dòng)…")
        set_busy(True)

        params = GradeJobParams(
            assignment_ref=d,
            submission_ref=norm_subs[0] if norm_subs else "",
            out_path=None,
            model=model_var.get().strip(),
            no_template=not use_tpl_var.get(),
            strict_ai=strict_var.get(),
            ai_confidence=int(conf_var.get()),
            debug=False,
            report_repos_text=report_raw,
        )

        def worker() -> None:
            try:
                batch = run_grade_batch(d, subs_lines, params)
                root.after(0, lambda b=batch: on_grade_batch_done(b))
            except Exception as e:
                ns, nr, _ = normalized_grade_rows(subs_lines, report_raw)
                err_lab = grade_row_label(ns[0] if ns else "", nr[0] if nr else "", 0)
                root.after(
                    0,
                    lambda lab=err_lab, err=str(e): on_grade_batch_done(
                        [(lab, GradeJobResult(ok=False, error_message=err))],
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    run_btn.configure(command=run_job)

    ttk.Label(
        btn_fr,
        text="Google Docs: chia sẻ link xem. Key: nhúng khi build EXE.",
        foreground="#444",
    ).pack(side=tk.RIGHT)


def _build_quiz_tab(main: ttk.Frame, root: tk.Tk) -> None:
    row = 0

    q_kind_var = tk.StringVar(value=QUIZ_KIND_OPTIONS[0][0])
    ttk.Label(main, text="Loại quizz").grid(row=row, column=0, sticky=tk.W, pady=2)
    q_kind_cb = ttk.Combobox(
        main,
        textvariable=q_kind_var,
        width=58,
        values=[lbl for lbl, _ in QUIZ_KIND_OPTIONS],
        state="readonly",
    )
    q_kind_cb.grid(row=row, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0), pady=2)
    row += 1

    subject_q_var = tk.StringVar()
    ttk.Label(main, text="Môn học (tuỳ chọn, khuyến nghị)").grid(row=row, column=0, sticky=tk.W, pady=2)
    ttk.Entry(main, textvariable=subject_q_var, width=62).grid(
        row=row, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0), pady=2
    )
    row += 1

    tpl_var = tk.StringVar()
    n_var = tk.IntVar(value=5)

    def sync_quiz_template_to_kind(*_args: object) -> None:
        """Đổi mẫu theo loại quiz."""
        lbl = q_kind_var.get().strip()
        kind_map = dict(QUIZ_KIND_OPTIONS)
        qk = normalize_quiz_kind(kind_map.get(lbl, QUIZ_KIND_SESSION))
        if qk == QUIZ_KIND_LESSON:
            tpl_var.set(str(ensure_lesson_quiz_example_template()))
        elif qk in (QUIZ_KIND_SESSION_WARMUP, QUIZ_KIND_SESSION_END):
            tpl_var.set(str(ensure_session_warmup_quiz_example_template()))
        else:
            tpl_var.set(str(ensure_default_quiz_template()))
        if qk in (QUIZ_KIND_SESSION_WARMUP, QUIZ_KIND_SESSION_END):
            n_var.set(45)
        else:
            n_var.set(5)

    sync_quiz_template_to_kind()

    quiz_n_questions_row = row
    n_q_lbl = ttk.Label(main, text="Số câu hỏi")
    n_q_spin = ttk.Spinbox(main, from_=1, to=50, textvariable=n_var, width=8)
    tpl_hint_lbl = ttk.Label(
        main,
        text="(Mẫu theo loại quiz: lesson → example/quizz-lession-example.xlsx; session → quiz_mau; session đầu giờ → example/Quizz_Session_Dau_Gio_Example.xlsx — luôn 45 câu, không chỉnh số câu. Các loại khác: mẫu 1 hàng/câu thì dùng ô Số câu.)",
        wraplength=520,
        foreground="#444",
    )

    def _sync_quiz_num_questions_row(*_args: object) -> None:
        lbl = q_kind_var.get().strip()
        kind_map = dict(QUIZ_KIND_OPTIONS)
        qk = normalize_quiz_kind(kind_map.get(lbl, QUIZ_KIND_SESSION))
        if qk in (QUIZ_KIND_SESSION_WARMUP, QUIZ_KIND_SESSION_END):
            n_q_lbl.grid_remove()
            n_q_spin.grid_remove()
            n_var.set(45)
            tpl_hint_lbl.grid(
                row=quiz_n_questions_row,
                column=0,
                columnspan=3,
                sticky=tk.W,
                padx=(0, 8),
                pady=2,
            )
        else:
            tpl_hint_lbl.grid_remove()
            n_q_lbl.grid(row=quiz_n_questions_row, column=0, sticky=tk.NW, pady=2)
            n_q_spin.grid(row=quiz_n_questions_row, column=1, sticky=tk.W, padx=(8, 0), pady=2)
            tpl_hint_lbl.grid(
                row=quiz_n_questions_row,
                column=2,
                sticky=tk.W,
                padx=(8, 0),
                pady=2,
            )

    n_q_lbl.grid(row=quiz_n_questions_row, column=0, sticky=tk.NW, pady=2)
    n_q_spin.grid(row=quiz_n_questions_row, column=1, sticky=tk.W, padx=(8, 0), pady=2)
    tpl_hint_lbl.grid(row=quiz_n_questions_row, column=2, sticky=tk.W, padx=(8, 0), pady=2)
    _sync_quiz_num_questions_row()
    row += 1

    ttk.Label(main, text="Excel mẫu (tuỳ chọn)").grid(row=row, column=0, sticky=tk.W, pady=2)
    ttk.Entry(main, textvariable=tpl_var, width=62).grid(
        row=row, column=1, sticky=tk.EW, padx=(8, 4), pady=2
    )

    def browse_tpl() -> None:
        p = filedialog.askopenfilename(
            title="Chọn file Excel mẫu",
            filetypes=[("Excel", "*.xlsx"), ("Tất cả", "*.*")],
        )
        if p:
            tpl_var.set(p)

    def use_default_tpl() -> None:
        lbl = q_kind_var.get().strip()
        kind_map = dict(QUIZ_KIND_OPTIONS)
        qk = normalize_quiz_kind(kind_map.get(lbl, QUIZ_KIND_SESSION))
        if qk == QUIZ_KIND_LESSON:
            p = ensure_lesson_quiz_example_template()
        elif qk in (QUIZ_KIND_SESSION_WARMUP, QUIZ_KIND_SESSION_END):
            p = ensure_session_warmup_quiz_example_template()
        else:
            p = ensure_default_quiz_template()
        tpl_var.set(str(p))
        if qk in (QUIZ_KIND_SESSION_WARMUP, QUIZ_KIND_SESSION_END):
            n_var.set(45)
        else:
            n_var.set(5)
        _sync_quiz_num_questions_row()
        messagebox.showinfo("Mẫu", f"Đã tạo / dùng file mẫu:\n{p}")

    ttk.Button(main, text="Chọn…", command=browse_tpl).grid(row=row, column=2, pady=2)
    row += 1

    ttk.Button(main, text="Tạo / mở mẫu mặc định (theo loại quiz)", command=use_default_tpl).grid(
        row=row, column=1, sticky=tk.W, padx=(8, 0), pady=2
    )
    row += 1

    docx_var = tk.StringVar()
    ttk.Label(main, text="DOCX bài giảng (tuỳ chọn)").grid(row=row, column=0, sticky=tk.W, pady=2)
    ttk.Entry(main, textvariable=docx_var, width=62).grid(
        row=row, column=1, sticky=tk.EW, padx=(8, 4), pady=2
    )

    def browse_lecture() -> None:
        p = filedialog.askopenfilename(
            title="Chọn DOCX bài giảng",
            filetypes=[("Word", "*.docx"), ("Tất cả", "*.*")],
        )
        if p:
            docx_var.set(p)

    ttk.Button(main, text="Chọn…", command=browse_lecture).grid(row=row, column=2, pady=2)
    row += 1

    lesson_var = tk.StringVar()
    session_var = tk.StringVar()
    session_prev_var = tk.StringVar()
    session_curr_var = tk.StringVar()

    lesson_lbl = ttk.Label(main, text="Tên lesson (bắt buộc)")
    lesson_ent = ttk.Entry(main, textvariable=lesson_var, width=62)
    session_lbl = ttk.Label(main, text="Tên session (bắt buộc)")
    session_ent = ttk.Entry(main, textvariable=session_var, width=62)

    prev_lbl = ttk.Label(main, text="Session trước (tuỳ chọn)")
    prev_ent = ttk.Entry(main, textvariable=session_prev_var, width=62)
    curr_lbl = ttk.Label(main, text="Session hiện tại (bắt buộc)")
    curr_ent = ttk.Entry(main, textvariable=session_curr_var, width=62)

    warmup_plan_lbl = ttk.Label(
        main,
        text=session_warmup_distribution_summary_vi(),
        wraplength=640,
        foreground="#1d4ed8",
    )

    def _toggle_quiz_fields() -> None:
        lbl = q_kind_var.get().strip()
        kind_map = dict(QUIZ_KIND_OPTIONS)
        qk = normalize_quiz_kind(kind_map.get(lbl, QUIZ_KIND_SESSION))
        if qk == QUIZ_KIND_SESSION_WARMUP:
            lesson_lbl.grid_remove()
            lesson_ent.grid_remove()
            session_lbl.grid_remove()
            session_ent.grid_remove()

            prev_lbl.grid(row=row, column=0, sticky=tk.W, pady=2)
            prev_ent.grid(row=row, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0), pady=2)
            curr_lbl.grid(row=row + 1, column=0, sticky=tk.W, pady=2)
            curr_ent.grid(row=row + 1, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0), pady=2)
            warmup_plan_lbl.grid(row=row + 2, column=0, columnspan=3, sticky=tk.W, padx=(0, 8), pady=(4, 8))
        elif qk == QUIZ_KIND_SESSION_END:
            lesson_lbl.grid_remove()
            lesson_ent.grid_remove()
            session_lbl.grid_remove()
            session_ent.grid_remove()

            prev_lbl.grid_remove()
            prev_ent.grid_remove()
            curr_lbl.grid(row=row, column=0, sticky=tk.W, pady=2)
            curr_ent.grid(row=row, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0), pady=2)
            warmup_plan_lbl.grid_remove()
        else:
            prev_lbl.grid_remove()
            prev_ent.grid_remove()
            curr_lbl.grid_remove()
            curr_ent.grid_remove()
            warmup_plan_lbl.grid_remove()

            lesson_lbl.grid(row=row, column=0, sticky=tk.W, pady=2)
            lesson_ent.grid(row=row, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0), pady=2)
            session_lbl.grid(row=row + 1, column=0, sticky=tk.W, pady=2)
            session_ent.grid(row=row + 1, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0), pady=2)

    _toggle_quiz_fields()
    q_kind_cb.bind(
        "<<ComboboxSelected>>",
        lambda _e: (_toggle_quiz_fields(), sync_quiz_template_to_kind(), _sync_quiz_num_questions_row()),
    )
    row += 2

    q_model = tk.StringVar(value=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6"))
    ttk.Label(main, text="Model OpenRouter").grid(row=row, column=0, sticky=tk.W, pady=2)
    ttk.Combobox(main, textvariable=q_model, width=60, values=MODEL_OPTIONS).grid(
        row=row, column=1, columnspan=2, sticky=tk.EW, padx=(8, 0), pady=2
    )
    row += 1

    qlog = _make_log_panel(main, grid_row=row, grid_columnspan=3, height=12)
    main.columnconfigure(1, weight=1)
    row += 1

    qbtn_fr = ttk.Frame(main)
    qbtn_fr.grid(row=row, column=0, columnspan=3, sticky=tk.EW)
    gen_btn = ttk.Button(qbtn_fr, text="Tạo quiz (tự lưu cạnh file mẫu)")
    gen_btn.pack(side=tk.LEFT)
    save_as_btn = ttk.Button(qbtn_fr, text="Tạo và chọn nơi lưu…", command=lambda: run_quiz(True))
    save_as_btn.pack(side=tk.LEFT, padx=(8, 0))
    row += 1
    ttk.Label(
        main,
        text=(
            "Mặc định lưu cạnh Excel mẫu: session đầu giờ → quizz_session_Dau_gio_<session hiện tại>_<ngày-giờ>.xlsx; "
            "các loại khác → quiz_<lesson>_<session>_<ngày-giờ>.xlsx."
        ),
        wraplength=640,
        foreground="#444",
    ).grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 6))

    def q_append(msg: str) -> None:
        qlog.configure(state=tk.NORMAL)
        qlog.insert(tk.END, msg.rstrip() + "\n")
        qlog.see(tk.END)
        qlog.configure(state=tk.DISABLED)

    def q_busy(v: bool) -> None:
        st = tk.DISABLED if v else tk.NORMAL
        ro = "disabled" if v else "readonly"
        gen_btn.configure(state=st)
        save_as_btn.configure(state=st)
        q_kind_cb.configure(state=ro)

    def run_quiz(pick_save: bool = False) -> None:
        kind_lbl = q_kind_var.get().strip()
        kind_map = dict(QUIZ_KIND_OPTIONS)
        qkind = normalize_quiz_kind(kind_map.get(kind_lbl, QUIZ_KIND_SESSION))

        template_path_str = tpl_var.get().strip()
        if template_path_str and Path(template_path_str).is_file():
            template_path = Path(template_path_str)
        else:
            if qkind == QUIZ_KIND_LESSON:
                template_path = ensure_lesson_quiz_example_template()
            elif qkind == QUIZ_KIND_SESSION_WARMUP:
                template_path = ensure_session_warmup_quiz_example_template()
            else:
                template_path = ensure_default_quiz_template()
            tpl_var.set(str(template_path))

        lesson = lesson_var.get().strip()
        session = session_var.get().strip()
        session_prev = session_prev_var.get().strip()
        session_curr = session_curr_var.get().strip()
        if qkind in (QUIZ_KIND_SESSION_WARMUP, QUIZ_KIND_SESSION_END):
            if not subject_q_var.get().strip() or not session_curr:
                messagebox.showwarning("Thiếu thông tin", "Điền Môn học và Session hiện tại.")
                return
            # reuse lesson/session fields for filename only
            lesson = subject_q_var.get().strip()
            session = session_curr
        else:
            if not lesson or not session:
                messagebox.showwarning("Thiếu thông tin", "Điền tên lesson và session.")
                return
        docx_p = docx_var.get().strip()
        docx_path = Path(docx_p) if docx_p else None
        if docx_path and not docx_path.is_file():
            messagebox.showwarning("DOCX", f"Không tìm thấy file: {docx_path}")
            return

        try:
            from cham_bai.settings import api_key as _need_key

            _need_key()
        except RuntimeError as e:
            messagebox.showwarning("Thiếu API key", str(e))
            return

        if pick_save:
            suggested = (
                default_session_warmup_quiz_output_path(template_path, session_curr).name
                if qkind == QUIZ_KIND_SESSION_WARMUP
                else (
                    default_session_end_quiz_output_path(template_path, session_curr).name
                    if qkind == QUIZ_KIND_SESSION_END
                    else default_quiz_output_path(template_path, lesson, session).name
                )
            )
            out = filedialog.asksaveasfilename(
                title="Lưu file quiz Excel",
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")],
                initialfile=suggested,
            )
            if not out:
                return
            out_path = Path(out)
        else:
            out_path = (
                default_session_warmup_quiz_output_path(template_path, session_curr)
                if qkind == QUIZ_KIND_SESSION_WARMUP
                else (
                    default_session_end_quiz_output_path(template_path, session_curr)
                    if qkind == QUIZ_KIND_SESSION_END
                    else default_quiz_output_path(template_path, lesson, session)
                )
            )

        q_append(f"[File ra] {out_path}")

        params = QuizGenParams(
            template_xlsx=template_path,
            docx_path=docx_path,
            lesson=lesson,
            session=session,
            session_prev=session_prev,
            session_current=session_curr,
            num_questions=int(n_var.get()),
            model=q_model.get().strip(),
            output_xlsx=out_path,
            subject=subject_q_var.get().strip(),
            quiz_kind=qkind,
        )

        q_append("Đang gọi AI soạn quiz (có thể 1–3 phút)…")
        q_busy(True)

        def worker() -> None:
            try:
                ok, msg = run_quiz_generation(params)
            except Exception as e:
                ok, msg = False, str(e)

            def finish() -> None:
                q_busy(False)
                if ok:
                    q_append(f"[Xong] Đã lưu: {msg}")
                    messagebox.showinfo("Quiz", f"Đã tạo file:\n{msg}")
                else:
                    q_append(f"[Lỗi] {msg}")
                    messagebox.showerror("Lỗi", msg)

            root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    gen_btn.configure(command=run_quiz)


def _build_reading_tab(main: ttk.Frame, root: tk.Tk) -> None:
    main.columnconfigure(0, weight=1)

    lf = ttk.LabelFrame(main, text="Khung bài đọc — Storytelling in Tech", padding=8)
    lf.grid(row=0, column=0, sticky=tk.EW)
    lf.columnconfigure(1, weight=1)

    r = 0
    subject_var = tk.StringVar()
    ttk.Label(lf, text="Môn").grid(row=r, column=0, sticky=tk.W, pady=2)
    subj_e = ttk.Entry(lf, textvariable=subject_var, width=62)
    subj_e.grid(row=r, column=1, sticky=tk.EW, padx=(6, 0), pady=2)
    r += 1

    session_rd_var = tk.StringVar()
    session_stt_var = tk.StringVar(value="1")
    ttk.Label(lf, text="Session (tên / mô tả)").grid(row=r, column=0, sticky=tk.W, pady=2)
    sess_row = ttk.Frame(lf)
    sess_row.grid(row=r, column=1, sticky=tk.EW, padx=(6, 0), pady=2)
    sess_row.columnconfigure(0, weight=1)
    sess_rd_e = ttk.Entry(sess_row, textvariable=session_rd_var)
    sess_rd_e.grid(row=0, column=0, sticky=tk.EW)
    ttk.Label(sess_row, text="Số thứ tự Session:").grid(row=0, column=1, padx=(8, 2))
    sess_stt_sb = ttk.Spinbox(sess_row, from_=1, to=99, width=5, textvariable=session_stt_var)
    sess_stt_sb.grid(row=0, column=2, sticky=tk.W)
    r += 1

    lesson_var = tk.StringVar()
    lesson_stt_var = tk.StringVar(value="1")
    ttk.Label(lf, text="Lesson (chủ đề bài đọc)").grid(row=r, column=0, sticky=tk.W, pady=2)
    les_row = ttk.Frame(lf)
    les_row.grid(row=r, column=1, sticky=tk.EW, padx=(6, 0), pady=2)
    les_row.columnconfigure(0, weight=1)
    lesson_e = ttk.Entry(les_row, textvariable=lesson_var)
    lesson_e.grid(row=0, column=0, sticky=tk.EW)
    ttk.Label(les_row, text="Số thứ tự Lesson:").grid(row=0, column=1, padx=(8, 2))
    les_stt_sb = ttk.Spinbox(les_row, from_=1, to=99, width=5, textvariable=lesson_stt_var)
    les_stt_sb.grid(row=0, column=2, sticky=tk.W)
    r += 1

    video_var = tk.StringVar()
    ttk.Label(lf, text="Video tham khảo (tuỳ chọn, YouTube)").grid(row=r, column=0, sticky=tk.NW, pady=2)
    video_e = ttk.Entry(lf, textvariable=video_var, width=62)
    video_e.grid(row=r, column=1, sticky=tk.EW, padx=(6, 0), pady=2)
    r += 1
    ttk.Label(
        lf,
        text="Nếu có link: tool lấy phụ đề (không “xem” hình). Video cần bật phụ đề việt hoặc anh — bắt buộc để AI dùng nguồn này.",
        wraplength=620,
        foreground="#444",
    ).grid(row=r, column=1, sticky=tk.W, padx=(6, 0), pady=(0, 4))
    r += 1

    tech_var = tk.StringVar()
    ttk.Label(lf, text="Ngôn ngữ / công nghệ (tuỳ chọn)").grid(row=r, column=0, sticky=tk.W, pady=2)
    tech_e = ttk.Entry(lf, textvariable=tech_var, width=62)
    tech_e.grid(row=r, column=1, sticky=tk.EW, padx=(6, 0), pady=2)
    r += 1

    audience_var = tk.StringVar(value="Sinh viên năm 1, mới học lập trình")
    ttk.Label(lf, text="Đối tượng (tuỳ chọn)").grid(row=r, column=0, sticky=tk.W, pady=2)
    audience_e = ttk.Entry(lf, textvariable=audience_var, width=62)
    audience_e.grid(row=r, column=1, sticky=tk.EW, padx=(6, 0), pady=2)
    r += 1

    ttk.Label(lf, text="Mục tiêu sau bài đọc").grid(row=r, column=0, sticky=tk.NW, pady=2)
    goals_tx = scrolledtext.ScrolledText(lf, height=5, wrap=tk.WORD)
    goals_tx.grid(row=r, column=1, sticky=tk.EW, padx=(6, 0), pady=2)
    goals_tx.insert("1.0", DEFAULT_LEARNING_GOALS)
    r += 1

    ttk.Label(lf, text="Gợi ý tài liệu tham khảo (trên Word là mục VII, tuỳ chọn)").grid(
        row=r, column=0, sticky=tk.NW, pady=2
    )
    refs_tx = scrolledtext.ScrolledText(lf, height=3, wrap=tk.WORD)
    refs_tx.grid(row=r, column=1, sticky=tk.EW, padx=(6, 0), pady=2)
    r += 1

    r_text_model = tk.StringVar(value=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6"))
    ttk.Label(lf, text="Model nội dung bài đọc").grid(row=r, column=0, sticky=tk.W, pady=2)
    r_txt_cb = ttk.Combobox(
        lf, textvariable=r_text_model, width=58, values=MODEL_OPTIONS
    )
    r_txt_cb.grid(row=r, column=1, sticky=tk.EW, padx=(6, 0), pady=2)
    r += 1

    r_image_model = tk.StringVar(value=IMAGE_MODEL_OPTIONS[0])
    ttk.Label(lf, text="Model ảnh minh họa").grid(row=r, column=0, sticky=tk.W, pady=2)
    r_img_cb = ttk.Combobox(
        lf, textvariable=r_image_model, width=58, values=IMAGE_MODEL_OPTIONS
    )
    r_img_cb.grid(row=r, column=1, sticky=tk.EW, padx=(6, 0), pady=2)
    r += 1

    gen_img_var = tk.BooleanVar(value=True)
    chk_img = ttk.Checkbutton(
        lf,
        text="Tạo 3 ảnh (mục I, II, III — trên hình không chữ Việt hoặc nhãn Anh cực ngắn; code chỉ trong văn bản)",
        variable=gen_img_var,
    )
    chk_img.grid(row=r, column=0, columnspan=2, sticky=tk.W, pady=(4, 2))
    r += 1

    rlog = _make_log_panel(main, grid_row=1, grid_columnspan=1, height=11)

    btn_fr = ttk.Frame(main)
    btn_fr.grid(row=2, column=0, sticky=tk.EW)
    go_btn = ttk.Button(btn_fr, text="Tạo bài đọc → DOCX + Excel (chọn nơi lưu)")
    go_def_btn = ttk.Button(btn_fr, text="Lưu mặc định (thư mục hiện tại)")
    go_btn.pack(side=tk.LEFT)
    go_def_btn.pack(side=tk.LEFT, padx=(8, 0))

    ttk.Label(
        main,
        text="Đầu ra: DOCX I…VI rồi VII (tài liệu). Excel: 2 cột questionName | answerName (3 hàng). Tên: «Môn - Session x - Lesson y». pip install youtube-transcript-api.",
        wraplength=820,
        foreground="#444",
    ).grid(row=3, column=0, sticky=tk.W, pady=(0, 4))

    def r_append(msg: str) -> None:
        rlog.configure(state=tk.NORMAL)
        rlog.insert(tk.END, msg.rstrip() + "\n")
        rlog.see(tk.END)
        rlog.configure(state=tk.DISABLED)

    def r_busy(v: bool) -> None:
        st = tk.DISABLED if v else tk.NORMAL
        go_btn.configure(state=st)
        go_def_btn.configure(state=st)
        r_img_cb.configure(state="disabled" if v else "normal")
        r_txt_cb.configure(state="disabled" if v else "normal")
        chk_img.configure(state=st)
        goals_tx.configure(state=st)
        refs_tx.configure(state=st)
        subj_e.configure(state=st)
        sess_rd_e.configure(state=st)
        sess_stt_sb.configure(state=st)
        lesson_e.configure(state=st)
        les_stt_sb.configure(state=st)
        video_e.configure(state=st)
        tech_e.configure(state=st)
        audience_e.configure(state=st)

    def run_reading(use_save_dialog: bool) -> None:
        subject = subject_var.get().strip()
        session = session_rd_var.get().strip()
        lesson = lesson_var.get().strip()
        video_url_input = video_var.get().strip()
        if not subject:
            messagebox.showwarning("Thiếu thông tin", "Điền tên môn.")
            return
        if not session:
            messagebox.showwarning("Thiếu thông tin", "Điền session.")
            return
        if not lesson:
            messagebox.showwarning("Thiếu thông tin", "Điền lesson.")
            return

        try:
            from cham_bai.settings import api_key as _need_key

            _need_key()
        except RuntimeError as e:
            messagebox.showwarning("Thiếu API key", str(e))
            return

        session_stt = session_stt_var.get().strip() or "1"
        lesson_stt = lesson_stt_var.get().strip() or "1"
        stem = reading_output_stem(subject, session_stt, lesson_stt)
        if use_save_dialog:
            out = filedialog.asksaveasfilename(
                title="Lưu bài đọc (DOCX — cùng thư mục sẽ có thêm .xlsx)",
                initialfile=f"{stem}.docx",
                defaultextension=".docx",
                filetypes=[("Word", "*.docx")],
            )
            if not out:
                return
            out_docx = Path(out)
            out_xlsx = out_docx.with_suffix(".xlsx")
        else:
            out_docx, out_xlsx = default_reading_output_pair(stem)

        r_append(f"[File DOCX] {out_docx}\n[File Excel] {out_xlsx}")

        params = ReadingDocParams(
            subject=subject,
            session=session,
            lesson=lesson,
            session_stt=session_stt,
            lesson_stt=lesson_stt,
            video_url=video_url_input or None,
            technology=tech_var.get().strip(),
            audience=audience_var.get().strip(),
            learning_goals=goals_tx.get("1.0", tk.END).strip(),
            references_hint=refs_tx.get("1.0", tk.END).strip(),
            text_model=r_text_model.get().strip(),
            image_model=r_image_model.get().strip(),
            generate_illustrations=bool(gen_img_var.get()),
            output_docx=out_docx,
            output_xlsx=out_xlsx,
        )

        r_busy(True)
        r_append(
            "Bắt đầu: DOCX ~4–5 trang (I–VI, VII=tham khảo, link dạng [chữ](URL)) + Excel + 3 ảnh — thường ~8–18 phút."
        )

        def worker() -> None:
            def prog(line: str) -> None:
                root.after(0, lambda t=line: r_append(t))

            try:
                ok, msg = run_reading_generation(params, on_progress=prog)
            except Exception as e:
                ok, msg = False, str(e)

            def finish() -> None:
                r_busy(False)
                if ok:
                    r_append(f"[Xong] {msg}")
                    messagebox.showinfo("Bài đọc", f"Đã tạo file:\n{msg}")
                else:
                    r_append(f"[Lỗi] {msg}")
                    messagebox.showerror("Lỗi", msg)

            root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    go_btn.configure(command=lambda: run_reading(True))
    go_def_btn.configure(command=lambda: run_reading(False))


def run_app() -> None:
    root = tk.Tk()
    root.title(f"Agent Edu — v{__version__}")
    root.minsize(780, 640)
    root.geometry("900x760")

    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")

    outer = ttk.Frame(root, padding=8)
    outer.pack(fill=tk.BOTH, expand=True)

    nb = ttk.Notebook(outer)
    nb.pack(fill=tk.BOTH, expand=True)

    tab_grade = ttk.Frame(nb, padding=10)
    tab_quiz = ttk.Frame(nb, padding=10)
    tab_reading = ttk.Frame(nb, padding=10)
    nb.add(tab_grade, text="Chấm bài")
    nb.add(tab_quiz, text="Quizz")
    nb.add(tab_reading, text="Bài đọc")

    _build_grade_tab(tab_grade, root)
    _build_quiz_tab(tab_quiz, root)
    _build_reading_tab(tab_reading, root)

    root.mainloop()


def main() -> None:
    run_app()


if __name__ == "__main__":
    main()
