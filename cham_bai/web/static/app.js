(function () {
  const $ = (sel, root = document) => root.querySelector(sel);

  let meta = null;

  async function loadMeta() {
    const r = await fetch("/api/meta");
    if (!r.ok) throw new Error("Không tải được /api/meta");
    meta = await r.json();
    $("#ver-pill").innerHTML =
      'phiên bản <strong>' + escapeHtml(meta.version) + "</strong>";

    const fillSelect = (el, values, def) => {
      el.innerHTML = "";
      values.forEach((v) => {
        const o = document.createElement("option");
        o.value = v;
        o.textContent = v;
        if (v === def) o.selected = true;
        el.appendChild(o);
      });
    };

    fillSelect($("#g-model"), meta.models, meta.default_model);
    fillSelect($("#q-model"), meta.models, meta.default_model);
    fillSelect($("#r-text-model"), meta.models, meta.default_model);
    fillSelect($("#r-image-model"), meta.image_models, meta.default_image_model);
    if ($("#b-model"))
      fillSelect(
        $("#b-model"),
        meta.models,
        meta.default_btvn_model || meta.default_model
      );

    if (meta.default_learning_goals && !$("#r-goals").value.trim()) {
      $("#r-goals").value = meta.default_learning_goals;
    }

    const qk = $("#q-kind");
    qk.innerHTML = "";
    meta.quiz_kinds.forEach((x) => {
      const o = document.createElement("option");
      o.value = x.label;
      o.textContent = x.label;
      qk.appendChild(o);
    });

    applyQuizKindUI();
    qk.addEventListener("change", applyQuizKindUI);
  }

  function formatApiErr(detail) {
    if (detail == null) return "";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail))
      return detail
        .map((x) => (x && (x.msg || x.message)) || JSON.stringify(x))
        .join("\n");
    return JSON.stringify(detail);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setLog(id, text, isErr) {
    const el = $(id);
    el.classList.toggle("error", !!isErr);
    el.textContent = text || "";
  }

  function setBusy(btn, busy, labelBusy) {
    btn.disabled = busy;
    if (labelBusy) btn.dataset._old = btn.textContent;
    btn.textContent = busy ? labelBusy : btn.dataset._old || btn.textContent;
  }

  function applyQuizKindUI() {
    const kindLabel = ($("#q-kind").value || "").trim();
    const warmup = kindLabel === "Quizz Session đầu giờ";
    const end = kindLabel === "Quizz Session cuối giờ";

    const a = $("#quiz-fields-lesson-session");
    const b = $("#quiz-fields-session-warmup");
    if (a) a.style.display = warmup || end ? "none" : "";
    if (b) b.style.display = warmup || end ? "" : "none";

    const lesson = $("#q-lesson");
    const session = $("#q-session");
    const prev = $("#q-session-prev");
    const curr = $("#q-session-curr");
    if (lesson) lesson.required = !(warmup || end);
    if (session) session.required = !(warmup || end);
    if (curr) curr.required = warmup || end;
    if (prev) prev.required = false;

    const wh = $("#warmup-dist-hint");
    if (wh) wh.style.display = warmup ? "block" : "none";
    const eh = $("#end-dist-hint");
    if (eh) eh.style.display = end ? "block" : "none";

    const prevField = $("#quiz-field-session-prev");
    if (prevField) prevField.style.display = end ? "none" : "";

    const nField = $("#quiz-field-num-questions");
    const qn = $("#q-n");
    if (warmup || end) {
      if (nField) nField.style.display = "none";
      if (qn) {
        if (qn.dataset.prevBeforeWarmup === undefined) {
          qn.dataset.prevBeforeWarmup = qn.value || "5";
        }
        qn.value = "45";
      }
    } else {
      if (nField) nField.style.display = "";
      if (qn && qn.dataset.prevBeforeWarmup !== undefined) {
        qn.value = qn.dataset.prevBeforeWarmup;
        delete qn.dataset.prevBeforeWarmup;
      }
    }
  }

  function tabsSetup() {
    const nav = $("#main-tabs");
    nav.querySelectorAll("button[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-tab");
        nav.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        document.querySelectorAll(".panel").forEach((p) => {
          p.classList.toggle("visible", p.id === "panel-" + id);
        });
      });
    });
  }

  async function postGrade(ev) {
    ev.preventDefault();
    const btn = $("#g-submit");
    const fd = new FormData(ev.target);
    fd.set("use_template", $("#g-tpl").checked ? "true" : "false");
    fd.set("strict_ai", $("#g-strict").checked ? "true" : "false");
    setBusy(btn, true, "Đang chấm…");
    setLog("#g-log", "", false);
    $("#g-status").textContent = "";
    $("#g-status").classList.add("run");
    try {
      const r = await fetch("/api/grade", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        setLog("#g-log", formatApiErr(data.detail) || JSON.stringify(data), true);
        return;
      }
      setLog("#g-log", data.log || "", !data.ok);
      $("#g-status").textContent = data.ok ? "Xong." : "Có lỗi — xem log.";
    } catch (e) {
      setLog("#g-log", String(e), true);
    } finally {
      setBusy(btn, false);
      $("#g-status").classList.remove("run");
    }
  }

  async function postQuiz(ev) {
    ev.preventDefault();
    const btn = $("#q-submit");
    setBusy(btn, true, "Đang tạo…");
    $("#q-status").textContent = "";
    try {
      const fd = new FormData(ev.target);
      const r = await fetch("/api/quiz", { method: "POST", body: fd });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        alert(formatApiErr(err.detail) || "Lỗi tạo quiz");
        return;
      }
      const blob = await r.blob();
      const cd = r.headers.get("Content-Disposition") || "";
      let name = "quiz.xlsx";
      const m = /filename\*?=(?:UTF-8'')?([^;\n]+)/i.exec(cd);
      if (m) name = decodeURIComponent(m[1].replace(/['"]/g, "").trim());
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = name;
      a.click();
      URL.revokeObjectURL(a.href);
      $("#q-status").textContent = "Đã tải file Excel.";
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(btn, false);
    }
  }

  function btvnEditorPlainTextWithPlaceholders() {
    const ed = $("#b-assignment-editor");
    if (!ed) return "";
    const clone = ed.cloneNode(true);
    let n = 0;
    clone.querySelectorAll("img").forEach((img) => {
      n += 1;
      const tn = document.createTextNode("\n[Hình " + n + " trong đề]\n");
      img.parentNode.replaceChild(tn, img);
    });
    return clone.innerText
      .replace(/\u00a0/g, " ")
      .replace(/\r\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  async function imgSrcToBlob(src) {
    if (!src || String(src).startsWith("javascript:")) return null;
    try {
      const r = await fetch(src);
      if (!r.ok) return null;
      const blob = await r.blob();
      if (!blob.type.startsWith("image/")) return null;
      return blob;
    } catch {
      return null;
    }
  }

  async function btvnBuildFormData() {
    const fd = new FormData();
    const ed = $("#b-assignment-editor");
    const text = btvnEditorPlainTextWithPlaceholders();
    fd.set("assignment_text", text);
    let failed = 0;
    const totalImg = ed ? ed.querySelectorAll("img").length : 0;
    if (ed) {
      let idx = 0;
      for (const img of ed.querySelectorAll("img")) {
        idx += 1;
        const blob = await imgSrcToBlob(img.src);
        if (!blob || blob.size > 5_000_000) {
          failed += 1;
          continue;
        }
        const ext = (blob.type.split("/")[1] || "png").replace(/[^a-z0-9]/gi, "") || "png";
        fd.append("assignment_images", blob, "de-bai-hinh-" + idx + "." + ext);
      }
    }
    fd.set("submissions_text", ($("#b-subs") && $("#b-subs").value) || "");
    fd.set("model", ($("#b-model") && $("#b-model").value) || "");
    fd.set("github_token", ($("#b-gh-token") && $("#b-gh-token").value) || "");
    return { fd, failed, totalImg };
  }

  function setupBtvnEditor() {
    const ed = $("#b-assignment-editor");
    if (!ed) return;
    ed.addEventListener("paste", (e) => {
      const cd = e.clipboardData;
      if (!cd) return;
      const files = Array.from(cd.files || []).filter((f) => f.type.startsWith("image/"));
      if (!files.length) return;
      e.preventDefault();
      const sel = window.getSelection();
      if (!sel || !sel.rangeCount) return;
      const range = sel.getRangeAt(0);
      range.deleteContents();
      const plain = cd.getData("text/plain");
      if (plain) {
        range.insertNode(document.createTextNode(plain));
        range.collapse(false);
      }
      for (const file of files) {
        if (file.size > 5_000_000) continue;
        const url = URL.createObjectURL(file);
        const img = document.createElement("img");
        img.src = url;
        img.alt = "";
        range.insertNode(img);
        range.setStartAfter(img);
        range.collapse(true);
      }
    });
    ed.addEventListener("dragover", (e) => e.preventDefault());
    ed.addEventListener("drop", (e) => {
      e.preventDefault();
      const files = Array.from(e.dataTransfer && e.dataTransfer.files ? e.dataTransfer.files : []).filter(
        (f) => f.type.startsWith("image/")
      );
      if (!files.length) return;
      const sel = window.getSelection();
      let range;
      if (sel && sel.rangeCount && ed.contains(sel.anchorNode)) {
        range = sel.getRangeAt(0);
      } else {
        range = document.createRange();
        range.selectNodeContents(ed);
        range.collapse(false);
      }
      for (const file of files) {
        if (file.size > 5_000_000) continue;
        const url = URL.createObjectURL(file);
        const img = document.createElement("img");
        img.src = url;
        img.alt = "";
        range.insertNode(img);
        range.setStartAfter(img);
        range.collapse(true);
      }
    });
  }

  async function postBtvn(ev) {
    ev.preventDefault();
    const btn = $("#b-submit");
    setBusy(btn, true, "Đang xử lý BTVN…");
    $("#b-status").textContent = "";
    const resWrap = $("#b-results");
    const resBody = $("#b-results-body");
    if (resWrap) resWrap.style.display = "none";
    if (resBody) resBody.innerHTML = "";
    try {
      const { fd, failed, totalImg } = await btvnBuildFormData();
      const r = await fetch("/api/btvn", { method: "POST", body: fd });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        alert(formatApiErr(err.detail) || "Lỗi chấm BTVN");
        return;
      }
      const data = await r.json().catch(() => ({}));
      const rows = (data && data.rows) || [];
      if (resBody && Array.isArray(rows)) {
        rows.forEach((x) => {
          const tr = document.createElement("tr");
          const repo = (x.repo || x.submission || "").trim();
          const repoErr = (x.repo_error || "").trim();
          const cmt = (x.comment || "").trim();
          const aiErr = (x.ai_error || "").trim();
          const td = (t) => {
            const el = document.createElement("td");
            el.style.padding = "10px";
            el.style.borderBottom = "1px solid #f3f4f6";
            el.textContent = t;
            return el;
          };
          tr.appendChild(td(repo));
          tr.appendChild(td(repoErr));
          tr.appendChild(td(cmt));
          tr.appendChild(td(aiErr));
          resBody.appendChild(tr);
          
        });
        if (resWrap) resWrap.style.display = "";
      }
      let statusMsg = "Xong.";
      if (totalImg > 0 && failed > 0) {
        statusMsg +=
          " Cảnh báo: " +
          failed +
          "/" +
          totalImg +
          " ảnh trong đề không gửi được (link bị chặn hoặc quá 5MB) — thử dán ảnh trực tiếp hoặc chụp màn hình.";
      }
      $("#b-status").textContent = statusMsg;
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(btn, false);
    }
  }

  async function postReading(ev) {
    ev.preventDefault();
    const btn = $("#r-submit");
    setBusy(btn, true, "Đang tạo bài đọc…");
    $("#r-status").textContent = "";
    try {
      const fd = new FormData(ev.target);
      fd.set("generate_illustrations", $("#r-img").checked ? "true" : "false");
      const r = await fetch("/api/reading", { method: "POST", body: fd });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        alert(formatApiErr(err.detail) || "Lỗi tạo bài đọc");
        return;
      }
      const blob = await r.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "bai-doc.zip";
      a.click();
      URL.revokeObjectURL(a.href);
      $("#r-status").textContent = "Đã tải ZIP (DOCX + Excel).";
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(btn, false);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    tabsSetup();
    $("#form-grade").addEventListener("submit", postGrade);
    $("#form-quiz").addEventListener("submit", postQuiz);
    $("#form-reading").addEventListener("submit", postReading);
    const fb = $("#form-btvn");
    if (fb) fb.addEventListener("submit", postBtvn);
    setupBtvnEditor();
    loadMeta().catch((e) => {
      $("#ver-pill").textContent = "lỗi tải meta";
      console.error(e);
    });
  });
})();
