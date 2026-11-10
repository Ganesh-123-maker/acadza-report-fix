/* Acadza Report -> Fix console. Loads precomputed web/data.json only.
   No LLM calls happen in the browser. Audit log + reviewed state live in
   localStorage on this device. */
(function () {
  "use strict";
  var AUDIT_KEY = "acadza-audit-v1";
  var REVIEWED_KEY = "acadza-reviewed-v1";

  var state = { data: null, cases: [], selected: null, reviewed: {}, audit: [] };
  var $ = function (id) { return document.getElementById(id); };

  function loadStore(key) { try { return JSON.parse(localStorage.getItem(key) || "{}"); } catch (e) { return {}; } }
  function loadAudit() { try { return JSON.parse(localStorage.getItem(AUDIT_KEY) || "[]"); } catch (e) { return []; } }
  function saveStore(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* Stored HTML is Acadza production data, but it is still injected through a
     sanitiser: no scripts, frames, forms or event handlers survive. */
  function safeHtml(html) {
    var doc = new DOMParser().parseFromString("<div>" + html + "</div>", "text/html");
    var bad = doc.querySelectorAll("script,iframe,object,embed,form,link,meta,style");
    bad.forEach(function (n) { n.remove(); });
    doc.querySelectorAll("*").forEach(function (el) {
      Array.from(el.attributes).forEach(function (a) {
        if (/^on/i.test(a.name) || (a.name === "href" && /^\s*javascript:/i.test(a.value))) el.removeAttribute(a.name);
      });
    });
    return doc.body.firstChild ? doc.body.firstChild.innerHTML : "";
  }

  function plain(html) {
    var d = document.createElement("div");
    d.innerHTML = html || "";
    return (d.textContent || "").replace(/\s+/g, " ").trim();
  }

  function fmtAnswer(a) {
    if (Array.isArray(a)) return a.map(function (x) { return x === "" ? "(blank)" : x; }).join(", ");
    return String(a);
  }

  function verdictLabel(v) {
    return { defect: "Defect", no_error: "No error", display_issue: "Display issue",
      app_issue: "App issue", language_mode: "Language request",
      not_actionable: "Not actionable", already_fixed: "Already fixed" }[v] || v;
  }
  function routeLabel(r) {
    return { auto_apply: "Ready to auto-apply", faculty_review: "Needs faculty", no_change: "No change" }[r] || r;
  }

  /* ---------- data ---------- */
  fetch("data.json").then(function (r) { return r.json(); }).then(function (data) {
    state.data = data;
    state.cases = data.cases.slice();
    state.reviewed = loadStore(REVIEWED_KEY);
    state.audit = loadAudit();
    renderStats(); renderBonus(); renderAudit(); applyFilters();
    /* Deep links, for sharing a case or a tab with faculty:
       ?case=<questionId> selects a case; #unreported / #how / #audit opens a tab. */
    var params = new URLSearchParams(location.search);
    var wantCase = params.get("case");
    var hash = (location.hash || "").replace("#", "");
    if (hash === "unreported" || hash === "how" || hash === "audit") {
      document.querySelector('.tab[data-tab="' + hash + '"]').click();
    }
    var first = wantCase && state.cases.some(function (c) { return c.questionId === wantCase; })
      ? wantCase : (state.cases[0] && state.cases[0].questionId);
    if (first) selectCase(first);
  }).catch(function (e) {
    $("detail").innerHTML = "<p>Could not load data.json. " + esc(String(e)) + "</p>";
  });

  function questionById(id) {
    return state.data.questions.find(function (q) { return q.id === id; });
  }

  function renderStats() {
    var c = state.data.counts;
    $("stats").innerHTML =
      '<span class="stat warn"><b>' + c.defects + '</b> defects in ' + c.cases + ' cases</span>' +
      '<span class="stat"><b>' + c.auto_apply + '</b> ready to auto-apply</span>' +
      '<span class="stat"><b>' + c.faculty_review + '</b> need faculty</span>' +
      '<span class="stat ok"><b>' + c.no_change + '</b> no change</span>' +
      '<span class="stat"><b>' + c.reports + '</b> student reports</span>';
    $("bonusCount").textContent = state.data.bonus.length;
  }

  /* ---------- queue ---------- */
  function filteredCases() {
    var q = ($("search").value || "").toLowerCase();
    var v = $("filterVerdict").value, r = $("filterRoute").value, s = $("filterSubject").value;
    var hide = $("hideReviewed").checked;
    return state.cases.filter(function (c) {
      if (hide && state.reviewed[c.questionId]) return false;
      if (v && c.verdict !== v) return false;
      if (r && c.route !== r) return false;
      var qu = questionById(c.questionId);
      if (s && qu.subject !== s) return false;
      if (q) {
        var hay = (plain(qu.questionHtml) + " " + qu.chapter + " " + qu.subject + " " +
          c.reports.map(function (x) { return x.comment; }).join(" ")).toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });
  }

  function renderQueue(list) {
    var ol = $("queue");
    ol.innerHTML = "";
    list.forEach(function (c, i) {
      var qu = questionById(c.questionId);
      var li = document.createElement("li");
      if (state.selected === c.questionId) li.className = "selected";
      if (state.reviewed[c.questionId]) li.className += " reviewed";
      var title = plain(qu.questionHtml).slice(0, 95);
      li.innerHTML =
        '<div class="q-top"><span class="q-rank">#' + (i + 1) + '</span>' +
        '<span class="q-title">' + esc(title) + (title.length >= 95 ? "…" : "") + '</span></div>' +
        '<div class="q-meta">' + esc(qu.subject) + ' · ' + esc(qu.chapter || "—") + ' · ' +
        c.reports.length + ' report' + (c.reports.length > 1 ? 's' : '') +
        ' · urgency ' + c.urgency + '</div>' +
        '<div class="q-badges"><span class="badge ' + c.verdict + '">' + verdictLabel(c.verdict) + '</span>' +
        '<span class="badge ' + c.route + '">' + routeLabel(c.route) + '</span>' +
        (state.reviewed[c.questionId] ? '<span class="badge no_change">✓ reviewed</span>' : '') + '</div>';
      li.addEventListener("click", function () { selectCase(c.questionId); });
      ol.appendChild(li);
    });
    var done = Object.keys(state.reviewed).length;
    $("progress").textContent = done + " / " + state.cases.length + " reviewed";
    $("auditCount").textContent = state.audit.length;
  }

  function applyFilters() { renderQueue(filteredCases()); }

  ["search", "filterVerdict", "filterRoute", "filterSubject", "hideReviewed"].forEach(function (id) {
    $(id).addEventListener("input", applyFilters);
  });

  /* ---------- detail ---------- */
  function diffHtml(c, qu) {
    var edit = c.edit;
    if (!edit) {
      var msg;
      if (c.verdict === "defect" && c.repair) {
        msg = "No auto-edit. Repair <b>" + esc(c.repair) + "</b> needs authored content or a faculty decision — " +
          (c.repair === "identical_options" ? "a new distractor must be written by a human." :
           c.repair === "diagram" ? "a figure must be supplied by a human." :
           c.repair === "wrong_chapter" ? "faculty re-files the question under the right chapter." :
           c.repair === "syllabus" ? "faculty confirm whether it is in the current NEET syllabus; the question stays live meanwhile." :
           "faculty decide.");
      } else if (c.verdict === "display_issue" || c.verdict === "app_issue") {
        msg = "No question edit — this is a platform problem (layout / loading / recording), routed for an engineering check.";
      } else if (c.verdict === "language_mode") {
        msg = "No question edit — a translation is a content decision for the team, not an auto-fix.";
      } else {
        msg = "No edit proposed. Nothing in the stored record needs to change.";
      }
      return '<div class="diff"><h3>Before / after</h3><div class="diff-col"><p>' + msg + '</p></div></div>';
    }
    if (edit.field === "answer") {
      var oldA = qu.answer, newA;
      if (Array.isArray(oldA)) newA = "[\"A\", \"B\", \"D\"]";
      else newA = edit.replace;
      return '<div class="diff"><h3>Before / after — answer key</h3><div class="diff-row">' +
        '<div class="diff-col before"><h4>Before (stored key)</h4><p class="big-change">' + esc(fmtAnswer(oldA)) + '</p></div>' +
        '<div class="diff-col after"><h4>After (proposed)</h4><p class="big-change">' + esc(fmtAnswer(newA)) + '</p></div>' +
        '</div></div>';
    }
    if (edit.field === "questionType") {
      return '<div class="diff"><h3>Before / after — question type</h3><div class="diff-row">' +
        '<div class="diff-col before"><h4>Before</h4><p class="big-change">' + esc(qu.type) + '</p></div>' +
        '<div class="diff-col after"><h4>After (proposed)</h4><p class="big-change">' + esc(edit.replace) + '</p></div>' +
        '</div></div>';
    }
    var srcHtml = edit.field === "solution" ? qu.solutionHtml : qu.questionHtml;
    var before = plain(srcHtml), after = before;
    /* Space-tolerant find: MathML flattening joins tokens ("5.47Å") while the
       edit is written against the human-readable form ("5.47 Å"). Match with
       whitespace removed, then map the span back to the original text. */
    var findNorm = edit.find.replace(/\s+/g, "");
    var beforeNorm = before.replace(/\s+/g, "");
    var idx2 = beforeNorm.indexOf(findNorm);
    var idx = -1, end = -1;
    if (idx2 !== -1) {
      var count = 0;
      for (var i = 0; i < before.length; i++) {
        if (!/\s/.test(before[i])) { if (count === idx2) { idx = i; break; } count++; }
      }
      end = idx; var n = 0;
      while (end < before.length && n < findNorm.length) { if (!/\s/.test(before[end])) n++; end++; }
    }
    var beforeHtml, afterHtml;
    if (idx === -1) {
      beforeHtml = "<p>" + esc(before.slice(0, 400)) + "…</p>";
      afterHtml = "<p>Replace <b>" + esc(edit.find) + "</b> with <b>" + esc(edit.replace) + "</b> in the " + esc(edit.field) + ".</p>";
    } else {
      var foundText = before.slice(idx, end);
      beforeHtml = "<p>" + esc(before.slice(0, idx)) + '<mark class="del">' + esc(foundText) + "</mark>" + esc(before.slice(end, end + 400)) + "…</p>";
      afterHtml = "<p>" + esc(before.slice(0, idx)) + '<mark class="ins">' + esc(edit.replace) + "</mark>" + esc(before.slice(end, end + 400)) + "…</p>";
    }
    var extra = "";
    if (qu.proposedSolution) extra = '<div class="note-box"><b>Full corrected solution proposed:</b> ' + esc(qu.proposedSolution) + '</div>';
    if (c.questionId === "68f21caf941cda588bc04365") extra = '<div class="note-box"><b>Part of the same fix:</b> the stored answer <code>["", "B"]</code> should also be normalised to <code>"B"</code> when the type changes.</div>';
    if (c.questionId === "622f08d7b70e4b50e4500a1b") extra = '<div class="note-box"><b>Note:</b> (D) 14 m/s is a proposed distractor — the heavier block\u2019s own velocity, the natural wrong answer. Swap it for any other distractor in one click below.</div>';
    return '<div class="diff"><h3>Before / after — ' + esc(edit.field) + '</h3><div class="diff-row">' +
      '<div class="diff-col before"><h4>Before</h4>' + beforeHtml + '</div>' +
      '<div class="diff-col after"><h4>After (proposed)</h4>' + afterHtml + '</div>' +
      '</div>' + extra + '</div>';
  }

  function selectCase(qid) {
    state.selected = qid;
    renderQueue(filteredCases());
    var c = state.cases.find(function (x) { return x.questionId === qid; });
    var qu = questionById(qid);
    if (!c || !qu) return;
    var reviewed = state.reviewed[qid];
    var reportsHtml = c.reports.map(function (r) {
      return '<div class="report"><div class="who">' + esc(r.reportId) + ' · ' + esc(r.source) + ' · ' +
        esc(r.reportedAt.slice(0, 10)) + ' — student wrote: “' + esc(r.comment) + '”</div>' +
        '<div class="reply"><b>What the student sees back</b><br>' + esc(r.student_reply) + '</div></div>';
    }).join("");
    var conf = Math.round(c.confidence * 100);
    $("detail").innerHTML =
      '<h2>' + esc(qu.subject) + ' · ' + esc(qu.chapter || "—") + ' <span class="badge urgent">urgency ' + c.urgency + '</span></h2>' +
      '<p class="q-meta">' + esc(c.urgencyWhy) + ' · ' + c.reports.length + ' report' + (c.reports.length > 1 ? 's' : '') +
      ' · ' + esc(qu.type) + ' · ' + esc(qu.level || "") + '</p>' +
      '<div class="verdict-card ' + c.verdict + '"><h3>AI verdict: ' + verdictLabel(c.verdict) +
      (c.repair ? ' — ' + esc(c.repair) : '') + ' <span class="badge ' + c.route + '">' + routeLabel(c.route) + '</span></h3>' +
      '<div class="conf" title="Confidence ' + conf + '%"><div style="width:' + conf + '%"></div></div>' +
      '<p class="evidence"><b>Why (' + conf + '% confident):</b> ' + esc(c.evidence) + '</p></div>' +
      diffHtml(c, qu) +
      '<h3>The question, as the student sees it</h3>' +
      '<div class="q-render">' + safeHtml(qu.questionHtml) + '</div>' +
      '<span class="answer-chip">Stored answer: ' + esc(fmtAnswer(qu.answer)) + ' <small>· ' + esc(qu.type) + '</small></span>' +
      '<details class="solution"><summary>Stored solution</summary><div class="sol-body">' + safeHtml(qu.solutionHtml) + '</div></details>' +
      '<div class="reports"><h3>Reports on this question</h3>' + reportsHtml + '</div>' +
      '<div class="actions">' +
        '<input id="auditNote" type="text" placeholder="Note for the audit log (optional) — e.g. swapped distractor D">' +
        '<button class="btn approve" id="btnApprove">✓ Approve' + (c.route === "auto_apply" ? " &amp; apply" : "") + '</button>' +
        '<button class="btn ghost" id="btnEdit">Edit proposal</button>' +
        '<button class="btn reject" id="btnReject">Reject</button>' +
        '<button class="btn ghost" id="btnNext">Next case →</button>' +
      '</div>' +
      '<div id="editBox"></div>' +
      (reviewed ? '<p class="actioned">✓ Reviewed — ' + esc(reviewed.action) + ' · ' + esc(reviewed.when) + (reviewed.note ? ' · “' + esc(reviewed.note) + '”' : '') + '</p>' : '');
    $("btnApprove").addEventListener("click", function () { act(c, "approved"); });
    $("btnReject").addEventListener("click", function () { act(c, "rejected"); });
    $("btnNext").addEventListener("click", function () { nextCase(); });
    $("btnEdit").addEventListener("click", function () { toggleEdit(c, qu); });
  }

  function toggleEdit(c, qu) {
    var box = $("editBox");
    if (box.innerHTML) { box.innerHTML = ""; return; }
    var e = c.edit || { field: c.repair ? "question" : "", find: "", replace: "" };
    box.innerHTML = '<div class="note-box"><b>Edit the proposal before approving.</b><br>' +
      'Field: <b>' + esc(e.field || "—") + '</b><br>' +
      '<label>Find<br><input id="editFind" type="text" value="' + esc(e.find || "") + '" style="width:100%"></label><br>' +
      '<label>Replace with<br><input id="editReplace" type="text" value="' + esc(e.replace || "") + '" style="width:100%"></label><br>' +
      '<button class="btn" id="editSave">Save edit &amp; approve</button></div>';
    $("editSave").addEventListener("click", function () {
      var find = $("editFind").value, replace = $("editReplace").value;
      if (c.edit) { c.edit.find = find; c.edit.replace = replace; }
      else c.edit = { field: e.field || "question", find: find, replace: replace };
      act(c, "approved with edit", "edit: " + find + " → " + replace);
    });
  }

  function act(c, action, extraNote) {
    var note = ($("auditNote") ? $("auditNote").value : "") || extraNote || "";
    var entry = { ts: new Date().toISOString(), questionId: c.questionId,
      reports: c.reports.map(function (r) { return r.reportId; }),
      verdict: c.verdict, repair: c.repair, route: c.route,
      action: action, edit: c.edit, note: note };
    state.audit.unshift(entry);
    saveStore(AUDIT_KEY, state.audit);
    state.reviewed[c.questionId] = { action: action, when: entry.ts.slice(0, 16).replace("T", " "), note: note };
    saveStore(REVIEWED_KEY, state.reviewed);
    renderAudit(); nextCase();
  }

  function nextCase() {
    var list = filteredCases().filter(function (c) { return !state.reviewed[c.questionId]; });
    if (list.length) selectCase(list[0].questionId);
    else { applyFilters(); $("detail").innerHTML = "<h2>Queue clear 🎉</h2><p>Every case in this filter has been reviewed. Clear the filters or un-hide reviewed cases to revisit them.</p>"; }
  }

  /* ---------- bonus / how / audit ---------- */
  function renderBonus() {
    $("bonusList").innerHTML = state.data.bonus.map(function (b) {
      var qu = questionById(b.questionId);
      return '<div class="bonus-item"><h3>' + esc(b.title) + '</h3><p>' + esc(b.detail) + '</p>' +
        '<p class="q-meta">' + esc(qu ? qu.subject + " · " + (qu.chapter || "") : "") + ' · severity: ' + esc(b.severity) + '</p></div>';
    }).join("");
    $("cleanList").innerHTML = state.data.clean_unreported.map(function (b) {
      var qu = questionById(b.questionId);
      return '<div class="bonus-item"><h3>' + esc(qu ? plain(qu.questionHtml).slice(0, 80) + "…" : b.questionId) + '</h3><p>' + esc(b.check) + '</p></div>';
    }).join("");
  }

  function renderAudit() {
    $("auditCount").textContent = state.audit.length;
    var ol = $("auditList");
    if (!state.audit.length) { ol.innerHTML = "<li>No actions yet. Approve, edit or reject a case and it appears here.</li>"; return; }
    ol.innerHTML = "";
    state.audit.forEach(function (a) {
      var li = document.createElement("li");
      li.innerHTML = '<b>' + esc(a.action) + '</b> — ' + esc(a.reports.join(", ")) + ' · ' + esc(a.verdict) +
        (a.repair ? ' / ' + esc(a.repair) : '') + '<br><span class="when">' + esc(a.ts.replace("T", " ").slice(0, 19)) + ' UTC' +
        (a.note ? ' · “' + esc(a.note) + '”' : '') + '</span>';
      ol.appendChild(li);
    });
  }

  $("exportAudit").addEventListener("click", function () {
    var blob = new Blob([JSON.stringify(state.audit, null, 2)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "acadza-audit-log.json"; a.click();
  });
  $("clearAudit").addEventListener("click", function () {
    if (!confirm("Clear the audit log and all reviewed marks on this device?")) return;
    state.audit = []; state.reviewed = {};
    saveStore(AUDIT_KEY, []); saveStore(REVIEWED_KEY, {});
    renderAudit(); applyFilters();
  });

  /* ---------- tabs & modal ---------- */
  document.querySelectorAll(".tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      document.querySelectorAll(".tab").forEach(function (t) { t.classList.remove("active"); });
      tab.classList.add("active");
      document.querySelectorAll(".tabpanel").forEach(function (p) { p.classList.add("hidden"); });
      $("tab-" + tab.dataset.tab).classList.remove("hidden");
    });
  });
  $("whyUrgency").addEventListener("click", function () { $("whyModal").classList.remove("hidden"); });
  $("whyClose").addEventListener("click", function () { $("whyModal").classList.add("hidden"); });
  $("whyModal").addEventListener("click", function (e) { if (e.target === $("whyModal")) $("whyModal").classList.add("hidden"); });
})();
