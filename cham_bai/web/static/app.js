(function () {
  const $ = (sel, root = document) => root.querySelector(sel);

  let meta = null;
  let _quizKindPrevLabel = "";

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
    if ($("#ga-model")) fillSelect($("#ga-model"), meta.models, meta.default_model);
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

  function pickCheapestTextModel(models, fallback) {
    const arr = Array.isArray(models) ? models : [];
    // Prefer the explicitly requested default for this popup (cheap/fast text)
    const flash = arr.find((m) => m === "google/gemini-3-flash-preview");
    if (flash) return flash;
    // Fallback: any free-tier models
    const free = arr.find((m) => typeof m === "string" && m.includes(":free"));
    if (free) return free;
    // Last: meta default or fallback
    return fallback || (arr[0] || "");
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

    const qm = $("#q-model");
    const sessionQuizModel =
      (meta && meta.default_quiz_session_warmup_end_model) ||
      "google/gemma-4-26b-a4b-it";
    const wasSessionQuiz =
      _quizKindPrevLabel === "Quizz Session đầu giờ" || _quizKindPrevLabel === "Quizz Session cuối giờ";
    const enteringSessionQuiz = (warmup || end) && !wasSessionQuiz;
    if (qm && enteringSessionQuiz) {
      for (let i = 0; i < qm.options.length; i++) {
        if (qm.options[i].value === sessionQuizModel) {
          qm.value = sessionQuizModel;
          break;
        }
      }
    }
    _quizKindPrevLabel = kindLabel;
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
      // Rikkei thường trả score: 0 + comment rỗng cho bài chưa chấm (không phải null).
      const isUngraded = (x) => {
        if (!isBlankComment(x.comment)) return false;
        if (x.score == null || x.score === "") return true;
        const n = Number(x.score);
        return !Number.isFinite(n) || n === 0;
      };

      // Filter: default only ungraded rows; optional include graded; then optional cap (g-rk-limit)
      const filtered = includeGraded ? items.slice() : items.filter(isUngraded);
      let visible = filtered.slice();
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

      if (statusEl) {
        let msg = `API: ${items.length} bài. Hiển thị ${visible.length} dòng${
          includeGraded ? " (gồm cả đã chấm)" : " (chưa chấm)"
        }`;
        if (!includeGraded && filtered.length < items.length) {
          msg += ` — ${items.length - filtered.length} bài đã có điểm/nhận xét (ẩn)`;
        }
        if (limitN > 0 && filtered.length > visible.length) {
          msg += `. Giới hạn ${limitN} dòng (còn ${filtered.length - visible.length} dòng; đặt 0 để lấy hết).`;
        }
        statusEl.textContent = msg;
      }
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {
      setBusy(btn, false);
    }
  }

  let _quizPollToken = 0;

  async function fetchQuizJobStatus(jobId, { retries = 3 } = {}) {
    const url = `/api/quiz/jobs/${encodeURIComponent(jobId)}`;
    let lastDetail = "";
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      const sr = await fetch(url, { cache: "no-store" });
      const st = await sr.json().catch(() => ({}));
      if (sr.ok) return st;
      lastDetail = formatApiErr(st.detail) || `HTTP ${sr.status}`;
      // 404 thường do request rơi worker khác (trước khi deploy job store trên disk) — thử lại.
      if (sr.status === 404 && attempt < retries) {
        await new Promise((resolve) => setTimeout(resolve, 400 + attempt * 300));
        continue;
      }
      throw new Error(lastDetail || "Không đọc được trạng thái job quiz.");
    }
    throw new Error(lastDetail || "Không đọc được trạng thái job quiz.");
  }

  async function fetchQuizJobDownload(jobId, { retries = 6 } = {}) {
    const url = `/api/quiz/jobs/${encodeURIComponent(jobId)}/download`;
    let lastDetail = "";
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      const dr = await fetch(url, { cache: "no-store" });
      if (dr.ok) return dr;
      const err = await dr.json().catch(() => ({}));
      lastDetail = formatApiErr(err.detail) || `HTTP ${dr.status}`;
      if ((dr.status === 404 || dr.status === 409) && attempt < retries) {
        await new Promise((resolve) => setTimeout(resolve, 400 + attempt * 300));
        continue;
      }
      throw new Error(lastDetail || "Lỗi tải file quiz.");
    }
    throw new Error(lastDetail || "Lỗi tải file quiz.");
  }

  async function postQuiz(ev) {
    ev.preventDefault();
    const btn = $("#q-submit");
    const statusEl = $("#q-status");
    const pollToken = ++_quizPollToken;
    setBusy(btn, true, "Đang tạo…");
    if (statusEl) statusEl.textContent = "";
    try {
      const fd = new FormData(ev.target);
      const r = await fetch("/api/quiz", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        alert(formatApiErr(data.detail) || "Lỗi tạo quiz");
        return;
      }
      const jobId = (data && data.job_id) || "";
      if (!jobId) {
        alert("Phản hồi thiếu job_id.");
        return;
      }
      if (statusEl) statusEl.textContent = "Đã nhận yêu cầu, đang chờ AI soạn quiz…";

      const maxWaitMs = 45 * 60 * 1000;
      const t0 = Date.now();
      let lastMsg = "";
      let pollMs = 4000;
      let pollCount = 0;

      while (Date.now() - t0 < maxWaitMs) {
        if (pollToken !== _quizPollToken) return;
        const st = await fetchQuizJobStatus(jobId);
        if (pollToken !== _quizPollToken) return;
        pollCount += 1;
        const status = String(st.status || "");
        const msg = String(st.message || "").trim();
        const elapsedMin = Math.floor((Date.now() - t0) / 60000);
        const statusLine = msg
          ? `${msg} (${elapsedMin} phút, lần kiểm tra ${pollCount})`
          : `Đang chạy… (${elapsedMin} phút, lần kiểm tra ${pollCount})`;
        if (statusLine !== lastMsg) {
          lastMsg = statusLine;
          if (statusEl) statusEl.textContent = statusLine;
        }
        if (status === "done") {
          const dr = await fetchQuizJobDownload(jobId);
          const blob = await dr.blob();
          const cd = dr.headers.get("Content-Disposition") || "";
          let name = (st.filename || "quiz.xlsx").trim() || "quiz.xlsx";
          const m = /filename\*?=(?:UTF-8'')?([^;\n]+)/i.exec(cd);
          if (m) name = decodeURIComponent(m[1].replace(/['"]/g, "").trim());
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = name;
          a.click();
          URL.revokeObjectURL(a.href);
          if (statusEl) statusEl.textContent = "Đã tải file Excel.";
          return;
        }
        if (status === "error") {
          alert(msg || "Lỗi tạo quiz.");
          return;
        }
        // Backoff: 4s → 6s → … → tối đa 20s (ít request hơn khi sinh quiz 15–30 phút)
        pollMs = Math.min(20000, 4000 + Math.floor(pollCount / 4) * 2000);
        await new Promise((resolve) => setTimeout(resolve, pollMs));
      }
      alert("Hết thời gian chờ (quiz vẫn có thể đang chạy trên server). Thử lại sau.");
    } catch (e) {
      alert(String(e));
    } finally {
      if (pollToken === _quizPollToken) setBusy(btn, false);
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

  let btvnCtx = { students: [], sessionHomeworkCount: 0 };

  function btvnNormText(s) {
    return String(s || "")
      .replace(/[đĐ]/g, "d")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function btvnNormPersonName(s) {
    let t = String(s || "").trim();
    t = t.replace(/[đĐ]/g, "d");
    t = t.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    t = t.replace(BTVN_DATE_CHUNK_RE, " ");
    t = t.replace(/[\s_\-–—]+$/, "");
    t = t.replace(/\s+\d+\s*$/, "");
    t = t.replace(/\(leader\)/gi, "");
    return t.replace(/\s+/g, " ").trim().toLowerCase();
  }

  function btvnNormNameForMatch(s) {
    return btvnNormPersonName(s);
  }

  const BTVN_DATE_CHUNK_RE =
    /(?:[\s_\-–—]+)?(?:\(?\s*)?\d{1,2}\s*[/\-.]+\s*\d{1,2}\s*[/\-.]+\s*\d{2,4}(?:\s*\)?)?/gi;
  const BTVN_GROUP_LINE_RE = /^(?:cntt\s*\d*|nh[oó]m\s*(?:cá\s*biệt|\d+)|group\s*\d*)\s*$/i;

  function btvnSplitTierLine(line) {
    const s = String(line || "").trim();
    if (!s) return null;
    let work = s.replace(BTVN_DATE_CHUNK_RE, " ").trim();
    work = work.replace(/[\s_\-–—]+$/, "").trim();
    const low = btvnNormText(work);
    const suffixes = [
      [" gioi", "Giỏi"],
      [" kha", "Khá"],
      [" yeu", "Yếu"],
      [" tb", "TB"],
    ];
    for (const [suffix, tier] of suffixes) {
      if (!low.endsWith(suffix)) continue;
      const nameLow = low.slice(0, -suffix.length).trim();
      if (!nameLow) continue;
      const tokens = work.split(/\s+/);
      while (tokens.length) {
        const cand = tokens.join(" ");
        if (btvnNormText(cand) === nameLow) return { namePart: cand, tier };
        tokens.pop();
      }
    }
    return null;
  }

  function btvnParseStudentTierText(text) {
    const out = new Map();
    for (const rawLine of String(text || "").split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || BTVN_GROUP_LINE_RE.test(line)) continue;
      const split = btvnSplitTierLine(line);
      if (!split) continue;
      let namePart = split.namePart.replace(BTVN_DATE_CHUNK_RE, " ");
      namePart = namePart.replace(/[\s_\-–—]+$/, "").replace(/\s+/g, " ").trim();
      if (!namePart) continue;
      const key = btvnNormPersonName(namePart);
      if (key) out.set(key, split.tier);
    }
    return out;
  }

  function btvnLookupStudentTier(fullName, tiersMap) {
    const key = btvnNormPersonName(fullName);
    if (!key || !tiersMap || tiersMap.size === 0) return "";
    if (tiersMap.has(key)) return tiersMap.get(key);
    let best = null;
    for (const [k, tier] of tiersMap.entries()) {
      if (!k) continue;
      if (k === key) return tier;
      if (k.length >= 4 && (key.startsWith(k) || k.startsWith(key))) {
        const score = Math.min(k.length, key.length);
        if (!best || score > best.score) best = { score, tier };
      }
    }
    return best ? best.tier : "";
  }

  function btvnGetStudentTiersMap() {
    const tiersEl = $("#b-student-tiers");
    const tiersRaw = tiersEl && tiersEl.value != null ? String(tiersEl.value).trim() : "";
    return tiersRaw ? btvnParseStudentTierText(tiersRaw) : null;
  }

  const BTVN_TIER_OPTIONS = ["Yếu", "TB", "Khá", "Giỏi"];

  function btvnCreateTierSelect(studentId, autoTier, selectedTier) {
    const sel = document.createElement("select");
    sel.className = "b-stu-tier-select";
    sel.dataset.studentId = String(studentId);
    sel.title = "Chọn xếp loại thủ công hoặc để Tự động (map từ danh sách dán)";

    const autoOpt = document.createElement("option");
    autoOpt.value = "";
    autoOpt.textContent = autoTier ? `Tự động (${autoTier})` : "Tự động (—)";
    sel.appendChild(autoOpt);

    BTVN_TIER_OPTIONS.forEach((t) => {
      const o = document.createElement("option");
      o.value = t;
      o.textContent = t;
      sel.appendChild(o);
    });

    const manual = selectedTier && BTVN_TIER_OPTIONS.includes(selectedTier) ? selectedTier : "";
    sel.value = manual;
    sel.dataset.manual = manual ? "1" : "0";

    sel.addEventListener("change", () => {
      sel.dataset.manual = sel.value ? "1" : "0";
    });
    return sel;
  }

  function btvnResolveStudentTier(tr) {
    if (!tr) return "";
    const sel = tr.querySelector(".b-stu-tier-select");
    if (sel && sel.value) return sel.value;
    const name = (tr.dataset && tr.dataset.fullName) || "";
    const tiersMap = btvnGetStudentTiersMap();
    return tiersMap ? btvnLookupStudentTier(name, tiersMap) : "";
  }

  function btvnCollectStudentTierOverrides() {
    const out = {};
    const body = $("#b-students-body");
    if (!body) return out;
    body.querySelectorAll("tr").forEach((tr) => {
      const sid = tr.dataset && tr.dataset.studentId;
      const sel = tr.querySelector(".b-stu-tier-select");
      if (!sid || !sel || !sel.value) return;
      out[String(sid)] = sel.value;
    });
    return out;
  }

  function btvnHasTierModeConfigured() {
    const tiersRaw =
      ($("#b-student-tiers") && $("#b-student-tiers").value != null
        ? String($("#b-student-tiers").value)
        : ""
      ).trim();
    if (tiersRaw) return true;
    const overrides = btvnCollectStudentTierOverrides();
    return Object.keys(overrides).length > 0;
  }

  function btvnRefreshStudentTierColumn() {
    const body = $("#b-students-body");
    if (!body) return;
    const tiersMap = btvnGetStudentTiersMap();
    body.querySelectorAll("tr").forEach((tr) => {
      const sel = tr.querySelector(".b-stu-tier-select");
      if (!sel) return;
      const name =
        (tr.dataset && tr.dataset.fullName) ||
        (tr.children[1] ? tr.children[1].textContent.trim() : "");
      const autoTier = tiersMap ? btvnLookupStudentTier(name, tiersMap) : "";
      const autoOpt = sel.querySelector('option[value=""]');
      if (autoOpt) autoOpt.textContent = autoTier ? `Tự động (${autoTier})` : "Tự động (—)";
      if (sel.dataset.manual !== "1") {
        sel.value = "";
      }
    });
  }

  function btvnUpdatePassRuleHint() {
    const hint = $("#b-pass-rule-hint");
    if (!hint) return;
    const tiersEl = $("#b-student-tiers");
    const tiersRaw = tiersEl && tiersEl.value != null ? String(tiersEl.value).trim() : "";
    const minEl = $("#b-min-completed");
    const ratioEl = $("#b-ratio-ok");
    const scoreEl = $("#b-score-threshold");
    const total = parseInt(String(btvnCtx.sessionHomeworkCount || 0), 10) || 0;
    let scoreTh = 50;
    if (scoreEl && scoreEl.value != null) {
      const s = parseInt(String(scoreEl.value), 10);
      if (Number.isFinite(s)) scoreTh = Math.max(0, Math.min(100, s));
    }
    if (tiersRaw) {
      const lineCount = tiersRaw.split(/\r?\n/).filter((ln) => String(ln || "").trim()).length;
      hint.textContent =
        `Chế độ phân loại (${lineCount} dòng): Yếu — 2 bài đầu; TB — 3 bài đầu; Khá — 3 bài (bỏ bài 1); Giỏi — 3 bài cuối.` +
        ` Tất cả slot bắt buộc đạt (ĐẠT hoặc điểm > ${scoreTh}). Có thể chỉnh từng SV ở cột Phân loại.`;
      btvnRefreshStudentTierColumn();
      return;
    }
    const manualCount = Object.keys(btvnCollectStudentTierOverrides()).length;
    if (manualCount > 0) {
      hint.textContent =
        `Chế độ phân loại thủ công (${manualCount} SV): Yếu 2 đầu; TB 3 đầu; Khá 3 (bỏ bài 1); Giỏi 3 cuối; điểm > ${scoreTh}.`;
      return;
    }
    const minRaw = minEl && minEl.value != null ? String(minEl.value).trim() : "";
    let minN = null;
    if (minRaw) {
      const p = parseInt(minRaw, 10);
      if (Number.isFinite(p) && p > 0) minN = p;
    }
    let ratio = 0.5;
    if (ratioEl && ratioEl.value != null) {
      const r = parseFloat(String(ratioEl.value));
      if (Number.isFinite(r) && r > 0) ratio = Math.max(0.05, Math.min(1, r));
    }
    let required = null;
    if (total > 0) {
      required = minN != null ? Math.min(minN, total) : Math.max(1, Math.ceil(total * ratio - 1e-9));
    }
    if (minN != null && total > 0) {
      hint.textContent = `Quy tắc: đạt ≥ ${required}/${total} bài (bạn chọn ${minN}); điểm > ${scoreTh} hoặc dòng ĐẠT trong nhận xét.`;
    } else if (total > 0) {
      hint.textContent = `Quy tắc: đạt ≥ ${required}/${total} bài (${Math.round(ratio * 100)}% làm tròn lên); điểm > ${scoreTh} hoặc dòng ĐẠT.`;
    } else {
      hint.textContent = `Chọn session để xem tổng số bài. Để trống «Số bài đạt» = ${Math.round(ratio * 100)}% tổng; điểm > ${scoreTh}.`;
    }
    btvnRefreshStudentTierColumn();
  }

  async function btvnLoadSession() {
    const token = ($("#b-rk-token") && $("#b-rk-token").value) || "";
    const sid = ($("#b-rk-session") && $("#b-rk-session").value) || "";
    const statusEl = $("#b-session-status");
    const hwStatusEl = $("#b-homework-status");
    const hwSel = $("#b-homework");
    if (!token.trim() || !String(sid).trim()) {
      if (statusEl) statusEl.textContent = "Nhập token và session id trước.";
      return;
    }
    if (statusEl) statusEl.textContent = "";
    if (hwStatusEl) hwStatusEl.textContent = "Đang tải đề...";
    if (hwSel) {
      hwSel.innerHTML = "<option value=''>Đang tải…</option>";
      hwSel.disabled = true;
      delete hwSel.dataset.items;
    }
    try {
      const fd = new FormData();
      fd.set("session_id", String(sid).trim());
      fd.set("rikkei_token", token.trim());
      const r = await fetch("/api/rikkei/session", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi tải session.";
        return;
      }
      const hw = (data && data.homework) || [];
      if (!Array.isArray(hw) || hw.length === 0) {
        if (statusEl) statusEl.textContent = "Session không có homework hoặc API trả rỗng.";
        if (hwStatusEl) hwStatusEl.textContent = "(Không có đề.)";
        if (hwSel) {
          hwSel.innerHTML = "<option value=''> (Không có bài tập) </option>";
          hwSel.disabled = false;
        }
        return;
      }

      // Fill homework select + auto-pick first
      if (hwSel) {
        hwSel.dataset.items = JSON.stringify(hw);
        hwSel.innerHTML = "<option value=''>-- Chọn bài tập --</option>";
        hw.forEach((x) => {
          const o = document.createElement("option");
          o.value = String(x.id ?? "");
          o.textContent = String((x.title || x.id || "")).trim();
          hwSel.appendChild(o);
        });
        hwSel.disabled = false;
        const first = hw.find((x) => x && (x.id != null || x.title)) || hw[0];
        if (first && first.id != null) hwSel.value = String(first.id);
        btvnOnPickHomework();
      } else {
        // fallback: keep previous behavior
        const picked = hw[0];
        const hid = $("#b-homework-id");
        const aText = $("#b-assignment-text");
        const aImgs = $("#b-assignment-image-urls");
        if (hid) hid.value = String(picked.id || "");
        if (aText) aText.value = String(picked.plain_text || "").trim();
        if (aImgs) aImgs.value = JSON.stringify(picked.image_urls || []);
      }

      if (statusEl) statusEl.textContent = `Đã tải session: ${data && data.name ? data.name : sid}`;
      if (hwStatusEl) hwStatusEl.textContent = `Đã tải ${hw.length} bài tập của session.`;
      btvnCtx.sessionHomeworkCount = hw.length;
      btvnUpdatePassRuleHint();

      // Auto load students ngay khi chọn session
      await btvnLoadStudents();
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    }
  }

  async function btvnLoadSystems() {
    const token = ($("#b-rk-token") && $("#b-rk-token").value) || "";
    const btn = $("#b-rk-load");
    const statusEl = $("#b-session-status");
    const selSys = $("#b-rk-system");
    const selClass = $("#b-rk-class");
    const selCourse = $("#b-rk-course");
    if (!token.trim()) {
      if (statusEl) statusEl.textContent = "Nhập token trước (hoặc đăng nhập để lấy token).";
      return;
    }
    if (btn) setBusy(btn, true, "Đang tải…");
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
      if (btn) setBusy(btn, false);
    }
  }

  async function btvnLoadClassesForSystem() {
    const token = ($("#b-rk-token") && $("#b-rk-token").value) || "";
    const sysId = ($("#b-rk-system") && $("#b-rk-system").value) || "";
    const statusEl = $("#b-session-status");
    const selClass = $("#b-rk-class");
    const selCourse = $("#b-rk-course");
    const selSession = $("#b-rk-session");
    if (!token.trim() || !String(sysId).trim()) return;
    if (selClass) {
      selClass.innerHTML = "<option value=''>Đang tải…</option>";
      selClass.disabled = true;
    }
    if (selCourse) {
      selCourse.innerHTML = "<option value=''>Chọn lớp trước</option>";
      selCourse.disabled = true;
    }
    if (selSession) {
      selSession.innerHTML = "<option value=''>Chọn môn trước</option>";
      selSession.disabled = true;
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
      if (statusEl) statusEl.textContent = `Đã tải ${items.length} lớp. Chọn lớp để tải môn.`;
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    }
  }

  async function btvnLoadCoursesForClass() {
    const token = ($("#b-rk-token") && $("#b-rk-token").value) || "";
    const classId = ($("#b-rk-class") && $("#b-rk-class").value) || "";
    const statusEl = $("#b-session-status");
    const selCourse = $("#b-rk-course");
    const selSession = $("#b-rk-session");
    if (!token.trim() || !String(classId).trim()) return;
    if (selCourse) {
      selCourse.innerHTML = "<option value=''>Đang tải…</option>";
      selCourse.disabled = true;
    }
    if (selSession) {
      selSession.innerHTML = "<option value=''>Chọn môn trước</option>";
      selSession.disabled = true;
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
      if (statusEl) statusEl.textContent = `Đã tải ${items.length} môn. Chọn môn để tải session.`;
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    }
  }

  async function btvnLoadSessionsForCourse() {
    const token = ($("#b-rk-token") && $("#b-rk-token").value) || "";
    const courseId = ($("#b-rk-course") && $("#b-rk-course").value) || "";
    const statusEl = $("#b-session-status");
    const selSession = $("#b-rk-session");
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
          selSession.innerHTML = "<option value=''> (Không có session) </option>";
          selSession.disabled = false;
        } else {
          selSession.dataset.items = JSON.stringify(items);
          selSession.innerHTML = "<option value=''>-- Chọn session --</option>";
          items.forEach((x) => {
            const o = document.createElement("option");
            o.value = String(x.id ?? "");
            const label = `${x.position != null ? `#${x.position} ` : ""}${String((x.name || x.id || "")).trim()}`;
            o.textContent = label;
            selSession.appendChild(o);
          });
          selSession.disabled = false;
        }
      }
      if (statusEl) statusEl.textContent = `Đã tải ${items.length} session. Chọn 1 session để tải homework.`;
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    }
  }

  async function btvnLoadStudents() {
    const token = ($("#b-rk-token") && $("#b-rk-token").value) || "";
    const classId = ($("#b-rk-class") && $("#b-rk-class").value) || "";
    const sessionId = ($("#b-rk-session") && $("#b-rk-session").value) || "";
    const statusEl = $("#b-session-status");
    const body = $("#b-students-body");
    const btn = $("#b-load-students");
    if (!token.trim() || !String(classId).trim() || !String(sessionId).trim()) {
      if (statusEl) statusEl.textContent = "Chọn class và session trước khi tải học sinh.";
      return;
    }
    if (body) body.innerHTML = "";
    if (statusEl) statusEl.textContent = "Đang tải danh sách học sinh…";
    try {
      const fd = new FormData();
      fd.set("rikkei_token", token.trim());
      fd.set("class_id", String(classId).trim());
      fd.set("session_id", String(sessionId).trim());
      const r = await fetch("/api/rikkei/btvn/students", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(formatApiErr(data.detail) || "Lỗi tải học sinh.");
      const items = (data && data.items) || [];
      btvnCtx.students = items;
      if (!Array.isArray(items) || items.length === 0) {
        if (statusEl) statusEl.textContent = "Session không có học sinh.";
        return;
      }
      if (body) {
        body.innerHTML = "";
        items.forEach((st, idx) => {
          const id = st.id != null ? st.id : st.studentId;
          const studentId = parseInt(String(id || ""), 10);
          const code = String(st.studentCode || "").trim();
          const name = String(st.fullName || "").trim();
          const tr = document.createElement("tr");
            tr.dataset.studentId = String(studentId);
            tr.dataset.fullName = name;
          const td = (html) => {
            const c = document.createElement("td");
            c.style.padding = "10px";
            c.style.borderBottom = "1px solid #f3f4f6";
            c.innerHTML = html;
            return c;
          };
          tr.appendChild(td(escapeHtml(code)));
          tr.appendChild(td(escapeHtml(name)));
            // `sessionStudent` thường là mảng nhiều session → pick đúng session đang chọn.
            const pickSessionStatus = () => {
              const sidPick = ($("#b-rk-session") && $("#b-rk-session").value) || "";
              const ss = st.sessionStudent;
              if (!sidPick || !Array.isArray(ss)) return "";
              for (const it of ss) {
                if (!it || typeof it !== "object") continue;
                const itSid = it.sessionId || it.session_id || (it.session && it.session.id);
                if (itSid != null && String(itSid).trim() === String(sidPick).trim()) {
                  return (it.status || "").toString().trim();
                }
              }
              return "";
            };
            let initStatus =
              pickSessionStatus() || st.homeworkStatus || st.status || st.sessionStatus || "";
            // Portal: null/empty => hiểu là "ĐANG CHỜ KIỂM TRA"
            if (!String(initStatus || "").trim()) initStatus = "ĐANG CHỜ KIỂM TRA";
            const tiersMap = btvnGetStudentTiersMap();
            const autoTier = tiersMap ? btvnLookupStudentTier(name, tiersMap) : "";
            const tierTd = document.createElement("td");
            tierTd.style.padding = "10px";
            tierTd.style.borderBottom = "1px solid #f3f4f6";
            tierTd.appendChild(btvnCreateTierSelect(studentId, autoTier, ""));
            tr.appendChild(tierTd);
            tr.appendChild(td(`<span class="b-stu-status">${escapeHtml(initStatus)}</span>`));
          tr.appendChild(
            td(
              `<button type="button" class="smalllink b-stu-view" data-student-id="${studentId}" title="Xem nội dung bài nộp">Xem</button>`
            )
          );
          body.appendChild(tr);
        });
        btvnRefreshStudentTierColumn();
      }
      if (statusEl) statusEl.textContent = `Đã tải ${items.length} học sinh.`;
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {}
  }

  async function btvnFetchStudentExercises(studentId) {
    const token = ($("#b-rk-token") && $("#b-rk-token").value) || "";
    const classId = ($("#b-rk-class") && $("#b-rk-class").value) || "";
    const sessionId = ($("#b-rk-session") && $("#b-rk-session").value) || "";
    const courseId = ($("#b-rk-course") && $("#b-rk-course").value) || "";
    if (!token.trim() || !String(classId).trim() || !String(sessionId).trim()) return [];

    const fd = new FormData();
    fd.set("rikkei_token", token.trim());
    fd.set("class_id", String(classId).trim());
    fd.set("session_id", String(sessionId).trim());
    fd.set("course_id", String(courseId).trim());
    fd.set("student_id", String(studentId).trim());
    const r = await fetch("/api/rikkei/btvn/student-exercises", { method: "POST", body: fd });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(formatApiErr(data.detail) || "Lỗi tải bài nộp.");
    return (data && data.items) || [];
  }

  function btvnEnsureModal() {
    let modal = $("#btvn-modal");
    if (!modal) {
      const wrap = document.createElement("div");
      wrap.id = "btvn-modal";
      wrap.style.position = "fixed";
      wrap.style.inset = "0";
      wrap.style.background = "rgba(0,0,0,.55)";
      wrap.style.display = "none";
      wrap.style.zIndex = "9999";
      wrap.innerHTML = `
        <div style="max-width:900px;margin:6vh auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,.25)">
          <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #e5e7eb">
            <div style="font-weight:700">Nội dung bài nộp</div>
            <button type="button" class="primary" id="btvn-modal-close">Đóng</button>
          </div>
          <div style="padding:16px; max-height:72vh; overflow:auto">
            <div id="btvn-modal-body"></div>
          </div>
        </div>
      `;
      document.body.appendChild(wrap);
      const closeBtn = $("#btvn-modal-close");
      if (closeBtn) closeBtn.addEventListener("click", () => btvnHideModal());
      wrap.addEventListener("click", (e) => {
        if (e.target === wrap) btvnHideModal();
      });
    }
    return modal || $("#btvn-modal");
  }

  function btvnShowModal(textOrHtml) {
    const modal = btvnEnsureModal();
    const body = $("#btvn-modal-body");
    if (body) {
      if (typeof textOrHtml === "string") {
        body.textContent = textOrHtml || "";
      } else {
        body.textContent = "";
      }
    }
    if (modal) modal.style.display = "block";
  }

  function btvnHideModal() {
    const modal = $("#btvn-modal");
    if (modal) modal.style.display = "none";
  }

  function btvnHtmlToText(html) {
    const s = String(html || "");
    return s
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/p\s*>/gi, "\n\n")
      .replace(/<hr\b[^>]*>/gi, "\n\n")
      .replace(/<[^>]*>/g, " ")
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/\s+\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .replace(/[ \t]{2,}/g, " ")
      .trim();
  }

  function btvnFormatResultLine(score) {
    const n = parseInt(String(score || ""), 10);
    if (!Number.isFinite(n)) return "";
    const ok = n >= 50;
    return `Kết quả: ${ok ? "✔ ĐẠT" : "✘ CHƯA ĐẠT"} — ${n}/100`;
  }

  const BTVN_MINDMAP_PHRASE = "Hệ thống kiến thức Mindmap";
  const BTVN_MINDMAP_COMMENT = "Chưa có nhận xét";

  function btvnIsMindmapExercise(it) {
    if (!it || typeof it !== "object") return false;
    const parts = [
      it.homework_title,
      it.title,
      it.name,
      it.description,
      it.homework && it.homework.title,
      it.homework && it.homework.name,
      it.homework && it.homework.description,
    ]
      .filter((x) => typeof x === "string" && x.trim())
      .join("\n");
    if (!parts) return false;
    return parts.toLowerCase().includes(BTVN_MINDMAP_PHRASE.toLowerCase());
  }

  function btvnComposePortalComment(score, note, it) {
    if (it && btvnIsMindmapExercise(it)) return BTVN_MINDMAP_COMMENT;
    const head = btvnFormatResultLine(score);
    const body = String(note || "").trim();
    if (!head && !body) return "";
    if (head && body) return head + "\n\n" + body;
    return head || body;
  }

  function btvnRenderStudentExercisesModal({ studentId, exercises }) {
    const body = $("#btvn-modal-body");
    if (!body) return;
    const items = Array.isArray(exercises) ? exercises : [];
    const esc = (s) => escapeHtml(String(s || ""));
    const defaultModalModel = pickCheapestTextModel(
      meta && meta.models ? meta.models : [],
      meta && (meta.default_btvn_model || meta.default_model)
    );
    body.innerHTML = `
      <style>
        #btvn-modal-body { color:#0f172a; }
        #btvn-modal-body .tbl th, #btvn-modal-body .tbl td { color:#0f172a; }
        #btvn-modal-body .small { color:#475569; }
      </style>
      <div style="display:flex;gap:10px;align-items:center;justify-content:space-between;margin:0 0 10px 0">
        <div>
          <div style="font-weight:700">Bài nộp của sinh viên</div>
          <div class="small" style="margin-top:4px">Chọn 1 hoặc nhiều bài để ghi nhận xét lên portal.</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <select id="btvn-modal-model" style="max-width:340px;background:#fff;color:#0f172a;border:1px solid #cbd5e1;border-radius:10px;padding:8px"></select>
          <button type="button" class="primary" id="btvn-modal-ai">AI chấm (đã chọn)</button>
          <button type="button" class="primary" id="btvn-modal-push">Ghi nhận xét (đã chọn)</button>
        </div>
      </div>
      <div style="overflow:auto;border:1px solid #e5e7eb;border-radius:12px">
        <table class="tbl" style="width:100%;border-collapse:collapse">
          <thead>
            <tr>
              <th style="text-align:left;padding:10px;border-bottom:1px solid #e5e7eb">
                <input type="checkbox" id="btvn-modal-checkall" />
              </th>
              <th style="text-align:left;padding:10px;border-bottom:1px solid #e5e7eb">Bài</th>
              <th style="text-align:left;padding:10px;border-bottom:1px solid #e5e7eb">Repo</th>
              <th style="text-align:left;padding:10px;border-bottom:1px solid #e5e7eb">Điểm</th>
              <th style="text-align:left;padding:10px;border-bottom:1px solid #e5e7eb">Nhận xét (ngắn)</th>
            </tr>
          </thead>
          <tbody>
            ${items
              .map((it, idx) => {
                const exId = it && (it.id != null ? it.id : it.exercise_id);
                const link = (it && (it.link_git || it.linkGit || it.linkGitHub || it.link)) || "";
                const hwTitle = (it && (it.homework_title || (it.homework && it.homework.title))) || "";
                const hwId = it && (it.homeworkId || it.homework_id || (it.homework && it.homework.id));
                const isMindmap = btvnIsMindmapExercise(it);
                const rawComment = it && (it.comment || it.note || "");
                const commentTxt = isMindmap ? BTVN_MINDMAP_COMMENT : btvnHtmlToText(rawComment);
                const score = isMindmap ? "" : it && (it.score != null ? it.score : "");
                return `
                  <tr data-idx="${idx}" data-mindmap="${isMindmap ? "1" : "0"}" style="vertical-align:top">
                    <td style="padding:10px;border-bottom:1px solid #f3f4f6">
                      <input type="checkbox" class="btvn-ex-chk" data-idx="${idx}" />
                    </td>
                    <td style="padding:10px;border-bottom:1px solid #f3f4f6">
                      <div style="font-weight:700">${esc(hwTitle || ("Exercise " + exId))}</div>
                      ${isMindmap ? `<div class="small" style="color:#0d9488;margin-top:4px">Mindmap — không chấm điểm; tự tính hoàn thành</div>` : ""}
                      <div class="small">exercise_id=${esc(exId)} · homework_id=${esc(hwId || "")}</div>
                    </td>
                    <td style="padding:10px;border-bottom:1px solid #f3f4f6;max-width:260px;word-break:break-word">
                      ${link ? `<a href="${esc(link)}" target="_blank" rel="noreferrer" style="color:#0ea5e9;text-decoration:underline">${esc(link)}</a>` : "<span class='small'>(trống)</span>"}
                    </td>
                    <td style="padding:10px;border-bottom:1px solid #f3f4f6;width:110px">
                      <input class="btvn-ex-score" data-idx="${idx}" type="number" min="0" max="100" value="${esc(score)}" ${isMindmap ? "disabled title='Bài Mindmap không chấm điểm'" : ""} style="display:block;width:96px;box-sizing:border-box;background:#fff;color:#0f172a;border:1px solid #cbd5e1;border-radius:10px;padding:8px" />
                    </td>
                    <td style="padding:10px;border-bottom:1px solid #f3f4f6;min-width:320px">
                      <textarea class="btvn-ex-note" data-idx="${idx}" rows="4" ${isMindmap ? "readonly" : ""} style="width:100%;background:#fff;color:#0f172a;border:1px solid #cbd5e1;border-radius:10px;padding:10px" placeholder="Nhận xét 2–4 câu…">${esc(commentTxt)}</textarea>
                      <div class="small" style="margin-top:6px;color:#64748b">
                        ${isMindmap ? "Ghi portal: <code>Chưa có nhận xét</code> (không kèm điểm)." : "Sẽ ghi lên portal theo dạng: <code>Kết quả: ✔ ĐẠT — 85/100</code> + 1 đoạn nhận xét."}
                      </div>
                    </td>
                  </tr>
                `;
              })
              .join("")}
          </tbody>
        </table>
      </div>
      <div class="small" id="btvn-modal-status" style="margin-top:10px"></div>
    `;

    const statusEl = $("#btvn-modal-status");

    // fill model select
    const msel = $("#btvn-modal-model");
    if (msel) {
      const values = (meta && meta.models) || [];
      msel.innerHTML = "";
      (Array.isArray(values) ? values : []).forEach((v) => {
        if (typeof v !== "string" || !v.trim()) return;
        const o = document.createElement("option");
        o.value = v;
        o.textContent = v;
        if (v === defaultModalModel) o.selected = true;
        msel.appendChild(o);
      });
      // If default isn't present, still set value (best-effort)
      if (defaultModalModel && !msel.value) msel.value = defaultModalModel;
    }
    const all = $("#btvn-modal-checkall");
    if (all) {
      all.addEventListener("change", () => {
        const on = all.checked;
        document.querySelectorAll("input.btvn-ex-chk").forEach((c) => (c.checked = on));
      });
    }

    const aiBtn = $("#btvn-modal-ai");
    if (aiBtn) {
      aiBtn.addEventListener("click", async () => {
        const token = ($("#b-rk-token") && $("#b-rk-token").value) || "";
        const assignmentText = ($("#b-assignment-text") && $("#b-assignment-text").value) || "";
        const model =
          ($("#btvn-modal-model") && $("#btvn-modal-model").value) ||
          ($("#b-model") && $("#b-model").value) ||
          "";
        const hwSel = $("#b-homework");
        let hwItems = [];
        try {
          hwItems = hwSel && hwSel.dataset && hwSel.dataset.items ? JSON.parse(hwSel.dataset.items || "[]") : [];
        } catch {
          hwItems = [];
        }
        const hwMap = new Map();
        (Array.isArray(hwItems) ? hwItems : []).forEach((h) => {
          if (!h || typeof h !== "object") return;
          if (h.id == null) return;
          hwMap.set(String(h.id), h);
        });
        if (!String(assignmentText).trim()) {
          if (statusEl) statusEl.textContent = "Thiếu đề bài (assignment_text). Hãy tải session và chọn homework.";
          return;
        }
        const checks = Array.from(document.querySelectorAll("input.btvn-ex-chk")).filter((c) => c.checked);
        if (!checks.length) {
          if (statusEl) statusEl.textContent = "Chưa chọn bài nào.";
          return;
        }
        // Group by homeworkId so each exercise matches correct assignment text
        const groups = new Map(); // key=hwid string (or "default"), value={assignment_text, idxs, repos}
        let mindmapSkipped = 0;
        for (const c of checks) {
          const idx = parseInt(String(c.getAttribute("data-idx") || ""), 10);
          const it = items[idx] || {};
          if (btvnIsMindmapExercise(it)) {
            mindmapSkipped += 1;
            const noteEl = document.querySelector(`textarea.btvn-ex-note[data-idx="${idx}"]`);
            if (noteEl) noteEl.value = BTVN_MINDMAP_COMMENT;
            continue;
          }
          const link = String(it.link_git || it.linkGit || it.link || "").trim();
          if (!link) continue;
          const hwid =
            it.homeworkId || it.homework_id || (it.homework && it.homework.id) || ($("#b-homework-id") && $("#b-homework-id").value) || "";
          const hwKey = hwid != null && String(hwid).trim() ? String(hwid).trim() : "default";
          const hwObj = hwKey !== "default" ? hwMap.get(hwKey) : null;
          const at = hwObj && hwObj.plain_text ? String(hwObj.plain_text).trim() : String(assignmentText).trim();
          if (!groups.has(hwKey)) groups.set(hwKey, { assignment_text: at, idxs: [], repos: [] });
          const g = groups.get(hwKey);
          g.idxs.push(idx);
          g.repos.push(link);
        }
        if (groups.size === 0) {
          if (mindmapSkipped > 0) {
            if (statusEl)
              statusEl.textContent = `Đã bỏ qua ${mindmapSkipped} bài Mindmap (không chấm điểm).`;
            return;
          }
          if (statusEl) statusEl.textContent = "Không có link repo trong các bài đã chọn.";
          return;
        }

        try {
          const total = Array.from(groups.values()).reduce((a, g) => a + (g.repos ? g.repos.length : 0), 0);
          if (statusEl)
            statusEl.textContent =
              (mindmapSkipped > 0 ? `Bỏ qua ${mindmapSkipped} bài Mindmap. ` : "") + `AI đang chấm ${total} bài…`;
          aiBtn.disabled = true;
          for (const g of Array.from(groups.values())) {
            const fd = new FormData();
            fd.set("assignment_text", String(g.assignment_text || ""));
            fd.set("submissions_text", (g.repos || []).join("\n"));
            fd.set("model", String(model || ""));
            fd.set("github_token", "");
            const r = await fetch("/api/btvn/grade", { method: "POST", body: fd });
            const data = await r.json().catch(() => ({}));
            if (!r.ok) {
              if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi AI chấm.";
              return;
            }
            const rows = (data && data.rows) || [];
            for (let j = 0; j < (g.idxs || []).length; j++) {
              const idx = g.idxs[j];
              const row = rows[j] || {};
              const score = row.score;
              const comment = row.comment || "";
              const scoreEl = document.querySelector(`input.btvn-ex-score[data-idx="${idx}"]`);
              const noteEl = document.querySelector(`textarea.btvn-ex-note[data-idx="${idx}"]`);
              if (scoreEl && score != null) scoreEl.value = String(score);
              if (noteEl) noteEl.value = String(comment);
            }
          }
          if (statusEl) statusEl.textContent = "AI chấm xong. Bạn có thể chỉnh sửa rồi bấm “Ghi nhận xét”.";
        } catch (e) {
          if (statusEl) statusEl.textContent = String(e);
        } finally {
          aiBtn.disabled = false;
        }
      });
    }

    const pushBtn = $("#btvn-modal-push");
    if (pushBtn) {
      pushBtn.addEventListener("click", async () => {
        const token = ($("#b-rk-token") && $("#b-rk-token").value) || "";
        if (!String(token).trim()) {
          if (statusEl) statusEl.textContent = "Thiếu token Rikkei.";
          return;
        }
        const checks = Array.from(document.querySelectorAll("input.btvn-ex-chk")).filter((c) => c.checked);
        if (!checks.length) {
          if (statusEl) statusEl.textContent = "Chưa chọn bài nào.";
          return;
        }
        const patches = [];
        for (const c of checks) {
          const idx = parseInt(String(c.getAttribute("data-idx") || ""), 10);
          const it = items[idx] || {};
          const exId = it.id != null ? it.id : it.exercise_id;
          const link_git = String(it.link_git || it.linkGit || it.link || "").trim();
          const hwid = it.homeworkId || it.homework_id || (it.homework && it.homework.id) || null;
          const scoreEl = document.querySelector(`input.btvn-ex-score[data-idx="${idx}"]`);
          const noteEl = document.querySelector(`textarea.btvn-ex-note[data-idx="${idx}"]`);
          const score = scoreEl && scoreEl.value != null ? String(scoreEl.value).trim() : "";
          const note = noteEl && noteEl.value != null ? String(noteEl.value) : "";
          const comment = btvnComposePortalComment(score, note, it);
          patches.push({ exercise_id: exId, link_git, homework_id: hwid, comment, full_body: it });
        }

        try {
          if (statusEl) statusEl.textContent = `Đang ghi ${patches.length} bài lên portal…`;
          pushBtn.disabled = true;
          const fd = new FormData();
          fd.set("rikkei_token", token.trim());
          fd.set("patches_json", JSON.stringify(patches));
          const r = await fetch("/api/rikkei/exercise/patch-batch", { method: "POST", body: fd });
          const data = await r.json().catch(() => ({}));
          if (!r.ok) {
            if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi ghi nhận xét.";
            return;
          }
          if (statusEl) statusEl.textContent = `Xong: OK=${data.ok_count || 0}, lỗi=${data.fail_count || 0}`;
        } catch (e) {
          if (statusEl) statusEl.textContent = String(e);
        } finally {
          pushBtn.disabled = false;
        }
      });
    }
  }

  async function btvnLogin() {
    const email = ($("#b-rk-email") && $("#b-rk-email").value) || "";
    const pass = ($("#b-rk-pass") && $("#b-rk-pass").value) || "";
    const bu = ($("#b-rk-basic-user") && $("#b-rk-basic-user").value) || "";
    const bp = ($("#b-rk-basic-pass") && $("#b-rk-basic-pass").value) || "";
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
      if (String(bu).trim()) fd.set("basic_user", String(bu).trim());
      if (String(bp).trim()) fd.set("basic_pass", String(bp));
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
    const bu = ($("#g-rk-basic-user") && $("#g-rk-basic-user").value) || "";
    const bp = ($("#g-rk-basic-pass") && $("#g-rk-basic-pass").value) || "";
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
      if (String(bu).trim()) fd.set("basic_user", String(bu).trim());
      if (String(bp).trim()) fd.set("basic_pass", String(bp));
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
    setBusy(btn, true, "Đang chốt trạng thái session…");
    $("#b-status").textContent = "";
    const resWrap = $("#b-results");
    const resBody = $("#b-results-body");
    if (resWrap) resWrap.style.display = "none";
    if (resBody) resBody.innerHTML = "";
    try {
      const fd = new FormData(ev.target);
      const classId = ($("#b-rk-class") && $("#b-rk-class").value) || "";
      const sessionId = ($("#b-rk-session") && $("#b-rk-session").value) || "";
      const courseId = ($("#b-rk-course") && $("#b-rk-course").value) || "";
      const sheetUrl = ($("#b-sheet-url") && $("#b-sheet-url").value) || "";
      const sheetName = ($("#b-sheet-name") && $("#b-sheet-name").value) || "";
      if (!String(classId).trim() || !String(sessionId).trim() || !String(courseId).trim()) {
        alert("Chưa chọn đầy đủ class/session/course.");
        return;
      }
      const students = (btvnCtx && btvnCtx.students) || [];
      const studentIds = students
        .map((st) => parseInt(String(st.id != null ? st.id : st.studentId || ""), 10))
        .filter((n) => Number.isFinite(n));
      if (!studentIds.length) {
        alert("Chưa có danh sách học sinh. Hãy chọn session trước.");
        return;
      }
      fd.set("class_id", String(classId).trim());
      fd.set("session_id", String(sessionId).trim());
      fd.set("course_id", String(courseId).trim());
      fd.set("students_ids_json", JSON.stringify(studentIds));
      if (String(sheetUrl).trim()) fd.set("sheet_url", String(sheetUrl).trim());
      if (String(sheetName).trim()) fd.set("sheet_name", String(sheetName).trim());
      // session_no: dùng position (#8) để map vào cột "SESSION 08" trên sheet
      try {
        const sel = $("#b-rk-session");
        const items = sel && sel.dataset && sel.dataset.items ? JSON.parse(sel.dataset.items || "[]") : [];
        const it = Array.isArray(items) ? items.find((x) => String(x.id) === String(sessionId)) : null;
        const pos = it && it.position != null ? parseInt(String(it.position), 10) : null;
        if (Number.isFinite(pos) && pos > 0) fd.set("session_no", String(pos));
      } catch {}
      fd.delete("assignment_text");
      fd.delete("assignment_image_urls");
      fd.delete("homework_id");
      fd.delete("model");
      const minEl = $("#b-min-completed");
      const ratioEl = $("#b-ratio-ok");
      const scoreEl = $("#b-score-threshold");
      if (minEl && String(minEl.value || "").trim()) fd.set("min_completed", String(minEl.value).trim());
      else fd.delete("min_completed");
      if (ratioEl) fd.set("ratio_ok", String(ratioEl.value || "0.5").trim() || "0.5");
      if (scoreEl) fd.set("score_threshold", String(scoreEl.value || "50").trim() || "50");
      const tiersEl = $("#b-student-tiers");
      const tiersRaw = tiersEl && tiersEl.value != null ? String(tiersEl.value).trim() : "";
      const tierOverrides = btvnCollectStudentTierOverrides();
      fd.set("student_tier_overrides_json", JSON.stringify(tierOverrides));
      if (tiersRaw || Object.keys(tierOverrides).length > 0) {
        if (tiersRaw) fd.set("student_tiers_text", tiersRaw);
        else fd.delete("student_tiers_text");
        fd.delete("min_completed");
      } else {
        fd.delete("student_tiers_text");
      }
      const r = await fetch("/api/btvn/rikkei/session-status", { method: "POST", body: fd });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        alert(formatApiErr(err.detail) || "Lỗi chấm BTVN");
        return;
      }
      const data = await r.json().catch(() => ({}));
      const su = data && data.session_update ? data.session_update : data && data.session_update;

      // Update status column in table (best-effort).
      const map = new Map();
      if (su && Array.isArray(su.updated)) {
        su.updated.forEach((u) => {
          if (!u) return;
          if (u.studentId == null) return;
          if (u.ok) map.set(String(u.studentId), u.newStatus || "");
          else map.set(String(u.studentId), "LỖI");
        });
      }
      const rows = $("#b-students-body") ? $("#b-students-body").querySelectorAll("tr") : [];
      rows.forEach((tr) => {
        const sid = tr && tr.dataset ? tr.dataset.studentId : "";
        if (!sid) return;
        const st = map.get(sid);
        const el = tr.querySelector(".b-stu-status");
        if (el && typeof st === "string" && st) el.textContent = st;
      });

      const scoreTh =
        su && su.score_threshold != null && su.score_threshold !== ""
          ? su.score_threshold
          : ($("#b-score-threshold") && $("#b-score-threshold").value) || "50";
      let ratioInfo = "";
      if (su && su.tier_mode) {
        const parsed = su.tier_students_parsed != null ? su.tier_students_parsed : "?";
        ratioInfo = ` (phân loại: ${parsed} SV; điểm > ${scoreTh})`;
      } else if (su && typeof su.ratio_ok_count !== "undefined" && typeof su.total !== "undefined") {
        ratioInfo = ` (cần đạt ≥ ${su.ratio_ok_count}/${su.total} bài; điểm > ${scoreTh})`;
      }
      const ignoredCount = su && Array.isArray(su.ignored) ? su.ignored.length : 0;
      const msg = su && su.ok
        ? `Session update: ${su.ok_count || 0} cập nhật, ${su.fail_count || 0} lỗi, ${ignoredCount} bị bỏ qua${ratioInfo}`
        : `Session update: thất bại${ratioInfo ? ratioInfo : ""}.`;
      let sheetMsg = "";
      if (data && data.sheet_update) {
        const sh = data.sheet_update;
        sheetMsg = sh.ok
          ? `Sheet update: ${sh.updated || 0} dòng, thiếu: ${(sh.missing && sh.missing.length) || 0}`
          : `Sheet update: lỗi (${(sh.error || "").toString()})`;
      }
      $("#b-status").textContent = msg + (sheetMsg ? "\n" + sheetMsg : "") + "\nXong.";
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(btn, false);
    }
  }

  async function fetchReadingJobStatus(jobId, { retries = 3 } = {}) {
    const url = `/api/reading/jobs/${encodeURIComponent(jobId)}`;
    let lastDetail = "";
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      const sr = await fetch(url, { cache: "no-store" });
      const st = await sr.json().catch(() => ({}));
      if (sr.ok) return st;
      lastDetail = formatApiErr(st.detail) || `HTTP ${sr.status}`;
      if (sr.status === 404 && attempt < retries) {
        await new Promise((resolve) => setTimeout(resolve, 400 + attempt * 300));
        continue;
      }
      throw new Error(lastDetail || "Không đọc được trạng thái job bài đọc.");
    }
    throw new Error(lastDetail || "Không đọc được trạng thái job bài đọc.");
  }

  async function fetchReadingJobDownload(jobId, { retries = 6 } = {}) {
    const url = `/api/reading/jobs/${encodeURIComponent(jobId)}/download`;
    let lastDetail = "";
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      const dr = await fetch(url, { cache: "no-store" });
      if (dr.ok) return dr;
      const err = await dr.json().catch(() => ({}));
      lastDetail = formatApiErr(err.detail) || `HTTP ${dr.status}`;
      if ((dr.status === 404 || dr.status === 409) && attempt < retries) {
        await new Promise((resolve) => setTimeout(resolve, 400 + attempt * 300));
        continue;
      }
      throw new Error(lastDetail || "Lỗi tải file bài đọc.");
    }
    throw new Error(lastDetail || "Lỗi tải file bài đọc.");
  }

  let _readingPollToken = 0;

  async function postReading(ev) {
    ev.preventDefault();
    const btn = $("#r-submit");
    const statusEl = $("#r-status");
    const pollToken = ++_readingPollToken;
    setBusy(btn, true, "Đang tạo bài đọc…");
    if (statusEl) statusEl.textContent = "";
    try {
      const fd = new FormData(ev.target);
      fd.set("generate_illustrations", $("#r-img").checked ? "true" : "false");
      const r = await fetch("/api/reading", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        alert(formatApiErr(data.detail) || "Lỗi tạo bài đọc");
        return;
      }
      const jobId = (data && data.job_id) || "";
      if (!jobId) {
        alert("Phản hồi thiếu job_id.");
        return;
      }
      if (statusEl) statusEl.textContent = "Đã nhận yêu cầu, đang soạn bài đọc…";

      const maxWaitMs = 45 * 60 * 1000;
      const t0 = Date.now();
      let lastMsg = "";
      let pollCount = 0;

      while (Date.now() - t0 < maxWaitMs) {
        if (pollToken !== _readingPollToken) return;
        const st = await fetchReadingJobStatus(jobId);
        if (pollToken !== _readingPollToken) return;
        pollCount += 1;
        const status = String(st.status || "");
        const msg = String(st.message || "").trim();
        const elapsedMin = Math.floor((Date.now() - t0) / 60000);
        const statusLine = msg
          ? `${msg} (${elapsedMin} phút)`
          : `Đang chạy… (${elapsedMin} phút)`;
        if (statusLine !== lastMsg) {
          lastMsg = statusLine;
          if (statusEl) statusEl.textContent = statusLine;
        }
        if (status === "done") {
          const dr = await fetchReadingJobDownload(jobId);
          const blob = await dr.blob();
          let name = (st.filename || "bai-doc.zip").trim() || "bai-doc.zip";
          const cd = dr.headers.get("Content-Disposition") || "";
          const m = /filename\*?=(?:UTF-8'')?([^;\n]+)/i.exec(cd);
          if (m) name = decodeURIComponent(m[1].replace(/['"]/g, "").trim());
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = name;
          a.click();
          URL.revokeObjectURL(a.href);
          if (statusEl) statusEl.textContent = "Đã tải ZIP (DOCX + Excel).";
          return;
        }
        if (status === "error") {
          alert(msg || "Lỗi tạo bài đọc.");
          return;
        }
        const pollMs = Math.min(20000, 4000 + Math.floor(pollCount / 4) * 2000);
        await new Promise((resolve) => setTimeout(resolve, pollMs));
      }
      alert("Hết thời gian chờ (bài đọc vẫn có thể đang chạy trên server). Thử lại sau.");
    } catch (e) {
      alert(String(e));
    } finally {
      if (pollToken === _readingPollToken) setBusy(btn, false);
    }
  }

  let gaCtx = { last_export_rows: [] };

  function gaParseStudents(text) {
    const lines = String(text || "")
      .split(/\r?\n/)
      .map((x) => x.trim())
      .filter((x) => x && !x.startsWith("#"));
    const out = [];
    for (const ln of lines) {
      // Prefer TAB-separated: name \t code \t repo
      const partsTab = ln
        .split("\t")
        .map((x) => x.trim())
        .filter(Boolean);
      if (partsTab.length >= 3) {
        const name = partsTab[0];
        const code = partsTab[1];
        const repo = partsTab.slice(2).join("\t").trim();
        out.push({ fullName: name, studentCode: code, repo });
        continue;
      }
      // Fallback: whitespace; repo=last token, code=prev token, name=rest
      const toks = ln.split(/\s+/).filter(Boolean);
      if (toks.length < 3) continue;
      const repo = toks[toks.length - 1];
      const code = toks[toks.length - 2];
      const name = toks.slice(0, toks.length - 2).join(" ").trim();
      out.push({ fullName: name, studentCode: code, repo });
    }
    return out;
  }

  function gaSetResults(rows) {
    const wrap = $("#ga-results");
    const body = $("#ga-results-body");
    if (body) body.innerHTML = "";
    if (!Array.isArray(rows) || rows.length === 0) {
      if (wrap) wrap.style.display = "none";
      return;
    }
    const esc = (s) => escapeHtml(String(s || ""));
    rows.forEach((r) => {
      const tr = document.createElement("tr");
      const td = (html) => {
        const c = document.createElement("td");
        c.style.padding = "10px";
        c.style.borderBottom = "1px solid #f3f4f6";
        c.innerHTML = html;
        return c;
      };
      const repo = String(r.repo || "").trim();
      tr.appendChild(td(esc(r.studentCode || "")));
      tr.appendChild(td(esc(r.fullName || "")));
      tr.appendChild(
        td(
          repo
            ? `<a href="${esc(repo)}" target="_blank" rel="noreferrer">${esc(repo)}</a>`
            : "<span class='small'>(trống)</span>"
        )
      );
      tr.appendChild(
        td(
          r.ok
            ? "<span style='color:#16a34a;font-weight:700'>OK</span>"
            : "<span style='color:#dc2626;font-weight:700'>LỖI</span>"
        )
      );
      tr.appendChild(td(esc(r.score == null ? "" : r.score)));
      tr.appendChild(td(esc(r.comment || "")));
      if (body) body.appendChild(tr);
    });
    if (wrap) wrap.style.display = "";
  }

  async function gaDownloadExcel(rows) {
    const statusEl = $("#ga-status");
    if (!Array.isArray(rows) || rows.length === 0) return;
    try {
      const fd = new FormData();
      fd.set("rows_json", JSON.stringify(rows));
      const r = await fetch("/api/group-a/export-xlsx", { method: "POST", body: fd });
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
      let name = "nhom_a_results.xlsx";
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

  async function postGroupA(ev) {
    ev.preventDefault();
    const btn = $("#ga-submit");
    setBusy(btn, true, "Đang chấm…");
    $("#ga-status").textContent = "";
    setLog("#ga-log", "", false);
    gaSetResults([]);
    try {
      const docsUrl = (
        $("#ga-docs-url") && $("#ga-docs-url").value
          ? String($("#ga-docs-url").value)
          : ""
      ).trim();
      const studentsText = (
        $("#ga-students") && $("#ga-students").value
          ? String($("#ga-students").value)
          : ""
      ).trim();
      if (!docsUrl) {
        setLog("#ga-log", "Thiếu link Google Docs đề bài.", true);
        return;
      }
      const st = gaParseStudents(studentsText);
      if (!st.length) {
        setLog("#ga-log", "Danh sách sinh viên rỗng hoặc sai định dạng.", true);
        return;
      }
      const repos = st.map((x) => (x.repo || "").trim()).join("\n");
      const fd = new FormData();
      fd.set("assignment_text", docsUrl);
      fd.set("submissions_text", repos);
      fd.set(
        "model",
        ($("#ga-model") && $("#ga-model").value ? String($("#ga-model").value) : "").trim()
      );
      // Chấm bài thường (không dùng prompt "bài tập đầu giờ")
      fd.set("github_token", "");
      const r = await fetch("/api/btvn/grade", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        setLog("#ga-log", formatApiErr(data.detail) || JSON.stringify(data), true);
        return;
      }
      const rr = (data && data.rows) || [];
      const out = [];
      for (let i = 0; i < st.length; i++) {
        const meta = st[i] || {};
        const row = rr[i] || {};
        const ok = !(row && (row.repo_error || row.ai_error));
        const score = row && row.score != null ? row.score : "";
        const comment = row && row.comment ? String(row.comment) : row && row.repo_error ? String(row.repo_error) : "";
        out.push({
          studentCode: meta.studentCode || "",
          fullName: meta.fullName || "",
          repo: meta.repo || "",
          assignment: docsUrl,
          model: ($("#ga-model") && $("#ga-model").value ? String($("#ga-model").value) : "").trim(),
          ok,
          score,
          comment,
        });
      }
      // /api/btvn/grade không trả log; hiển thị lỗi tổng nếu có
      setLog("#ga-log", "", false);
      gaSetResults(out);
      gaCtx.last_export_rows = out;
      const dlBtn = $("#ga-download");
      if (dlBtn) dlBtn.disabled = !(Array.isArray(out) && out.length > 0);
      $("#ga-status").textContent = "Xong.";
      const autoExport = $("#ga-export") && $("#ga-export").checked;
      if (autoExport && Array.isArray(out) && out.length > 0) {
        await gaDownloadExcel(out);
      }
    } catch (e) {
      setLog("#ga-log", String(e), true);
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

  let grTableCache = { urls: [], txs: [] };

  function snapshotGroupLinkRows() {
    const tbody = $("#gr-links-tbody");
    if (!tbody) return { urls: [], txs: [] };
    const urls = [];
    const txs = [];
    tbody.querySelectorAll("tr").forEach((tr) => {
      const yi = tr.querySelector("input.gr-row-yt");
      const ti = tr.querySelector("textarea.gr-row-tx");
      if (yi && ti) {
        urls.push(yi.value);
        txs.push(ti.value);
      }
    });
    return { urls, txs };
  }

  function rebuildGroupLinksTable(fileList) {
    const tbody = $("#gr-links-tbody");
    if (!tbody) return;
    const prev = grTableCache;
    tbody.replaceChildren();
    const n = fileList && fileList.length ? fileList.length : 0;
    if (n === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 4;
      td.className = "hint";
      td.style.padding = "12px";
      td.textContent =
        "Chọn một hoặc nhiều file báo cáo — bảng sẽ hiện một dòng link + transcript cho mỗi file.";
      tr.appendChild(td);
      tbody.appendChild(tr);
      grTableCache = { urls: [], txs: [] };
      return;
    }
    const urls = [];
    const txs = [];
    for (let i = 0; i < n; i++) {
      const u = i < prev.urls.length ? prev.urls[i] : "";
      const x = i < prev.txs.length ? prev.txs[i] : "";
      urls.push(u);
      txs.push(x);
      const tr = document.createElement("tr");
      const tdN = document.createElement("td");
      tdN.textContent = String(i + 1);
      const tdF = document.createElement("td");
      tdF.textContent = (fileList[i] && fileList[i].name) || "";
      const tdU = document.createElement("td");
      const inp = document.createElement("input");
      inp.type = "text";
      inp.className = "gr-row-yt";
      inp.autocomplete = "off";
      inp.placeholder = "https://… (để trống nếu chỉ điền transcript)";
      inp.value = u;
      tdU.appendChild(inp);
      const tdT = document.createElement("td");
      const ta = document.createElement("textarea");
      ta.className = "gr-row-tx";
      ta.rows = 4;
      ta.placeholder = "Transcript hoặc ghi chú…";
      ta.value = x;
      tdT.appendChild(ta);
      tr.appendChild(tdN);
      tr.appendChild(tdF);
      tr.appendChild(tdU);
      tr.appendChild(tdT);
      tbody.appendChild(tr);
    }
    grTableCache = { urls, txs };
  }

  function onGroupFilesPick(ev) {
    const inp = ev && ev.target ? ev.target : $("#gr-report-files");
    if (!inp || inp.id !== "gr-report-files") return;
    grTableCache = snapshotGroupLinkRows();
    rebuildGroupLinksTable(inp.files);
  }

  function parseGroupActivityBlocks(text) {
    const t = (text || "").trim();
    if (!t) return [];
    const parts = t.split(/\n\n=== /);
    const rows = [];
    for (let i = 0; i < parts.length; i++) {
      const p = i === 0 ? parts[i] : "=== " + parts[i];
      const m = p.match(/^===\s*(\d+)\.\s*(.+?)\s*===\s*\r?\n([\s\S]*)$/);
      if (m) {
        rows.push({ stt: m[1].trim(), file: m[2].trim(), body: m[3].trim() });
      } else {
        rows.push({ stt: String(rows.length + 1), file: "", body: p.trim() });
      }
    }
    return rows;
  }

  function grAttendanceLabel(att) {
    const a = String(att || "").toLowerCase();
    if (a === "present") return { text: "Có mặt", cls: "gr-att gr-att-present" };
    if (a === "absent") return { text: "Vắng", cls: "gr-att gr-att-absent" };
    return { text: "Chưa rõ", cls: "gr-att gr-att-unknown" };
  }

  function buildGroupMembersCell(members) {
    const td = document.createElement("td");
    const list = Array.isArray(members) ? members : [];
    if (!list.length) {
      const span = document.createElement("span");
      span.className = "gr-members-empty";
      span.textContent = "(Báo cáo không liệt kê thành viên)";
      td.appendChild(span);
      return td;
    }
    const table = document.createElement("table");
    table.className = "gr-members-mini";
    table.setAttribute("aria-label", "Thành viên từ báo cáo");
    const thead = document.createElement("thead");
    const hr = document.createElement("tr");
    ["Thành viên", "Buổi họp", "Ghi chú"].forEach((h) => {
      const th = document.createElement("th");
      th.textContent = h;
      hr.appendChild(th);
    });
    thead.appendChild(hr);
    table.appendChild(thead);
    const tb = document.createElement("tbody");
    list.forEach((m) => {
      if (!m || typeof m !== "object") return;
      const name = String(m.name || "").trim();
      if (!name) return;
      const tr = document.createElement("tr");
      const tdN = document.createElement("td");
      tdN.textContent = name;
      const tdA = document.createElement("td");
      const lab = grAttendanceLabel(m.attendance);
      const badge = document.createElement("span");
      badge.className = lab.cls;
      badge.textContent = lab.text;
      tdA.appendChild(badge);
      const tdNote = document.createElement("td");
      tdNote.textContent = String(m.note || "").trim() || "—";
      tr.appendChild(tdN);
      tr.appendChild(tdA);
      tr.appendChild(tdNote);
      tb.appendChild(tr);
    });
    table.appendChild(tb);
    td.appendChild(table);
    return td;
  }

  function showGroupSuccessTable(rows) {
    const wrap = $("#gr-results-wrap");
    const pre = $("#gr-log");
    const tbody = $("#gr-results-tbody");
    if (pre) {
      pre.textContent = "";
      pre.classList.remove("error");
      pre.style.display = "none";
    }
    if (!tbody || !wrap) return;
    tbody.replaceChildren();
    for (const row of rows) {
      const tr = document.createElement("tr");
      const td1 = document.createElement("td");
      td1.textContent = row.stt != null ? String(row.stt) : "";
      const td2 = document.createElement("td");
      td2.textContent = row.file || "";
      const tdMembers = buildGroupMembersCell(row.members);
      const tdComment = document.createElement("td");
      tdComment.className = "gr-result-body";
      tdComment.textContent = row.comment || row.body || "";
      tr.appendChild(td1);
      tr.appendChild(td2);
      tr.appendChild(tdMembers);
      tr.appendChild(tdComment);
      tbody.appendChild(tr);
    }
    wrap.style.display = "";
  }

  function showGroupErrorOutput(msg) {
    const wrap = $("#gr-results-wrap");
    const pre = $("#gr-log");
    if (wrap) wrap.style.display = "none";
    if (pre) pre.style.display = "";
    setLog("#gr-log", msg, true);
  }

  async function postGroup(ev) {
    ev.preventDefault();
    const btn = $("#gr-submit");
    setBusy(btn, true, "Đang chấm…");
    $("#gr-status").textContent = "";
    const pre = $("#gr-log");
    const wrap = $("#gr-results-wrap");
    if (pre) {
      pre.style.display = "";
      pre.classList.remove("error");
      pre.textContent = "";
    }
    if (wrap) wrap.style.display = "none";
    try {
      const fileInput = $("#gr-report-files");
      const files = fileInput && fileInput.files ? fileInput.files : null;
      if (!files || files.length === 0) {
        showGroupErrorOutput("Chọn ít nhất một file báo cáo.");
        return;
      }
      const { urls: linesYt, txs: linesTx } = snapshotGroupLinkRows();
      if (linesYt.length !== files.length || linesTx.length !== files.length) {
        showGroupErrorOutput("Bảng link/transcript không khớp số file — chọn lại file báo cáo.");
        return;
      }
      for (let i = 0; i < files.length; i++) {
        const y = (linesYt[i] || "").trim();
        const t = (linesTx[i] || "").trim();
        if (!y && !t) {
          showGroupErrorOutput(`Dòng ${i + 1}: cần ít nhất link YouTube hoặc transcript/ghi chú.`);
          return;
        }
      }
      const fd = new FormData();
      fd.set("model", ($("#gr-model") && $("#gr-model").value ? String($("#gr-model").value) : "").trim());
      for (let i = 0; i < files.length; i++) {
        fd.append("youtube_url_row", (linesYt[i] || "").trim());
        fd.append("video_transcript_row", linesTx[i] || "");
      }
      for (let i = 0; i < files.length; i++) {
        fd.append("report_files", files[i]);
      }
      const r = await fetch("/api/group-activity", { method: "POST", body: fd });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        showGroupErrorOutput(formatApiErr(data.detail) || JSON.stringify(data));
        return;
      }
      const raw = await r.text().catch(() => "");
      let rows = [];
      try {
        const data = JSON.parse(raw);
        if (data && Array.isArray(data.rows)) rows = data.rows;
      } catch {
        rows = parseGroupActivityBlocks(raw).map((x) => ({
          stt: x.stt,
          file: x.file,
          comment: x.body,
          members: [],
        }));
      }
      if (rows.length) {
        showGroupSuccessTable(rows);
      } else {
        showGroupErrorOutput("(Phản hồi rỗng)");
        return;
      }
      $("#gr-status").textContent = "Xong.";
    } catch (e) {
      showGroupErrorOutput(String(e));
    } finally {
      setBusy(btn, false);
    }
  }

  let _cfLastPlain = "";
  let _cfLastHtml = "";

  async function runFormatCode() {
    const btn = $("#cf-submit");
    const statusEl = $("#cf-status");
    const outWrap = $("#cf-out-wrap");
    const outEl = $("#cf-output");
    const copyBtn = $("#cf-copy");
    const code = ($("#cf-input") && $("#cf-input").value) || "";
    const lang = ($("#cf-lang") && $("#cf-lang").value) || "python";
    if (!code.trim()) {
      if (statusEl) statusEl.textContent = "Dán code vào ô nhập.";
      return;
    }
    setBusy(btn, true, "Đang format…");
    if (statusEl) {
      statusEl.textContent = "";
      statusEl.classList.add("run");
    }
    if (copyBtn) copyBtn.disabled = true;
    try {
      const r = await fetch("/api/format-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, lang }),
      });
      const data = await r.json();
      if (!r.ok) {
        if (statusEl) statusEl.textContent = formatApiErr(data.detail) || "Lỗi format code.";
        return;
      }
      _cfLastPlain = data.plain || "";
      _cfLastHtml = data.html || "";
      if (outEl) outEl.innerHTML = _cfLastHtml;
      if (outWrap) outWrap.hidden = false;
      if (copyBtn) copyBtn.disabled = !_cfLastPlain;
      if (statusEl) statusEl.textContent = "Xong — có thể copy.";
    } catch (e) {
      if (statusEl) statusEl.textContent = String(e);
    } finally {
      if (statusEl) statusEl.classList.remove("run");
      setBusy(btn, false);
    }
  }

  async function copyFormatCode() {
    const statusEl = $("#cf-status");
    if (!_cfLastPlain) {
      if (statusEl) statusEl.textContent = "Chưa có kết quả — bấm Format trước.";
      return;
    }
    const htmlDoc =
      '<!DOCTYPE html><html><body style="margin:0;background:#1E1E1E">' +
      _cfLastHtml +
      "</body></html>";
    try {
      if (navigator.clipboard && window.ClipboardItem) {
        await navigator.clipboard.write([
          new ClipboardItem({
            "text/plain": new Blob([_cfLastPlain], { type: "text/plain" }),
            "text/html": new Blob([htmlDoc], { type: "text/html" }),
          }),
        ]);
      } else {
        await navigator.clipboard.writeText(_cfLastPlain);
      }
      if (statusEl) statusEl.textContent = "Đã copy.";
    } catch (e) {
      if (statusEl) statusEl.textContent = "Copy thất bại: " + String(e);
    }
  }

  function init() {
    tabsSetup();
    $("#form-grade").addEventListener("submit", postGrade);
    $("#form-quiz").addEventListener("submit", postQuiz);
    $("#form-reading").addEventListener("submit", postReading);
    const cfSubmit = $("#cf-submit");
    if (cfSubmit) cfSubmit.addEventListener("click", runFormatCode);
    const cfCopy = $("#cf-copy");
    if (cfCopy) cfCopy.addEventListener("click", copyFormatCode);
    const fga = $("#form-group-a");
    if (fga) fga.addEventListener("submit", postGroupA);
    const gaDl = $("#ga-download");
    if (gaDl) {
      gaDl.addEventListener("click", async () => {
        const rows = (gaCtx && gaCtx.last_export_rows) || [];
        await gaDownloadExcel(rows);
      });
    }
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
    const gri = $("#gr-report-files");
    if (gri) {
      grTableCache = { urls: [], txs: [] };
      gri.addEventListener("change", onGroupFilesPick);
      rebuildGroupLinksTable(gri.files);
    }
    const fb = $("#form-btvn");
    if (fb) fb.addEventListener("submit", postBtvn);
    const bStudentsBody = $("#b-students-body");
    if (bStudentsBody) {
      bStudentsBody.addEventListener("change", (ev) => {
        if (ev.target && ev.target.classList && ev.target.classList.contains("b-stu-tier-select")) {
          btvnUpdatePassRuleHint();
        }
      });
    }
    ["b-min-completed", "b-ratio-ok", "b-score-threshold", "b-student-tiers"].forEach((id) => {
      const el = $("#" + id);
      if (el) {
        el.addEventListener("input", btvnUpdatePassRuleHint);
        el.addEventListener("paste", () => setTimeout(btvnUpdatePassRuleHint, 0));
      }
    });
    btvnUpdatePassRuleHint();
    const bLoad = $("#b-rk-load");
    if (bLoad) bLoad.addEventListener("click", btvnLoadSystems);
    const bSys = $("#b-rk-system");
    if (bSys) bSys.addEventListener("change", btvnLoadClassesForSystem);
    const bClass = $("#b-rk-class");
    if (bClass) bClass.addEventListener("change", btvnLoadCoursesForClass);
    const bCourse = $("#b-rk-course");
    if (bCourse) bCourse.addEventListener("change", btvnLoadSessionsForCourse);
    const bSess = $("#b-rk-session");
    if (bSess) bSess.addEventListener("change", btvnLoadSession);
    const bLoadStudentsBtn = $("#b-load-students");
    if (bLoadStudentsBtn) bLoadStudentsBtn.addEventListener("click", btvnLoadStudents);
    document.addEventListener("click", async (ev) => {
      const t = ev.target && ev.target.closest && ev.target.closest("button.b-stu-view");
      if (!t) return;
      ev.preventDefault();
      const sid = t.getAttribute("data-student-id") || "";
      if (!String(sid).trim()) return;
      try {
        btvnShowModal("Đang tải bài nộp...");
        const items = await btvnFetchStudentExercises(sid);
        if (!items || items.length === 0) {
          btvnShowModal("Không có bài nộp (exercise) cho sinh viên này trong session.");
          return;
        }
        btvnEnsureModal();
        btvnRenderStudentExercisesModal({ studentId: sid, exercises: items });
        const modal = $("#btvn-modal");
        if (modal) modal.style.display = "block";
      } catch (e) {
        btvnShowModal(String(e));
      }
    });
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
    const hgDocsManual = $("#hg-docs-manual");
    if (hgDocsManual)
      hgDocsManual.addEventListener("change", () => {
        const v = ($("#hg-schedule") && $("#hg-schedule").value) || "";
        if (String(v).trim()) hgLoadScheduleDetail();
      });
    const hgBody = $("#hg-body");
    if (hgBody)
      hgBody.addEventListener("change", (ev) => {
        if (ev.target && ev.target.classList && ev.target.classList.contains("hg-exam-pick")) {
          hgUpdateRowNoteFromSelect(ev.target);
        }
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

      const deso = /deso\s*0*([0-9]{1,3})/i.exec(t);
      if (deso) {
        const n = parseInt(deso[1], 10);
        if (Number.isFinite(n) && n > 0 && n <= 99) return n;
      }
      const de = /(?:^|[_-])de\s*0*([0-9]{1,3})(?=[_-]|$)/i.exec(t);
      if (de) {
        const n = parseInt(de[1], 10);
        if (Number.isFinite(n) && n > 0 && n <= 99) return n;
      }

      // Mục tiêu: ưu tiên mã đề dạng _003_... hơn số ngày/tháng (09-17) hoặc giờ (_09).
      // Thu thập mọi nhóm số 1–3 chữ số được phân tách bởi _ hoặc -.
      const reSeg = /(?:^|[_-])0*([0-9]{1,3})(?=[_-]|$)/g;
      const hits = [];
      let mm;
      while ((mm = reSeg.exec(t))) {
        const raw = String(mm[1] || "");
        const n = parseInt(raw, 10);
        if (!Number.isFinite(n) || n <= 0 || n > 999) continue;
        hits.push({ n, raw, idx: mm.index });
      }
      if (!hits.length) {
        // fallback rất lỏng: số ở cuối chuỗi (vd. ...De02)
        const tailNum = /([0-9]{1,3})$/.exec(t);
        if (!tailNum) return null;
        const n = parseInt(tailNum[1], 10);
        if (!Number.isFinite(n) || n <= 0 || n > 999) return null;
        return n;
      }

      function scoreHit(h) {
        let score = 0;
        // Ưu tiên 3 chữ số (003) vì thường là mã đề.
        if (String(h.raw || "").length >= 3) score += 120;
        // Mã đề thường nhỏ (1–50).
        if (h.n >= 1 && h.n <= 50) score += 60;
        if (h.n >= 1 && h.n <= 30) score += 20;
        // Tránh picking các số nhỏ nhưng nằm ở cuối (hay là phút/giờ/ngày) bằng cách ưu tiên xuất hiện sớm hơn.
        score += Math.max(0, 30 - Math.min(30, h.idx));
        return score;
      }

      hits.sort((a, b) => scoreHit(b) - scoreHit(a));
      return hits[0].n;
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
  const hgRepoCodeCache = new Map();

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
    let out = s
      .split(/\s+/)
      .join(" ")
      .replace(/mini\s*project\s*\(chỉ\s*có\/không\)\s*:\s*[^\n.?!]*[.?!]?/giu, "")
      .replace(/\bbài\s*tập\s*đầu\s*giờ\b/giu, "Bài thi")
      // Chỉ bỏ các cụm "báo cáo" cố định để tránh cắt cụt câu hợp lệ.
      .replace(/\bkh[oô]ng\s+c[oó]\s+b[aá]o\s*c[aá]o\s+k[èe]m\s+theo\b[.?!]?/giu, "")
      .replace(/\bthi[eế]u\s+b[aá]o\s*c[aá]o\b[.?!]?/giu, "")
      .replace(/\s{2,}/g, " ")
      .trim();
    return out;
  }

  function hgSanitizeHackathonLog(raw) {
    return String(raw || "")
      .replace(/^.*mini\s*project\s*\(chỉ\s*có\/không\)\s*:.*$/gimu, "")
      .replace(/\bbài\s*tập\s*đầu\s*giờ\b/giu, "Bài thi");
  }

  function hgManualDocsMap() {
    const el = $("#hg-docs-manual");
    const txt = (el && el.value) || "";
    const out = {};
    txt.split(/\r?\n/).forEach((ln) => {
      const s = String(ln || "").trim();
      if (!s || s.startsWith("#")) return;
      const m = /^\s*0*([0-9]{1,3})\s*[:=]\s*(https?:\/\/\S+)\s*$/i.exec(s);
      if (!m) return;
      const k = String(parseInt(m[1], 10)).padStart(2, "0");
      const u = String(m[2] || "").trim();
      if (u) out[k] = u;
    });
    return out;
  }

  function hgMergedDocs() {
    const base = ((hgCtx && hgCtx.docs) || {});
    return { ...base, ...hgManualDocsMap() };
  }

  function hgExamDocKeys(docsMap) {
    return Object.keys(docsMap || {}).sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
  }

  function hgExamSelectHtml(idx, autoKey, docsMap) {
    const keys = hgExamDocKeys(docsMap);
    const ak = autoKey ? String(autoKey).padStart(2, "0") : "";
    let html = `<select class="hg-exam-pick" data-idx="${idx}" title="Chọn mã đề">`;
    html += `<option value="">${ak ? "(Tự động / đổi)" : "— Chọn đề —"}</option>`;
    keys.forEach((k) => {
      const sel = k === ak ? " selected" : "";
      html += `<option value="${escapeHtml(k)}"${sel}>Đề ${escapeHtml(k)}</option>`;
    });
    html += "</select>";
    if (ak && docsMap[ak]) {
      html += ` <a href="${escapeHtml(docsMap[ak])}" target="_blank" rel="noreferrer" class="small">Docs</a>`;
    }
    return html;
  }

  function hgRowNote(gitRaw, examKey, docUrl) {
    if (!gitRaw) return "Không nộp bài.";
    if (examKey && docUrl) return "";
    if (examKey && !docUrl) return "Đã chọn đề nhưng chưa có link Docs.";
    return "Chưa nhận mã đề — chọn cột Đề hoặc kiểm tra tên repo.";
  }

  function hgUpdateRowNoteFromSelect(sel) {
    if (!sel || !sel.classList.contains("hg-exam-pick")) return;
    const tr = sel.closest("tr");
    if (!tr || !tr.cells || tr.cells.length < 6) return;
    const idx = parseInt(sel.getAttribute("data-idx") || "0", 10);
    const row = (hgCtx.visible || [])[idx];
    const gitRaw = row ? String(row.link || "").trim() : "";
    const docsMap = hgMergedDocs();
    const manual = String(sel.value || "").trim();
    const key = manual || (extractExamCodeFromRepoLink(gitRaw) != null ? String(extractExamCodeFromRepoLink(gitRaw)).padStart(2, "0") : "");
    tr.cells[5].textContent = hgRowNote(gitRaw, key, key && docsMap[key] ? docsMap[key] : "");
  }

  async function hgExamCodeForRow(idx, gitRaw, docsMap) {
    const sel = document.querySelector(`select.hg-exam-pick[data-idx="${String(idx)}"]`);
    const manual = sel && sel.value ? String(sel.value).trim() : "";
    if (manual) {
      const n = parseInt(manual, 10);
      return Number.isFinite(n) && n > 0 ? n : null;
    }
    if (!gitRaw) return null;
    return hgResolveExamCodeFromGithub(gitRaw, docsMap);
  }

  async function hgResolveExamCodeFromGithub(gitUrl, docsMap) {
    const k = String(gitUrl || "").trim();
    if (!k) return null;
    if (hgRepoCodeCache.has(k)) return hgRepoCodeCache.get(k);
    let out = extractExamCodeFromRepoLink(k);
    const keyFromUrl = out == null ? "" : String(out).padStart(2, "0");
    const hasDocForUrlCode = !!(docsMap && keyFromUrl && docsMap[keyFromUrl]);
    if (out != null && hasDocForUrlCode) {
      hgRepoCodeCache.set(k, out);
      return out;
    }
    try {
      const fd = new FormData();
      fd.set("repo_url", k);
      const r = await fetch("/api/github/exam-code", { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (r.ok) {
        const c = parseInt(String(data && data.code != null ? data.code : ""), 10);
        out = Number.isFinite(c) && c > 0 ? c : null;
      }
    } catch {}
    hgRepoCodeCache.set(k, out);
    return out;
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
        const merged = hgMergedDocs();
        const keys = Object.keys(merged || {}).sort();
        if (!keys.length) {
          docsEl.textContent = "(Không tìm thấy link đề trong test.)";
        } else {
          docsEl.innerHTML =
            keys
              .map((k) => {
                const u = merged[k];
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
        const docsMap = hgMergedDocs();
        const gitRaw = String(x.link || "").trim();
        const git = normalizeGithubRepo(gitRaw);
        const code = extractExamCodeFromRepoLink(gitRaw);
        const key = code == null ? "" : String(code).padStart(2, "0");
        const docUrl = key && docsMap[key] ? docsMap[key] : "";
        const skipZeroOverwrite = !!includeGraded && Number(x.point) === 0;
        let note = "";
        if (skipZeroOverwrite) note = "Đã có điểm 0 (bỏ qua theo rule không đè).";
        else note = hgRowNote(gitRaw, key, docUrl);

        const tr = document.createElement("tr");
        const td = (html) => {
          const c = document.createElement("td");
          c.style.padding = "10px";
          c.style.borderBottom = "1px solid #e5e7eb";
          c.innerHTML = html;
          return c;
        };
        const checked = !skipZeroOverwrite && !!gitRaw;
        tr.appendChild(td(`<input type="checkbox" class="hg-row" data-idx="${idx}" ${checked ? "checked" : ""} />`));
        tr.appendChild(td(escapeHtml(x.studentCode || "")));
        tr.appendChild(td(escapeHtml(x.fullName || "")));
        tr.appendChild(td(git ? `<a href="${escapeHtml(git)}" target="_blank" rel="noreferrer">${escapeHtml(git)}</a>` : "<span class='small'>(trống)</span>"));
        tr.appendChild(td(hgExamSelectHtml(idx, key, docsMap)));
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
    const docs = hgMergedDocs();
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
    const includeGraded = $("#hg-include-graded") && $("#hg-include-graded").checked;
    for (const c of checks) {
      if (!c.checked) continue;
      if (limitN > 0 && picked >= limitN) continue;
      const idx = parseInt(c.getAttribute("data-idx") || "0", 10);
      const x = rows[idx];
      if (!x) continue;
      if (includeGraded && Number(x.point) === 0) continue; // không đè các bài đã 0 điểm
      const gitRaw = String(x.link || "").trim();
      const git = normalizeGithubRepo(gitRaw);
      const code = gitRaw ? await hgExamCodeForRow(idx, gitRaw, docs) : null;
      const key = code == null ? "" : String(code).padStart(2, "0");
      const docUrl = key && docs[key] ? docs[key] : "";
      const isMissing = !gitRaw;
      const isInvalidExamCode = !isMissing && (!key || !docUrl);
      if (!isMissing && !git) continue;
      selected.push({
        docUrl,
        git,
        studentCode: x.studentCode,
        fullName: x.fullName,
        resultTestId: x.id,
        isMissing,
        isInvalidExamCode,
      });
      picked += 1;
    }
    if (selected.length === 0) {
      if (statusEl) statusEl.textContent = "Không có dòng hợp lệ để chấm.";
      return;
    }
    const missingSubs = selected.filter((x) => x.isMissing);
    const invalidExamSubs = selected.filter((x) => !x.isMissing && x.isInvalidExamCode);
    const normalSubs = selected.filter((x) => !x.isMissing && !x.isInvalidExamCode);
    const byDoc = new Map();
    normalSubs.forEach((x) => {
      if (!byDoc.has(x.docUrl)) byDoc.set(x.docUrl, []);
      byDoc.get(x.docUrl).push(x);
    });
    const parUi = parseInt((($("#hg-par") && $("#hg-par").value) || "2").toString(), 10);
    const PAR = Number.isFinite(parUi) && parUi > 0 ? Math.min(4, parUi) : 2;
    if (statusEl) {
      statusEl.textContent = `Đang xử lý ${selected.length} bài (nộp hợp lệ: ${normalSubs.length}, không nộp: ${missingSubs.length}, sai mã đề: ${invalidExamSubs.length})…`;
    }
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
    invalidExamSubs.forEach((meta) => {
      exportRows.push({
        resultTestId: meta.resultTestId || "",
        studentCode: meta.studentCode || "",
        fullName: meta.fullName || "",
        repo: meta.git || "",
        assignment: "",
        ok: true,
        score: 0,
        comment: "Nộp sai tên, không rõ mã đề.",
        repo_error: "Nộp sai tên, không rõ mã đề.",
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
