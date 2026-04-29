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
    if ($("#hg-model")) fillSelect($("#hg-model"), meta.models, meta.default_model);

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
    const form = ev.target;
    const baseFd = new FormData(form);
    baseFd.set("use_template", $("#g-tpl").checked ? "true" : "false");
    baseFd.set("strict_ai", $("#g-strict").checked ? "true" : "false");
    setBusy(btn, true, "Đang chấm…");
    setLog("#g-log", "", false);
    $("#g-status").textContent = "";
    $("#g-status").classList.add("run");
    try {
      const subsText = (baseFd.get("submissions_text") || "").toString();
      const repsText = (baseFd.get("report_repos_text") || "").toString();
      const rawSubs = subsText
        .split(/\r?\n/)
        .map((x) => x.replace(/\r/g, ""))
        .filter((x) => !(x.trim().startsWith("#")));
      const rawReps = repsText
        .split(/\r?\n/)
        .map((x) => x.replace(/\r/g, ""))
        .filter((x) => !(x.trim().startsWith("#")));

      // pad to same length, keep blanks (backend supports report-only rows)
      const n = Math.max(rawSubs.length, rawReps.length);
      const subsLines = rawSubs.concat(Array(Math.max(0, n - rawSubs.length)).fill(""));
      const repLines = rawReps.concat(Array(Math.max(0, n - rawReps.length)).fill(""));
      // trim trailing pairs of blanks
      let end = n;
      while (end > 0 && !subsLines[end - 1].trim() && !repLines[end - 1].trim()) end--;
      const subsFinal = subsLines.slice(0, end);
      const repsFinal = repLines.slice(0, end);

      const batchUi = parseInt((($("#g-batch") && $("#g-batch").value) || "5").toString(), 10);
      const parallelUi = parseInt((($("#g-par") && $("#g-par").value) || "2").toString(), 10);
      const BATCH_SIZE = Number.isFinite(batchUi) && batchUi > 0 ? Math.min(20, batchUi) : 5;
      const PARALLEL = Number.isFinite(parallelUi) && parallelUi > 0 ? Math.min(4, parallelUi) : 2;
      const total = Math.max(subsFinal.length, repsFinal.length) || 0;
      const chunks = [];
      if (total <= BATCH_SIZE) {
        chunks.push({ start: 0, end: total, subs: subsFinal, reps: repsFinal });
      } else {
        for (let i = 0; i < total; i += BATCH_SIZE) {
          const subChunk = subsFinal.slice(i, i + BATCH_SIZE);
          const repChunk = repsFinal.slice(i, i + BATCH_SIZE);
          chunks.push({
            start: i,
            end: Math.min(i + BATCH_SIZE, total),
            subs: subChunk,
            reps: repChunk,
          });
        }
      }

      let allOk = true;
      let mergedLog = "";
      let done = 0;

      async function runOne(ci) {
        const c = chunks[ci];
        const fd = new FormData();
        for (const [k, v] of baseFd.entries()) {
          if (k === "submissions_text" || k === "report_repos_text") continue;
          fd.append(k, v);
        }
        fd.set("submissions_text", (c.subs || []).join("\n"));
        fd.set("report_repos_text", (c.reps || []).join("\n"));

        const r = await fetch("/api/grade", { method: "POST", body: fd });
        const data = await r.json().catch(() => ({}));
        return { ci, ok: r.ok, data };
      }

      const results = new Array(chunks.length);
      let next = 0;
      const workers = [];
      const workerCount = Math.max(1, Math.min(PARALLEL, chunks.length));

      for (let w = 0; w < workerCount; w++) {
        workers.push(
          (async () => {
            while (true) {
              const ci = next++;
              if (ci >= chunks.length) break;
              const c = chunks[ci];
              $("#g-status").textContent = `Đang chấm… (${done}/${total}) | Lô ${ci + 1}/${chunks.length} (${c.start + 1}-${c.end})`;
              try {
                const res = await runOne(ci);
                results[ci] = res;
              } catch (e) {
                results[ci] = { ci, ok: false, data: { detail: String(e) } };
              } finally {
                done += Math.max((chunks[ci].subs || []).length, (chunks[ci].reps || []).length);
              }
            }
          })()
        );
      }

      await Promise.all(workers);

      // merge logs in original order
      const mergedResults = [];
      for (let ci = 0; ci < results.length; ci++) {
        const res = results[ci] || { ok: false, data: { detail: "Không có kết quả" } };
        if (!res.ok) {
          allOk = false;
          mergedLog += `\n[Batch ${ci + 1}/${chunks.length}] LỖI:\n${formatApiErr(res.data.detail) || JSON.stringify(res.data)}\n`;
        } else {
          mergedLog += (res.data.log || "").trim() + "\n\n";
          allOk = allOk && !!res.data.ok;
          const rr = (res.data && res.data.results) || [];
          if (Array.isArray(rr)) mergedResults.push(...rr);
        }
      }
      setLog("#g-log", mergedLog.trim(), !allOk);

      $("#g-status").textContent = allOk ? "Xong." : "Có lỗi — xem log.";

      // Post back to Rikkei if enabled
      const doPost = $("#g-rk-post") && $("#g-rk-post").checked;
      if (doPost) {
        await gradePostScoresToRikkei(mergedResults);
      }
    } catch (e) {
      setLog("#g-log", String(e), true);
    } finally {
      setBusy(btn, false);
      $("#g-status").classList.remove("run");
    }
  }

  function _commentToHtmlP(text) {
    const s = String(text || "").trim();
    if (!s) return "";
    if (/<\s*p[\s>]/i.test(s) || /<br\s*\/?>/i.test(s)) return s;
    return "<p>" + escapeHtml(s).replace(/\n/g, "<br/>") + "</p>";
  }

  async function gradePostScoresToRikkei(gradeResults) {
    const token = ($("#g-rk-token") && $("#g-rk-token").value) || "";
    const statusEl = $("#g-rk-submit-status");
    const idsEl = $("#g-rk-practice-ids");
    if (!token.trim()) {
      if (statusEl) statusEl.textContent = "Không có token để post điểm lên Rikkei.";
      return;
    }
    let ids = [];
    try {
      ids = JSON.parse((idsEl && idsEl.value) || "[]");
    } catch {
      ids = [];
    }
    if (!Array.isArray(ids) || ids.length === 0) {
      if (statusEl) statusEl.textContent = "Chưa có danh sách practice-resource ids (hãy bấm Tải danh sách bài nộp trước).";
      return;
    }

    // results align with visible table rows (selected/unselected kept as blank lines)
    const patches = [];
    for (let i = 0; i < ids.length; i++) {
      const prId = ids[i];
      if (!prId) continue;
      const r = gradeResults[i];
      if (!r || !r.ok || !r.result) continue;
      const score = r.result.final_score;
      const comment = r.result.final_comment;
      if (typeof score !== "number" && typeof score !== "string") continue;
      const sc = parseInt(String(score), 10);
      if (!Number.isFinite(sc)) continue;
      patches.push({ id: prId, score: sc, comment_html: _commentToHtmlP(comment) });
    }

    if (patches.length === 0) {
      if (statusEl) statusEl.textContent = "Không có dòng nào đủ dữ liệu để post (cần ok + có điểm/nhận xét).";
      return;
    }
    if (statusEl) statusEl.textContent = `Đang post ${patches.length} dòng lên Rikkei…`;

    try {
      const fd = new FormData();
      fd.set("rikkei_token", token.trim());
      fd.set("patches_json", JSON.stringify(patches));
      const r = await fetch("/api/rikkei/practice-resource/patch-batch", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi post điểm lên Rikkei.";
        return;
      }
      const okCount = (data && data.ok_count) || 0;
      const failCount = (data && data.fail_count) || 0;
      if (statusEl) statusEl.textContent = `Post xong: OK=${okCount}, lỗi=${failCount}.`;
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    }
  }

  async function gradeLoadPracticeResources() {
    const token = ($("#g-rk-token") && $("#g-rk-token").value) || "";
    const classId = ($("#g-rk-class") && $("#g-rk-class").value) || "";
    const sessionId = ($("#g-rk-session") && $("#g-rk-session").value) || "";
    const statusEl = $("#g-rk-submit-status");
    const btn = $("#g-rk-load-submits");
    const body = $("#g-rk-submit-body");
    const hSubs = $("#g-subs");
    const hReps = $("#g-report-repos");
    const hIds = $("#g-rk-practice-ids");
    const includeGraded = $("#g-rk-include-graded") && $("#g-rk-include-graded").checked;
    const limitUi = parseInt((($("#g-rk-limit") && $("#g-rk-limit").value) || "0").toString(), 10);
    const limitN = Number.isFinite(limitUi) && limitUi > 0 ? limitUi : 0;
    if (!token.trim() || !String(classId).trim() || !String(sessionId).trim()) {
      if (statusEl) statusEl.textContent = "Cần có token + chọn lớp + chọn session thực hành trước.";
      return;
    }
    if (body) body.innerHTML = "";
    if (statusEl) statusEl.textContent = "";
    setBusy(btn, true, "Đang tải…");
    try {
      const fd = new FormData();
      fd.set("rikkei_token", token.trim());
      fd.set("class_id", String(classId).trim());
      fd.set("session_id", String(sessionId).trim());
      const r = await fetch("/api/rikkei/practice-resource", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi tải practice-resource.";
        return;
      }
      const items = (data && data.items) || [];
      if (!Array.isArray(items) || items.length === 0) {
        if (statusEl) statusEl.textContent = "Không có dữ liệu bài nộp cho lớp/session này.";
        return;
      }

      const esc = (s) => escapeHtml(String(s || ""));
      const isBlankComment = (c) => {
        const t = String(c || "").trim();
        if (!t) return true;
        // treat empty html paragraphs as blank
        if (/^<p>\s*(?:<br\s*\/?>)?\s*<\/p>$/i.test(t)) return true;
        if (/^<p>\s*&nbsp;\s*<\/p>$/i.test(t)) return true;
        return false;
      };
      const isUngraded = (x) => x.score == null && isBlankComment(x.comment);

      // Filter: default only ungraded rows; optional include graded
      let visible = includeGraded ? items.slice() : items.filter(isUngraded);
      if (limitN > 0) visible = visible.slice(0, limitN);

      const subsLines = [];
      const repLines = [];
      const idLines = [];
      visible.forEach((x, idx) => {
        const sid = esc(x.studentCode || "");
        const name = esc(x.fullName || "");
        const git = String(x.link || "").trim();
        const rep = String(x.reportLink || "").trim();
        const score = x.score == null ? "" : String(x.score);
        // Default selection:
        // - If not including graded: all visible rows are ungraded → auto-check
        // - If including graded: auto-check top rows (visible list), regardless graded/ungraded
        const checked = true;

        const tr = document.createElement("tr");
        const td = (html) => {
          const c = document.createElement("td");
          c.style.padding = "10px";
          c.style.borderBottom = "1px solid #e5e7eb";
          c.innerHTML = html;
          return c;
        };
        tr.appendChild(
          td(
            `<input type="checkbox" class="g-rk-row" data-idx="${idx}" ${
              checked ? "checked" : ""
            } />`
          )
        );
        tr.appendChild(td(sid));
        tr.appendChild(td(name));
        tr.appendChild(td(git ? `<a href="${esc(git)}" target="_blank" rel="noreferrer">${esc(git)}</a>` : "<span class='small'>(trống)</span>"));
        tr.appendChild(td(rep ? `<a href="${esc(rep)}" target="_blank" rel="noreferrer">${esc(rep)}</a>` : "<span class='small'>(trống)</span>"));
        tr.appendChild(td(esc(score)));
        if (body) body.appendChild(tr);

        subsLines.push(git);
        repLines.push(rep);
        idLines.push(x.id || null);
      });

      if (hSubs) hSubs.value = subsLines.join("\n");
      if (hReps) hReps.value = repLines.join("\n");
      if (hIds) hIds.value = JSON.stringify(idLines);

      // hook checkboxes to rebuild hidden fields
      const rebuild = () => {
        const checks = Array.from(document.querySelectorAll("input.g-rk-row"));
        const s2 = [];
        const r2 = [];
        const ids2 = [];
        checks.forEach((c) => {
          const i = parseInt(c.getAttribute("data-idx") || "0", 10);
          const on = c.checked;
          s2.push(on ? subsLines[i] : "");
          r2.push(on ? repLines[i] : "");
          ids2.push(on ? idLines[i] : null);
        });
        if (hSubs) hSubs.value = s2.join("\n");
        if (hReps) hReps.value = r2.join("\n");
        if (hIds) hIds.value = JSON.stringify(ids2);
      };
      document.querySelectorAll("input.g-rk-row").forEach((c) => {
        c.addEventListener("change", rebuild);
      });

      if (statusEl)
        statusEl.textContent = `Đã tải ${visible.length} dòng${
          includeGraded ? " (gồm cả bài đã chấm)" : " (chỉ bài chưa chấm)"
        }.`;
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {
      setBusy(btn, false);
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
      try {
        localStorage.setItem("rk_token", token);
      } catch {}
      if (statusEl) statusEl.textContent = "Đã lấy token và điền vào ô Token.";
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {
      setBusy(btn, false);
    }
  }

  async function gradeRikkeiLogin() {
    const email = ($("#g-rk-email") && $("#g-rk-email").value) || "";
    const pass = ($("#g-rk-pass") && $("#g-rk-pass").value) || "";
    const statusEl = $("#g-rk-login-status");
    const btn = $("#g-rk-login");
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
      if ($("#g-rk-token")) $("#g-rk-token").value = token;
      if ($("#b-rk-token") && !$("#b-rk-token").value.trim()) $("#b-rk-token").value = token;
      try {
        localStorage.setItem("rk_token", token);
      } catch {}
      if (statusEl) statusEl.textContent = "Đã lấy token.";
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {
      setBusy(btn, false);
    }
  }

  async function gradeLoadSystemsAndCourses() {
    const token = ($("#g-rk-token") && $("#g-rk-token").value) || "";
    const statusEl = $("#g-rk-login-status");
    const btn = $("#g-rk-load");
    const selSys = $("#g-rk-system");
    const selClass = $("#g-rk-class");
    const selCourse = $("#g-rk-course");
    if (!token.trim()) {
      if (statusEl) statusEl.textContent = "Nhập token trước (hoặc đăng nhập để lấy token).";
      return;
    }
    setBusy(btn, true, "Đang tải…");
    if (statusEl) statusEl.textContent = "";
    if (selSys) {
      selSys.innerHTML = "<option value=''>Đang tải…</option>";
      selSys.disabled = true;
    }
    if (selClass) {
      selClass.innerHTML = "<option value=''>Chọn hệ trước</option>";
      selClass.disabled = true;
    }
    if (selCourse) {
      selCourse.innerHTML = "<option value=''>Chọn lớp trước</option>";
      selCourse.disabled = true;
    }
    try {
      const fd = new FormData();
      fd.set("rikkei_token", token.trim());
      const r = await fetch("/api/rikkei/systems", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi tải hệ đào tạo.";
        return;
      }
      const items = (data && data.items) || [];
      if (!Array.isArray(items) || items.length === 0) {
        if (statusEl) statusEl.textContent = "Không có dữ liệu hệ đào tạo.";
        return;
      }
      if (selSys) {
        selSys.innerHTML = "<option value=''>-- Chọn hệ --</option>";
        items.forEach((x) => {
          const o = document.createElement("option");
          o.value = String(x.id ?? "");
          o.textContent = String((x.name || x.systemCode || x.id || "")).trim();
          selSys.appendChild(o);
        });
        selSys.disabled = false;
      }
      if (statusEl) statusEl.textContent = `Đã tải ${items.length} hệ. Chọn 1 hệ để tải lớp.`;
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {
      setBusy(btn, false);
    }
  }

  async function gradeLoadClassesForSystem() {
    const token = ($("#g-rk-token") && $("#g-rk-token").value) || "";
    const sysId = ($("#g-rk-system") && $("#g-rk-system").value) || "";
    const statusEl = $("#g-rk-login-status");
    const selClass = $("#g-rk-class");
    const selCourse = $("#g-rk-course");
    const selSession = $("#g-rk-session");
    if (!token.trim() || !String(sysId).trim()) return;
    if (selClass) {
      selClass.innerHTML = "<option value=''>Đang tải…</option>";
      selClass.disabled = true;
    }
    try {
      const fd = new FormData();
      fd.set("rikkei_token", token.trim());
      fd.set("system_id", String(sysId).trim());
      const r = await fetch("/api/rikkei/classes", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi tải lớp.";
        if (selClass) {
          selClass.innerHTML = "<option value=''> (Lỗi tải lớp) </option>";
          selClass.disabled = true;
        }
        return;
      }
      const items = (data && data.items) || [];
      if (selClass) {
        if (!Array.isArray(items) || items.length === 0) {
          selClass.innerHTML = "<option value=''> (Không có lớp) </option>";
          selClass.disabled = true;
        } else {
          selClass.innerHTML = "<option value=''>-- Chọn lớp --</option>";
          items.forEach((x) => {
            const o = document.createElement("option");
            o.value = String(x.id ?? "");
            o.textContent = String((x.name || x.classCode || x.id || "")).trim();
            selClass.appendChild(o);
          });
          selClass.disabled = false;
        }
      }
      if (selCourse) {
        selCourse.innerHTML = "<option value=''>Chọn lớp trước</option>";
        selCourse.disabled = true;
      }
      if (selSession) {
        selSession.innerHTML = "<option value=''>Chọn môn trước</option>";
        selSession.disabled = true;
      }
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    }
  }

  async function gradeLoadCoursesForClass() {
    const token = ($("#g-rk-token") && $("#g-rk-token").value) || "";
    const classId = ($("#g-rk-class") && $("#g-rk-class").value) || "";
    const statusEl = $("#g-rk-login-status");
    const selCourse = $("#g-rk-course");
    const selSession = $("#g-rk-session");
    if (!token.trim() || !String(classId).trim()) return;
    if (selCourse) {
      selCourse.innerHTML = "<option value=''>Đang tải…</option>";
      selCourse.disabled = true;
    }
    try {
      const fd = new FormData();
      fd.set("rikkei_token", token.trim());
      fd.set("class_id", String(classId).trim());
      const r = await fetch("/api/rikkei/class-courses", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi tải môn học.";
        if (selCourse) {
          selCourse.innerHTML = "<option value=''> (Lỗi tải môn) </option>";
          selCourse.disabled = true;
        }
        return;
      }
      const items = (data && data.items) || [];
      if (selCourse) {
        if (!Array.isArray(items) || items.length === 0) {
          selCourse.innerHTML = "<option value=''> (Không có môn) </option>";
          selCourse.disabled = true;
        } else {
          selCourse.innerHTML = "<option value=''>-- Chọn môn --</option>";
          items.forEach((x) => {
            const o = document.createElement("option");
            o.value = String(x.id ?? "");
            o.textContent = String((x.name || x.courseCode || x.id || "")).trim();
            selCourse.appendChild(o);
          });
          selCourse.disabled = false;
        }
      }
      if (selSession) {
        selSession.innerHTML = "<option value=''>Chọn môn trước</option>";
        selSession.disabled = true;
      }
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    }
  }

  async function gradeLoadPracticeSessionsForCourse() {
    const token = ($("#g-rk-token") && $("#g-rk-token").value) || "";
    const courseId = ($("#g-rk-course") && $("#g-rk-course").value) || "";
    const statusEl = $("#g-rk-login-status");
    const selSession = $("#g-rk-session");
    if (!token.trim() || !String(courseId).trim()) return;
    if (selSession) {
      selSession.innerHTML = "<option value=''>Đang tải…</option>";
      selSession.disabled = true;
    }
    try {
      const fd = new FormData();
      fd.set("rikkei_token", token.trim());
      fd.set("course_id", String(courseId).trim());
      const r = await fetch("/api/rikkei/course-sessions", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi tải session.";
        if (selSession) {
          selSession.innerHTML = "<option value=''> (Lỗi tải session) </option>";
          selSession.disabled = true;
        }
        return;
      }
      const items = (data && data.items) || [];
      if (selSession) {
        if (!Array.isArray(items) || items.length === 0) {
          selSession.innerHTML = "<option value=''> (Không có session thực hành) </option>";
          selSession.disabled = true;
        } else {
          selSession.dataset.items = JSON.stringify(items);
          selSession.innerHTML = "<option value=''>-- Chọn session thực hành --</option>";
          items.forEach((x) => {
            const o = document.createElement("option");
            o.value = String(x.id ?? "");
            const pos = x.position != null ? String(x.position) : "";
            const label = (pos ? `#${pos} ` : "") + String((x.name || x.id || "")).trim();
            o.textContent = label;
            selSession.appendChild(o);
          });
          selSession.disabled = false;
        }
      }
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    }
  }

  function gradeOnPickPracticeSession() {
    const sel = $("#g-rk-session");
    const aText = $("#g-assignment-text");
    if (!sel || !aText) return;
    const id = (sel.value || "").trim();
    if (!id) return;
    let items = [];
    try {
      items = JSON.parse(sel.dataset.items || "[]");
    } catch {}
    const it = items.find((x) => String(x.id) === id);
    if (!it) return;
    const mp = String(it.miniProject || "").trim();
    if (mp && /^https?:\/\//i.test(mp)) {
      aText.value = mp;
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
    const gLogin = $("#g-rk-login");
    if (gLogin) gLogin.addEventListener("click", gradeRikkeiLogin);
    const gLoad = $("#g-rk-load");
    if (gLoad) gLoad.addEventListener("click", gradeLoadSystemsAndCourses);
    const gSys = $("#g-rk-system");
    if (gSys) {
      gSys.addEventListener("change", gradeLoadClassesForSystem);
    }
    const gClass = $("#g-rk-class");
    if (gClass) gClass.addEventListener("change", gradeLoadCoursesForClass);
    const gCourse = $("#g-rk-course");
    if (gCourse) gCourse.addEventListener("change", gradeLoadPracticeSessionsForCourse);
    const gSess = $("#g-rk-session");
    if (gSess) gSess.addEventListener("change", gradeOnPickPracticeSession);
    const gLoadSub = $("#g-rk-load-submits");
    if (gLoadSub) gLoadSub.addEventListener("click", gradeLoadPracticeResources);
    // Hackathon grading
    const hgToken = $("#hg-token");
    if (hgToken) {
      try {
        const t = localStorage.getItem("rk_token") || "";
        if (t && !hgToken.value.trim()) hgToken.value = t;
      } catch {}
    }
    const hgLoad = $("#hg-load");
    if (hgLoad) hgLoad.addEventListener("click", hgLoadSchedules);
    const hgSel = $("#hg-schedule");
    if (hgSel) hgSel.addEventListener("change", hgLoadScheduleDetail);
    const hgRun = $("#hg-run");
    if (hgRun) hgRun.addEventListener("click", hgRunGrading);
    const hgDl = $("#hg-download");
    if (hgDl)
      hgDl.addEventListener("click", async () => {
        const rows = (hgCtx && hgCtx.last_export_rows) || [];
        const statusEl = $("#hg-status");
        if (!Array.isArray(rows) || rows.length === 0) {
          if (statusEl) statusEl.textContent = "Chưa có dữ liệu để xuất Excel (hãy chấm xong trước).";
          return;
        }
        if (statusEl) statusEl.textContent = "Đang tạo Excel…";
        await hgDownloadExcel(rows);
        if (statusEl) statusEl.textContent = "Đã tạo Excel.";
      });
    const hgLimit = $("#hg-limit");
    if (hgLimit)
      hgLimit.addEventListener("change", () => {
        const v = ($("#hg-schedule") && $("#hg-schedule").value) || "";
        if (String(v).trim()) hgLoadScheduleDetail();
      });
    const hgInc = $("#hg-include-graded");
    if (hgInc)
      hgInc.addEventListener("change", () => {
        const v = ($("#hg-schedule") && $("#hg-schedule").value) || "";
        if (String(v).trim()) hgLoadScheduleDetail();
      });
    const bSel = $("#b-homework");
    if (bSel) bSel.addEventListener("change", btvnOnPickHomework);

    // Pre-fill token from localStorage if exists
    try {
      const t = localStorage.getItem("rk_token") || "";
      if (t && $("#g-rk-token") && !$("#g-rk-token").value.trim()) $("#g-rk-token").value = t;
      if (t && $("#b-rk-token") && !$("#b-rk-token").value.trim()) $("#b-rk-token").value = t;
    } catch {}
    loadMeta().catch((e) => {
      $("#ver-pill").textContent = "lỗi tải meta";
      console.error(e);
    });
  }

  // ----------------------------
  // Hackathon grading (Rikkei)
  // ----------------------------

  function extractExamCodeFromRepoLink(url) {
    const s = String(url || "").trim();
    if (!s) return null;
    const m = /github\.com\/[^/]+\/([^/?#]+)(?:\/(.*))?/i.exec(s);
    const repo = m ? String(m[1] || "") : "";
    const tail = m ? String(m[2] || "") : "";
    const candidates = [];
    if (repo) candidates.push(repo.replace(/\.git$/i, ""));
    if (tail) {
      tail
        .split("/")
        .map((x) => x.trim())
        .filter(Boolean)
        .forEach((seg) => candidates.push(seg.replace(/\.sql$/i, "").replace(/\.git$/i, "")));
    }

    function pickCode(text) {
      const t = String(text || "");
      if (!t) return null;
      // ưu tiên dạng _001 / -001 ở cuối
      let mm = /(?:[_-])0*([0-9]{1,3})$/i.exec(t);
      if (!mm) {
        // hỗ trợ dạng ...Nhan03 hoặc ...De02.sql (không có _ trước số)
        mm = /([0-9]{1,3})$/i.exec(t);
      }
      if (!mm) return null;
      const n = parseInt(mm[1], 10);
      if (!Number.isFinite(n) || n <= 0 || n > 999) return null;
      return n;
    }

    // ưu tiên segment sâu hơn (folder/file) rồi mới tới tên repo
    for (let i = candidates.length - 1; i >= 0; i--) {
      const n = pickCode(candidates[i]);
      if (n != null) return n;
    }
    return null;
  }

  function normalizeGithubRepo(url) {
    const s = String(url || "").trim();
    const m = /^https?:\/\/github\.com\/([^/]+)\/([^/?#]+)/i.exec(s);
    if (!m) return s;
    const repo = (m[2] || "").replace(/\.git$/i, "");
    return `https://github.com/${m[1]}/${repo}`;
  }

  let hgCtx = { rows: [], visible: [], docs: {}, last_export_rows: [] };

  function hgNormalizeScore100(raw) {
    let v = parseFloat(String(raw != null ? raw : ""));
    if (!Number.isFinite(v)) v = 0;
    // Hackathon result-test dùng thang 100.
    v = Math.max(0, Math.min(100, v));
    return Math.round(v * 100) / 100;
  }

  function hgSanitizeCommentForCodeOnly(raw) {
    const s = String(raw || "").trim();
    if (!s) return "";
    return s
      .split(/\s+/)
      .join(" ")
      .replace(/mini\s*project\s*\(chỉ\s*có\/không\)\s*:\s*[^\n.?!]*[.?!]?/giu, "")
      .replace(/\bbài\s*tập\s*đầu\s*giờ\b/giu, "Bài thi")
      .replace(/(^|[.?!]\s+)([^.?!]*\bbáo\s*cáo\b[^.?!]*[.?!]?)/giu, "$1")
      .replace(/\s{2,}/g, " ")
      .trim();
  }

  function hgSanitizeHackathonLog(raw) {
    return String(raw || "")
      .replace(/^.*mini\s*project\s*\(chỉ\s*có\/không\)\s*:.*$/gimu, "")
      .replace(/\bbài\s*tập\s*đầu\s*giờ\b/giu, "Bài thi");
  }

  async function hgLoadSchedules() {
    const token = ($("#hg-token") && $("#hg-token").value) || "";
    const statusEl = $("#hg-status");
    const btn = $("#hg-load");
    const sel = $("#hg-schedule");
    if (!token.trim()) {
      if (statusEl) statusEl.textContent = "Nhập token Rikkei trước.";
      return;
    }
    setBusy(btn, true, "Đang tải…");
    if (statusEl) statusEl.textContent = "";
    if (sel) {
      sel.innerHTML = "<option value=''>Đang tải…</option>";
      sel.disabled = true;
    }
    try {
      const fd = new FormData();
      fd.set("rikkei_token", token.trim());
      const r = await fetch("/api/rikkei/test-schedules", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi tải schedules.";
        return;
      }
      const items = (data && data.items) || [];
      if (!Array.isArray(items) || items.length === 0) {
        if (statusEl) statusEl.textContent = "Không có lịch thi.";
        return;
      }
      if (sel) {
        sel.innerHTML = "<option value=''>-- Chọn cuộc thi --</option>";
        items.forEach((x) => {
          const o = document.createElement("option");
          o.value = String(x.id || "");
          o.textContent = `[${(x.type || "").trim()}] ${(x.classCode || "").trim()} — ${(x.testName || "").trim()} (id=${x.id})`;
          o.dataset.testId = String(x.testId || "");
          sel.appendChild(o);
        });
        sel.disabled = false;
      }
      if (statusEl) statusEl.textContent = `Đã tải ${items.length} lịch thi.`;
      try {
        localStorage.setItem("rk_token", token.trim());
      } catch {}
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {
      setBusy(btn, false);
    }
  }

  async function hgLoadScheduleDetail() {
    const token = ($("#hg-token") && $("#hg-token").value) || "";
    const scheduleId = ($("#hg-schedule") && $("#hg-schedule").value) || "";
    const sel = $("#hg-schedule");
    const statusEl = $("#hg-status");
    const body = $("#hg-body");
    const docsEl = $("#hg-docs");
    if (!token.trim() || !String(scheduleId).trim()) return;
    if (body) body.innerHTML = "";
    if (statusEl) statusEl.textContent = "Đang tải chi tiết…";
    try {
      const testId = (sel && sel.selectedOptions && sel.selectedOptions[0] && sel.selectedOptions[0].dataset.testId) || "";
      const fd1 = new FormData();
      fd1.set("rikkei_token", token.trim());
      fd1.set("test_id", String(testId || "").trim());
      const fd2 = new FormData();
      fd2.set("rikkei_token", token.trim());
      fd2.set("schedule_id", String(scheduleId).trim());

      const [rTest, rDet] = await Promise.all([
        fetch("/api/rikkei/test", { method: "POST", body: fd1 }),
        fetch("/api/rikkei/test-schedule-detail", { method: "POST", body: fd2 }),
      ]);
      const testData = await rTest.json().catch(() => ({}));
      const detData = await rDet.json().catch(() => ({}));
      if (!rTest.ok) throw new Error(formatApiErr(testData.detail) || "Lỗi tải test");
      if (!rDet.ok) throw new Error(formatApiErr(detData.detail) || "Lỗi tải detail");

      const docs = (testData && testData.docs) || {};
      const rows = (detData && detData.items) || [];
      hgCtx = { rows, visible: [], docs, last_export_rows: [] };

      if (docsEl) {
        const keys = Object.keys(docs || {}).sort();
        if (!keys.length) {
          docsEl.textContent = "(Không tìm thấy link đề trong test.)";
        } else {
          docsEl.innerHTML =
            keys
              .map((k) => {
                const u = docs[k];
                return `<div>Đề ${escapeHtml(k)}: <a href="${escapeHtml(u)}" target="_blank" rel="noreferrer">${escapeHtml(u)}</a></div>`;
              })
              .join("");
        }
      }

      const includeGraded = $("#hg-include-graded") && $("#hg-include-graded").checked;
      const limitUi = parseInt((($("#hg-limit") && $("#hg-limit").value) || "0").toString(), 10);
      const limitN = Number.isFinite(limitUi) && limitUi > 0 ? limitUi : 0;

      const visible = [];
      for (const x of rows) {
        const already = x.point != null;
        if (!includeGraded && already) continue;
        visible.push(x);
        if (limitN > 0 && visible.length >= limitN) break;
      }
      hgCtx.visible = visible;

      visible.forEach((x, idx) => {
        const gitRaw = String(x.link || "").trim();
        const git = normalizeGithubRepo(gitRaw);
        const code = extractExamCodeFromRepoLink(gitRaw);
        const key = code == null ? "" : String(code).padStart(2, "0");
        const docUrl = key && docs[key] ? docs[key] : "";
        let note = "";
        if (!gitRaw) note = "Không nộp bài.";
        else if (!code) note = "Sai format link (cần hậu tố _001.._005).";
        else if (!docUrl) note = `Không có link đề cho mã ${key}.`;

        const tr = document.createElement("tr");
        const td = (html) => {
          const c = document.createElement("td");
          c.style.padding = "10px";
          c.style.borderBottom = "1px solid #e5e7eb";
          c.innerHTML = html;
          return c;
        };
        const checked = !gitRaw || (!!docUrl && !!git);
        tr.appendChild(td(`<input type="checkbox" class="hg-row" data-idx="${idx}" ${checked ? "checked" : ""} />`));
        tr.appendChild(td(escapeHtml(x.studentCode || "")));
        tr.appendChild(td(escapeHtml(x.fullName || "")));
        tr.appendChild(td(git ? `<a href="${escapeHtml(git)}" target="_blank" rel="noreferrer">${escapeHtml(git)}</a>` : "<span class='small'>(trống)</span>"));
        tr.appendChild(td(docUrl ? `<a href="${escapeHtml(docUrl)}" target="_blank" rel="noreferrer">Đề ${key}</a>` : "<span class='small'>(không có)</span>"));
        tr.appendChild(td(escapeHtml(note)));
        if (body) body.appendChild(tr);
      });
      if (statusEl) statusEl.textContent = `Đã tải ${visible.length}/${rows.length} dòng.`;
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    }
  }

  async function hgRunGrading() {
    const btn = $("#hg-run");
    const model = ($("#hg-model") && $("#hg-model").value) || "";
    const token = ($("#hg-token") && $("#hg-token").value) || "";
    const statusEl = $("#hg-status");
    const logEl = $("#hg-log");
    const dlBtn = $("#hg-download");
    const rows = (hgCtx && hgCtx.visible) || [];
    const docs = (hgCtx && hgCtx.docs) || {};
    const checks = Array.from(document.querySelectorAll("input.hg-row"));
    if (checks.length === 0) {
      if (statusEl) statusEl.textContent = "Không có dòng để chấm.";
      return;
    }
    setBusy(btn, true, "Đang chấm…");
    if (dlBtn) dlBtn.disabled = true;
    const limitUi = parseInt((($("#hg-limit") && $("#hg-limit").value) || "0").toString(), 10);
    const limitN = Number.isFinite(limitUi) && limitUi > 0 ? limitUi : 0;
    const selected = [];
    let picked = 0;
    checks.forEach((c) => {
      if (!c.checked) return;
      if (limitN > 0 && picked >= limitN) return;
      const idx = parseInt(c.getAttribute("data-idx") || "0", 10);
      const x = rows[idx];
      if (!x) return;
      const gitRaw = String(x.link || "").trim();
      const git = normalizeGithubRepo(gitRaw);
      const code = extractExamCodeFromRepoLink(gitRaw);
      const key = code == null ? "" : String(code).padStart(2, "0");
      const docUrl = key && docs[key] ? docs[key] : "";
      const isMissing = !gitRaw;
      if (!isMissing && (!git || !docUrl)) return;
      selected.push({
        docUrl,
        git,
        studentCode: x.studentCode,
        fullName: x.fullName,
        resultTestId: x.id,
        isMissing,
      });
      picked += 1;
    });
    if (selected.length === 0) {
      if (statusEl) statusEl.textContent = "Không có dòng hợp lệ để chấm.";
      return;
    }
    const missingSubs = selected.filter((x) => x.isMissing);
    const normalSubs = selected.filter((x) => !x.isMissing);
    const byDoc = new Map();
    normalSubs.forEach((x) => {
      if (!byDoc.has(x.docUrl)) byDoc.set(x.docUrl, []);
      byDoc.get(x.docUrl).push(x);
    });
    const parUi = parseInt((($("#hg-par") && $("#hg-par").value) || "2").toString(), 10);
    const PAR = Number.isFinite(parUi) && parUi > 0 ? Math.min(4, parUi) : 2;
    if (statusEl) statusEl.textContent = `Đang xử lý ${selected.length} bài (nộp: ${normalSubs.length}, không nộp: ${missingSubs.length})…`;
    if (logEl) logEl.textContent = "";

    const tasks = Array.from(byDoc.entries()).map(([docUrl, arr]) => async () => {
      const fd = new FormData();
      fd.set("assignment_text", docUrl);
      fd.set("submissions_text", arr.map((x) => x.git).join("\n"));
      fd.set("report_repos_text", "");
      fd.set("model", model);
      fd.set("use_template", "true");
      fd.set("strict_ai", "true");
      fd.set("ai_confidence", "75");
      const r = await fetch("/api/grade", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(formatApiErr(data.detail) || "Lỗi /api/grade");
      return { docUrl, arr, data };
    });

    let next = 0;
    const exportRows = [];
    missingSubs.forEach((meta) => {
      exportRows.push({
        resultTestId: meta.resultTestId || "",
        studentCode: meta.studentCode || "",
        fullName: meta.fullName || "",
        repo: "",
        assignment: "",
        ok: true,
        score: 0,
        comment: "Không nộp bài.",
        repo_error: "Không nộp bài.",
        ai_error: "",
      });
    });
    async function worker() {
      while (true) {
        const i = next++;
        if (i >= tasks.length) break;
        const res = await tasks[i]();
        if (logEl) logEl.textContent = (logEl.textContent || "") + "\n" + hgSanitizeHackathonLog(res.data.log || "");
        // Build export rows (align by submissions order)
        const rr = (res.data && res.data.results) || [];
        const arr = res.arr || [];
        for (let j = 0; j < arr.length; j++) {
          const meta = arr[j] || {};
          const rj = rr[j] || {};
          const out = {
            resultTestId: meta.resultTestId || "",
            studentCode: meta.studentCode || "",
            fullName: meta.fullName || "",
            repo: meta.git || "",
            assignment: res.docUrl || "",
            ok: !!rj.ok,
            score: rj.result && rj.result.final_score != null ? rj.result.final_score : "",
            comment: hgSanitizeCommentForCodeOnly(rj.result && rj.result.final_comment ? rj.result.final_comment : ""),
            repo_error: rj.result && rj.result.repo_error ? rj.result.repo_error : "",
            ai_error: rj.result && rj.result.ai_error ? rj.result.ai_error : "",
          };
          exportRows.push(out);
        }
      }
    }
    try {
      if (tasks.length > 0) {
        await Promise.all(Array.from({ length: Math.min(PAR, tasks.length) }, () => worker()));
      }
      hgCtx.last_export_rows = exportRows;
      if (statusEl) statusEl.textContent = "Chấm xong (xem log).";
      if (dlBtn) dlBtn.disabled = !(Array.isArray(exportRows) && exportRows.length > 0);
      const doPost = $("#hg-post") && $("#hg-post").checked;
      if (doPost) {
        if (!String(token || "").trim()) throw new Error("Thiếu token Rikkei để đẩy điểm.");
        if (statusEl) statusEl.textContent = "Đang đẩy điểm lên Rikkei…";
        const postRes = await hgPostScores(token.trim(), exportRows);
        if (logEl) {
          logEl.textContent =
            (logEl.textContent || "") +
            `\n[POST] Thành công: ${postRes.ok_count || 0}, lỗi: ${postRes.fail_count || 0}`;
          const fails = Array.isArray(postRes.fails) ? postRes.fails : [];
          if (fails.length) {
            logEl.textContent += "\n[POST_FAILS]\n" + JSON.stringify(fails.slice(0, 50), null, 2);
          }
        }
      }
      const doExport = $("#hg-export") && $("#hg-export").checked;
      if (doExport) {
        if (statusEl) statusEl.textContent = "Đang tạo Excel…";
        await hgDownloadExcel(exportRows);
        if (statusEl) statusEl.textContent = "Đã tạo Excel (nếu không tự tải, bấm nút Tải Excel kết quả).";
      } else if (statusEl) {
        statusEl.textContent = "Chấm xong.";
      }
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {
      setBusy(btn, false);
    }
  }

  async function hgDownloadExcel(rows) {
    const statusEl = $("#hg-status");
    if (!Array.isArray(rows) || rows.length === 0) return;
    try {
      const fd = new FormData();
      fd.set("rows_json", JSON.stringify(rows));
      const r = await fetch("/api/hackathon-grade/export-xlsx", { method: "POST", body: fd });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        if (statusEl) statusEl.textContent = formatApiErr(err.detail) || "Lỗi xuất Excel.";
        return;
      }
      const blob = await r.blob();
      if (!blob || !blob.size) {
        if (statusEl) statusEl.textContent = "File Excel rỗng (blob.size=0).";
        return;
      }
      const cd = r.headers.get("Content-Disposition") || "";
      let name = "hackathon_results.xlsx";
      const m = /filename\*?=(?:UTF-8'')?([^;\n]+)/i.exec(cd);
      if (m) name = decodeURIComponent(m[1].replace(/['"]/g, "").trim());
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = name;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    }
  }

  async function hgPostScores(token, rows) {
    const patches = [];
    (Array.isArray(rows) ? rows : []).forEach((r) => {
      const id = parseInt(String(r && r.resultTestId != null ? r.resultTestId : ""), 10);
      if (!Number.isFinite(id) || id <= 0) return;
      const score = hgNormalizeScore100(r && r.score != null ? r.score : "");
      const note = hgSanitizeCommentForCodeOnly((r && r.comment) || "");
      patches.push({ id, point: score, note, link: String((r && r.repo) || "").trim() });
    });
    if (!patches.length) return { ok_count: 0, fail_count: 0, fails: [] };
    const fd = new FormData();
    fd.set("rikkei_token", token);
    fd.set("patches_json", JSON.stringify(patches));
    const r = await fetch("/api/rikkei/result-test/patch-batch", { method: "POST", body: fd });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(formatApiErr(data.detail) || "Lỗi đẩy điểm hackathon lên Rikkei.");
    return data || {};
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
