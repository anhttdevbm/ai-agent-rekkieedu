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
    if ($("#gr-model")) fillSelect($("#gr-model"), meta.models, meta.default_model);
    if ($("#h-model")) fillSelect($("#h-model"), meta.models, meta.default_model);

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

    // Lecture docs UI: warmup uses prev/current; others use single
    const lw = $("#quiz-lecture-warmup");
    const ls = $("#quiz-lecture-single");
    if (lw) lw.style.display = warmup ? "" : "none";
    if (ls) ls.style.display = warmup ? "none" : "";
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

  function sanitizeHtmlForPreview(html) {
    const s = String(html || "");
    // remove script/style blocks
    return s
      .replace(/<script[\s\S]*?<\/script>/gi, "")
      .replace(/<style[\s\S]*?<\/style>/gi, "")
      .replace(/\son\w+="[^"]*"/gi, "")
      .replace(/\son\w+='[^']*'/gi, "");
  }

  async function btvnLoadSession() {
    const token = ($("#b-rk-token") && $("#b-rk-token").value) || "";
    const sid = ($("#b-session-id") && $("#b-session-id").value) || "";
    const statusEl = $("#b-session-status");
    const sel = $("#b-homework");
    const preview = $("#b-preview");
    const btn = $("#b-load-session");
    if (!token.trim() || !String(sid).trim()) {
      if (statusEl) statusEl.textContent = "Nhập token và session id trước.";
      return;
    }
    setBusy(btn, true, "Đang tải…");
    if (statusEl) statusEl.textContent = "";
    if (sel) {
      sel.innerHTML = "<option value=''>Đang tải…</option>";
      sel.disabled = true;
    }
    if (preview) preview.textContent = "(Đang tải đề...)";
    try {
      const fd = new FormData();
      fd.set("session_id", String(sid).trim());
      fd.set("rikkei_token", token.trim());
      const r = await fetch("/api/rikkei/session", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi tải session.";
        if (sel) {
          sel.innerHTML = "<option value=''> (Lỗi tải session) </option>";
          sel.disabled = true;
        }
        if (preview) preview.textContent = "(Không tải được đề.)";
        return;
      }
      const hw = (data && data.homework) || [];
      if (!Array.isArray(hw) || hw.length === 0) {
        if (statusEl) statusEl.textContent = "Session không có bài tập (homework) hoặc API trả rỗng.";
        if (sel) {
          sel.innerHTML = "<option value=''> (Không có bài) </option>";
          sel.disabled = true;
        }
        if (preview) preview.textContent = "(Không có đề.)";
        return;
      }
      // store dataset on select
      sel.dataset.items = JSON.stringify(hw);
      sel.innerHTML = "<option value=''>-- Chọn bài --</option>";
      hw.forEach((x) => {
        const o = document.createElement("option");
        o.value = String(x.id || "");
        o.textContent = String(x.title || x.id || "");
        sel.appendChild(o);
      });
      sel.disabled = false;
      if (statusEl) statusEl.textContent = `Đã tải: ${data.name || "session"} (${hw.length} bài).`;
      if (preview) preview.textContent = "(Chọn một bài để xem đề.)";
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {
      setBusy(btn, false);
    }
  }

  async function btvnLogin() {
    const email = ($("#b-rk-email") && $("#b-rk-email").value) || "";
    const pass = ($("#b-rk-pass") && $("#b-rk-pass").value) || "";
    const statusEl = $("#b-rk-login-status");
    const btn = $("#b-rk-login");
    if (!email.trim() || !pass) {
      if (statusEl) statusEl.textContent = "Nhập email và mật khẩu trước.";
      return;
    }
    setBusy(btn, true, "Đang đăng nhập…");
    if (statusEl) statusEl.textContent = "";
    try {
      const fd = new FormData();
      fd.set("email", email.trim());
      fd.set("password", pass);
      const r = await fetch("/api/rikkei/login", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Đăng nhập thất bại.";
        return;
      }
      const token = (data && data.token) || "";
      if (!token) {
        if (statusEl) statusEl.textContent = "Đăng nhập OK nhưng không nhận được token.";
        return;
      }
      if ($("#b-rk-token")) $("#b-rk-token").value = token;
      if (statusEl) statusEl.textContent = "Đã lấy token và điền vào ô Token.";
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {
      setBusy(btn, false);
    }
  }

  function btvnOnPickHomework() {
    const sel = $("#b-homework");
    const preview = $("#b-preview");
    const hText = $("#b-assignment-text");
    const hUrls = $("#b-assignment-image-urls");
    if (!sel || !preview || !hText || !hUrls) return;
    const id = (sel.value || "").trim();
    if (!id) {
      preview.textContent = "(Chọn một bài để xem đề.)";
      hText.value = "";
      hUrls.value = "";
      return;
    }
    let items = [];
    try {
      items = JSON.parse(sel.dataset.items || "[]");
    } catch {}
    const it = items.find((x) => String(x.id) === id);
    if (!it) {
      preview.textContent = "(Không tìm thấy đề.)";
      hText.value = "";
      hUrls.value = "";
      return;
    }
    const html = sanitizeHtmlForPreview(it.description_html || "");
    preview.innerHTML =
      `<div style="font-weight:700;margin:0 0 .5rem 0">${escapeHtml(it.title || "")}</div>` + html;
    hText.value = String(it.plain_text || "").trim();
    hUrls.value = JSON.stringify(it.image_urls || []);
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
      const fd = new FormData(ev.target);
      const text = (fd.get("assignment_text") || "").toString().trim();
      const urls = (fd.get("assignment_image_urls") || "").toString().trim();
      if (!text) {
        alert("Chưa có đề bài. Hãy tải session và chọn bài trước.");
        return;
      }
      const r = await fetch("/api/btvn", { method: "POST", body: fd });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        alert(formatApiErr(err.detail) || "Lỗi chấm BTVN");
        return;
      }
      const data = await r.json().catch(() => ({}));
      const rows = (data && data.rows) || [];
      if (data && data.assignment_fingerprint) {
        const af = data.assignment_fingerprint;
        const note = `Đề bài đang dùng: ${af.chars || 0} ký tự, sha1=${af.sha1_10 || ""}\n${(af.head || "").trim()}`;
        setLog("#b-status", note, false);
      }
      if (resBody && Array.isArray(rows)) {
        rows.forEach((x) => {
          const tr = document.createElement("tr");
          const repo = (x.repo || x.submission || "").trim();
          const repoErr = (x.repo_error || "").trim();
          const cmt = (x.comment || "").trim();
          const aiSus = (x.ai_suspected || "").trim();
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
          tr.appendChild(td(aiSus));
          tr.appendChild(td(aiErr));
          resBody.appendChild(tr);
          
        });
        if (resWrap) resWrap.style.display = "";
      }
      $("#b-status").textContent = "Xong.";
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

  async function postHackathon(ev) {
    ev.preventDefault();
    const btn = $("#h-submit");
    setBusy(btn, true, "Đang tạo…");
    $("#h-status").textContent = "";
    try {
      const fd = new FormData(ev.target);
      // checkbox mode
      fd.set("mode", $("#h-ai") && $("#h-ai").checked ? "ai" : "manual");
      if ($("#h-ai") && $("#h-ai").checked) {
        fd.delete("body_text");
      }
      const r = await fetch("/api/hackathon", { method: "POST", body: fd });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        alert(formatApiErr(err.detail) || "Lỗi tạo đề Hackathon");
        return;
      }
      const blob = await r.blob();
      const cd = r.headers.get("Content-Disposition") || "";
      let name = "de_hackathon.docx";
      const m = /filename\*?=(?:UTF-8'')?([^;\n]+)/i.exec(cd);
      if (m) name = decodeURIComponent(m[1].replace(/['"]/g, "").trim());
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = name;
      a.click();
      URL.revokeObjectURL(a.href);
      $("#h-status").textContent = "Đã tải file DOCX.";
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(btn, false);
    }
  }

  async function postGroup(ev) {
    ev.preventDefault();
    const btn = $("#gr-submit");
    setBusy(btn, true, "Đang chấm…");
    $("#gr-status").textContent = "";
    setLog("#gr-log", "", false);
    try {
      const fd = new FormData(ev.target);
      const r = await fetch("/api/group-activity", { method: "POST", body: fd });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        setLog("#gr-log", formatApiErr(data.detail) || JSON.stringify(data), true);
        return;
      }
      const txt = await r.text().catch(() => "");
      setLog("#gr-log", (txt || "").trim(), false);
      $("#gr-status").textContent = "Xong.";
    } catch (e) {
      setLog("#gr-log", String(e), true);
    } finally {
      setBusy(btn, false);
    }
  }

  function init() {
    tabsSetup();
    $("#form-grade").addEventListener("submit", postGrade);
    $("#form-quiz").addEventListener("submit", postQuiz);
    $("#form-reading").addEventListener("submit", postReading);
    const fh = $("#form-hackathon");
    if (fh) fh.addEventListener("submit", postHackathon);
    const hAI = $("#h-ai");
    if (hAI) {
      hAI.addEventListener("change", () => {
        const on = hAI.checked;
        const box = $("#hackathon-ai-fields");
        if (box) box.style.display = on ? "" : "none";
        const mb = $("#hackathon-manual-body");
        if (mb) mb.style.display = on ? "none" : "";
        const body = $("#h-body");
        if (body) body.required = !on;
      });
      // init state
      hAI.dispatchEvent(new Event("change"));
    }
    const fg = $("#form-group");
    if (fg) fg.addEventListener("submit", postGroup);
    const fb = $("#form-btvn");
    if (fb) fb.addEventListener("submit", postBtvn);
    const bLoad = $("#b-load-session");
    if (bLoad) bLoad.addEventListener("click", btvnLoadSession);
    const bLogin = $("#b-rk-login");
    if (bLogin) bLogin.addEventListener("click", btvnLogin);
    const bSel = $("#b-homework");
    if (bSel) bSel.addEventListener("change", btvnOnPickHomework);
    loadMeta().catch((e) => {
      $("#ver-pill").textContent = "lỗi tải meta";
      console.error(e);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
