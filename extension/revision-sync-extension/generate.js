/*
 * TB Task Revise Extractor — Markdown generator (universal).
 *
 * Works both in the browser (exposes `window.TBGen`) and in Node
 * (`module.exports`). Given ONE task object (an element of the Snorkel API's
 * `tasks[]` array) it returns a comprehensive Markdown report.
 *
 * Example source of the data (the route varies by portal screen):
 *   GET https://experts.snorkel-ai.com/api/v1/assignment/{project_id}/review-{task_type_id}
 *   -> { tasks: [ { task_documents: [ { submission_document: {...} } ], ... } ] }
 *
 * Sections mirror the platform's right-hand task panel. (The original
 * "Source API" and "Appendix" sections are intentionally omitted.)
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.TBGen = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function extractTasks(payload) {
    if (!payload) return [];
    if (Array.isArray(payload.tasks)) return payload.tasks;
    // Allow passing a single task directly.
    if (payload.task_documents) return [payload];
    return [];
  }

  // The task UUID, whichever shape the route used: {task_id:{id}} (TB2 review
  // queue), a plain task_id string, or an id/task_uuid field. "" when absent.
  function rawTaskId(task) {
    if (!task || typeof task !== "object") return "";
    var tid = task.task_id;
    if (tid && typeof tid === "object" && tid.id) return String(tid.id);
    if (typeof tid === "string" && tid) return tid;
    var keys = ["task_uuid", "uuid", "id"];
    for (var i = 0; i < keys.length; i++) {
      var v = task[keys[i]];
      if (typeof v === "string" && v) return v;
      if (v && typeof v === "object" && v.id) return String(v.id);
    }
    return "";
  }

  // Platform ids arrive either as plain strings or as {id: "..."}.
  function idOf(v) {
    if (v && typeof v === "object") return v.id || "";
    return v == null ? "" : v;
  }

  function taskId(task) {
    return rawTaskId(task) || "unknown-task";
  }

  // FormBlocks documents wrap each answer ({value: ...}); legacy ones don't.
  function unwrapField(v) {
    if (v && typeof v === "object" && !Array.isArray(v)) {
      var keys = ["value", "answer", "data"];
      for (var i = 0; i < keys.length; i++) {
        if (Object.prototype.hasOwnProperty.call(v, keys[i])) return v[keys[i]];
      }
    }
    return v;
  }

  function submissionDoc(task) {
    var sd;
    try {
      sd = task.task_documents[0].submission_document || {};
    } catch (e) {
      return {};
    }
    var out = {};
    for (var k in sd) out[k] = k === "upload_a_zip_file" ? sd[k] : unwrapField(sd[k]);
    // The upload field itself may be wrapped too; keep its filename reachable.
    var up = sd.upload_a_zip_file;
    if (up && typeof up === "object" && !up.filename) {
      var inner = unwrapField(up);
      if (inner && typeof inner === "object") out.upload_a_zip_file = inner;
    }
    return out;
  }

  function show(v) {
    if (v === undefined || v === null) return "";
    return typeof v === "object" ? JSON.stringify(v, null, 2) : String(v);
  }

  function stripHtml(s) {
    return String(s == null ? "" : s).replace(/<[^>]+>/g, "").trim();
  }

  // Built-in fallback for Error Categories (value -> human label), used when
  // the task's form_schema doesn't carry the options.
  var ERROR_CATEGORY_LABELS = {
    instruction_styling: "Instruction Styling",
    test_alignment: "Test Alignment/Coverage Issues",
    expose_answers: "Exposing Hints/Answers",
    oracle: "Oracle Solution Issues",
    test_build: "Test Build Issues",
    time_tests: "Time Based Tests",
    task_difficulty: "Task Difficulty",
    metadata: "Metadata Issues",
    milestone: "Milestones",
    internet: "Uses Internet",
    timeout: "Agent Timeout",
    language: "Wrong Coding Language",
    canary: "Canary Strings",
    rubric: "Rubric",
    test_dependency: "Test Dependency Location",
    pinning: "Pinning Issues",
    environment: "Environment",
    other: "Other"
  };

  // Read the Error Categories value->label map from the task's own form_schema
  // (falls back to the built-in table above for anything missing).
  function errorCategoryMap(task) {
    var map = {};
    try {
      (task.form_schema.sections || []).forEach(function (sec) {
        (sec.fields || []).forEach(function (f) {
          if (f.field === "multiselect-error-categories") {
            (f.options || []).forEach(function (o) { map[o.value] = stripHtml(o.label); });
          }
        });
      });
    } catch (e) {}
    return map;
  }

  // Collect every object that might hold review-form answers, in priority order.
  function collectAnswerDocs(task, sd) {
    var docs = [];
    function addDoc(d) { if (d && typeof d === "object" && !Array.isArray(d)) docs.push(d); }
    function fromWrapper(x) {
      if (!x || typeof x !== "object") return;
      if (Array.isArray(x)) { x.forEach(fromWrapper); return; }
      addDoc(x);
      ["submission_document", "review_document", "document", "answers", "form_data"].forEach(function (k) {
        if (x[k] && typeof x[k] === "object") addDoc(x[k]);
      });
    }
    addDoc(sd);
    fromWrapper(task.review_document);
    fromWrapper(task.review_documents);
    fromWrapper(task.user_reviews);
    addDoc(task); // top-level revision_notes / accept_notes
    return docs;
  }

  function pickField(docs, keys) {
    for (var i = 0; i < docs.length; i++) {
      for (var j = 0; j < keys.length; j++) {
        var v = docs[i][keys[j]];
        if (v !== undefined && v !== null && v !== "") return v;
      }
    }
    return undefined;
  }

  function normalizeErrorCategories(v, task) {
    if (!v) return [];
    var arr = Array.isArray(v) ? v : String(v).split(",");
    var map = errorCategoryMap(task);
    return arr.map(function (x) {
      var key = String(x).trim();
      if (!key) return null;
      return map[key] || ERROR_CATEGORY_LABELS[key] || key;
    }).filter(Boolean);
  }

  function fence(lines, title, body, lang) {
    lines.push("### " + title, "");
    lines.push("```" + (lang || ""));
    lines.push(typeof body === "string" ? body.replace(/\s+$/, "") : show(body));
    lines.push("```", "");
  }

  function code(v) {
    return "`" + (v && typeof v === "object" ? JSON.stringify(v) : show(v)) + "`";
  }

  function generateMarkdown(task) {
    var t = task || {};
    var sd = submissionDoc(t);
    var L = [];
    function w(s) {
      L.push(s === undefined ? "" : s);
    }
    function g(k, def) {
      var v = sd[k];
      return v === undefined || v === null ? (def === undefined ? "" : def) : v;
    }

    // -------- Header --------
    w("# Terminal Bench 2.0 — Task Revise Report");
    w("");
    w("> Comprehensive task information extracted from the Snorkel Experts task payload.");
    w("> This is the same data that populates the task's right-hand **Revise panel** " +
      "(Difficulty Explanation, Solution Explanation, checks, rubrics, agent runs, etc.).");
    w("");

    // -------- 1. Task Identity & Metadata --------
    w("## 1. Task Identity & Metadata");
    w("");
    w("| Field | Value |");
    w("|---|---|");
    w("| Project | " + code(t.project) + " |");
    w("| Project ID | " + code(idOf(t.project_id)) + " |");
    w("| Assignment ID | " + code(idOf(t.assignment_id)) + " |");
    w("| Task ID | " + code(rawTaskId(t)) + " |");
    w("| Submission ID | " + code(idOf(t.submission_id)) + " |");
    w("| Task category (stage) | " + code(t.task_category) + " |");
    w("| Submission task type | " + code(t.submission_task_type) + " |");
    w("| Review task type | " + code(t.task_type) + " |");
    w("| Form schema revision | " + code(t.form_schema_revision_id) + " |");
    w("| Skippable | " + code(t.is_skippable) + " |");
    w("| Further revisions allowed | " + code(t.further_revision_requests_allowed) + " |");
    w("| Expiry time | " + code(t.expiry_time) + " |");
    w("");
    w("### Task Classification (submission_document)");
    w("");
    var langs = g("task_languages", []);
    var langStr = Array.isArray(langs) ? langs.map(function (x) { return "`" + x + "`"; }).join(", ") : "";
    w("| Field | Value |");
    w("|---|---|");
    w("| Difficulty | **" + String(g("difficulty", "")).toUpperCase() + "** |");
    w("| Solvable | " + code(g("solvable")) + " |");
    w("| Task category | " + code(g("task_category")) + " |");
    w("| Task subcategories | " + code((g("task_subcategories", []).length ? JSON.stringify(g("task_subcategories")) : "[]")) + " |");
    w("| Task languages | " + langStr + " |");
    w("| Codebase size | " + code(g("codebase_size")) + " |");
    w("| Number of milestones | " + code(g("number_of_milestones")) + " |");
    w("| Submission AHT (min) | " + code(g("submission_aht")) + " |");
    w("| Uses approved canonical base image | " + code(g("boolean-7b32a")) + " |");
    w("| Used Task Gallery inspiration | " + code(g("boolean-46f6d")) + " |");
    w("| Send to reviewer | " + code(g("checkbox_send_to_reviewer")) + " |");
    w("| Generate rubrics | " + code(g("checkbox_evaluate_rubrics")) + " |");
    w("");

    // -------- 2. Submission Artifact --------
    w("## 2. Submission Artifact");
    w("");
    var u = g("upload_a_zip_file", {}) || {};
    w("| Field | Value |");
    w("|---|---|");
    w("| Filename | " + code(u.filename) + " |");
    w("| Uploaded at | " + code(u.uploadedAt) + " |");
    w("| S3 URI | " + code(u.s3Uri) + " |");
    w("| S3 key | " + code(u.s3Key) + " |");
    w("");
    w("- **Difficulty-check artifact:** " + code(g("difficulty_check_artifact_s3_key")));
    w("");

    // -------- 3. Reviewer Narrative Fields (Right Panel) --------
    w("## 3. Reviewer Narrative Fields (Right Panel)");
    w("");
    w("### Difficulty Explanation");
    w("");
    w("> *Describe in your own words why your task is challenging for humans and agents to solve.*");
    w("");
    w(g("difficulty_explanation"));
    w("");
    w("### Solution Explanation");
    w("");
    w(g("solution_explanation"));
    w("");
    w("### Verification Explanation");
    w("");
    w(g("verification_explanation"));
    w("");

    // -------- 4. Difficulty Check — Agent Simulation Summary --------
    w("## 4. Difficulty Check — Agent Simulation Summary");
    w("");
    if (!g("difficulty") && !Object.keys(g("all_agent_stats", {}) || {}).length) {
      w("Overall: **difficulty check not run** (see the summary and quality panel below).");
    } else {
      w("Overall: **Difficulty: " + String(g("difficulty", "")).toUpperCase() +
        " · Status: " + (g("solvable") ? "Solvable" : "Not solvable") + "**.");
    }
    w("");
    w("### Agent Performance");
    w("");
    w("| Agent | Accuracy | Runs | Successes | Timeouts | Other failures |");
    w("|---|---|---|---|---|---|");
    var stats = g("all_agent_stats", {}) || {};
    Object.keys(stats).forEach(function (name) {
      var s = stats[name] || {};
      w("| `" + name + "` | " + ((s.accuracy || 0) * 100).toFixed(1) + "% | " +
        (s.n_runs || 0) + " | " + (s.n_successes || 0) + " | " +
        (s.n_agent_timeouts || 0) + " | " + (s.n_other_failures || 0) + " |");
    });
    w("");
    w("### Per-Test Results (pass count across runs)");
    w("");
    var tr = g("test_results", {}) || {};
    var nruns = 0;
    Object.keys(tr).forEach(function (k) { nruns = Math.max(nruns, (tr[k] || []).length); });
    w("| Test | Passed / " + nruns + " |");
    w("|---|---|");
    Object.keys(tr).forEach(function (name) {
      var results = tr[name] || [];
      var npass = results.filter(function (r) { return r === "passed"; }).length;
      var flag = npass === results.length ? "✅" : "⚠️";
      w("| `" + name + "` | " + flag + " " + npass + " / " + results.length + " |");
    });
    w("");
    fence(L, "Full Difficulty-Check Text Summary", g("text_summary"), "");

    // -------- 5. Quality Check Results --------
    w("## 5. Quality Check Results");
    w("");
    fence(L, "Quality Check Summary", g("quality_check_summary"), "");

    fence(L, "Quality Check Logs", g("code_quality_check_results"), "");

    // Terminus 3 quality panel (5 axes). This is where the blocking
    // Sound Verifier / Coherent Contract findings live.
    w("## 5b. Quality Panel Judge Feedback");
    w("");
    var axes = g("quality_panel_degraded_blocking_axes", []) || [];
    if (axes.length) { w("Degraded blocking axes: " + code(axes)); w(""); }
    fence(L, "Quality Panel Judge Feedback", g("quality_panel_judge_feedback"), "");

    w("## 5c. Oracle / NOP Validation");
    w("");
    fence(L, "Oracle / NOP Validation", g("oracle_nop_validation"), "");
    fence(L, "Difficulty Check Full Logs", g("difficulty_check_full_logs"), "");

    // -------- 6. Test Quality Report --------
    w("## 6. Test Quality Report");
    w("");
    fence(L, "Test Quality Judge Report", g("test_quality_judge_report"), "");

    // -------- 7. TB 3.0 Rubric Feedback Checks --------
    w("## 7. TB 3.0 Rubric Feedback Checks");
    w("");
    fence(L, "TB 3.0 Rubric Feedback Checks", g("tb_3_rubric_feedback_checks"), "");

    // -------- 8. Agent Review Report --------
    w("## 8. Agent Review Report");
    w("");
    fence(L, "Agent Review", g("test_review"), "");

    // -------- 9. CI & Static Checks --------
    w("## 9. CI & Static Checks");
    w("");
    fence(L, "CI Checks Summary", g("ci_checks_summary"), "");
    var fb = g("feedbackbutton-fast_static_checks", {}) || {};
    w("**Fast static checks:** status = " + code(fb.status));
    w("");
    var checks = (fb.notes && fb.notes.static_checks) || [];
    checks.forEach(function (sc) {
      w("- **" + (sc.name || "") + "** — passed: " + code(sc.passed) + " (" + (sc.note_type || "") + ")");
      if (sc.details) w("  - " + sc.details);
    });
    w("");

    // -------- 10. Evaluation Rubrics --------
    w("## 10. Evaluation Rubrics");
    w("");
    fence(L, "test_rubrics", g("test_rubrics"), "");

    // -------- 10b. Automated feedback & evaluation history --------
    w("## 10b. Automated Feedback");
    w("");
    w("| Field | Value |");
    w("|---|---|");
    w("| Eval revision notes | " + code(t.eval_revision_notes) + " |");
    w("| Eval revision requested at | " + code(t.eval_revision_requested_at) + " |");
    w("| Rebuttal notes | " + code(t.rebuttal_notes) + " |");
    w("");
    var comments = g("textarea-beca8");
    if (comments) fence(L, "Comments for Reviewer (submitted)", comments, "");
    var evals = Array.isArray(t.evaluations) ? t.evaluations.slice() : [];
    if (evals.length) {
      evals.sort(function (a, b) { return String(a.created_at || "").localeCompare(String(b.created_at || "")); });
      w("### Evaluation History (oldest first)");
      w("");
      w("| # | Created | Outcome | Blocking stage | Stages |");
      w("|---|---|---|---|---|");
      evals.forEach(function (ev, i) {
        var agent = null;
        var kids = (ev.overall_evaluation_result || {}).children_results || [];
        kids.forEach(function (k) {
          var m = k && k.metadata && k.metadata.agent_result;
          if (m) agent = m;
        });
        var stages = agent && agent.stages ? Object.keys(agent.stages).filter(function (n) {
          return agent.stages[n] && agent.stages[n].ran;
        }).map(function (n) {
          var st = agent.stages[n];
          return n + "=" + (st.eval_passed === true ? "pass" : st.eval_passed === false ? "FAIL" : "ran");
        }).join(", ") : "";
        w("| " + (i + 1) + " | " + code(ev.created_at) + " | " + code(ev.outcome) + " | " +
          code(agent ? agent.blocking_stage : "") + " | " + stages + " |");
      });
      w("");
    }

    // -------- 11. Reviewer Decision --------
    // The review panel shows conditional fields depending on the decision:
    //   • Accept          -> Acceptance Notes
    //   • Needs Revision  -> Revision Notes + Error Categories
    w("## 11. Reviewer Decision");
    w("");
    var docs = collectAnswerDocs(t, sd);
    var decisionRaw = pickField(docs, ["radio-9552f", "review_decision", "submission_review_decision"]);
    var revisionNotes = pickField(docs, ["textarea-revision_notes", "revision_notes"]);
    var acceptNotes = pickField(docs, ["textarea-a1f81", "acceptance_notes", "accept_notes"]);
    var errorCats = pickField(docs, ["multiselect-error-categories", "error_categories"]);

    var decision = decisionRaw ? String(decisionRaw).toLowerCase() : "";
    var inferred = false;
    if (!decision) {
      if (acceptNotes) { decision = "yes"; inferred = true; }
      else if (revisionNotes || (errorCats && errorCats.length)) { decision = "needs_revision"; inferred = true; }
    }
    var isAccept = decision === "yes" || decision === "accept";
    var isRevision = decision === "needs_revision" || decision === "revision";
    var decisionLabel = isAccept ? "Accept" : isRevision ? "Needs Revision" : "—";

    function writeParas(text) {
      if (text) {
        String(text).split("\n\n").forEach(function (para) { w(para.trim()); w(""); });
      } else {
        w("_(none)_");
        w("");
      }
    }

    w("| Field | Value |");
    w("|---|---|");
    w("| Submission Review Decision | **" + decisionLabel + "**" + (inferred ? " _(inferred from notes)_" : "") + " |");
    w("");

    if (isAccept) {
      w("### Acceptance Notes");
      w("");
      writeParas(acceptNotes);
    } else if (isRevision) {
      w("### Revision Notes");
      w("");
      writeParas(revisionNotes);
      w("### Error Categories");
      w("");
      var cats = normalizeErrorCategories(errorCats, t);
      if (cats.length) { cats.forEach(function (c) { w("- " + c); }); w(""); }
      else { w("_(none)_"); w(""); }
    } else {
      // Decision unknown: surface whatever review text exists.
      w("### Revision Notes");
      w("");
      writeParas(revisionNotes);
      if (acceptNotes) {
        w("### Acceptance Notes");
        w("");
        writeParas(acceptNotes);
      }
    }

    w("---");
    w("");
    w("_Generated by TB Task Revise Extractor from the Snorkel Experts task payload._");

    return L.join("\n") + "\n";
  }

  // ---- Revise prompt (flag remediation) ----
  // The paste-ready prompt for the "Some tests not passed by any agent run" +
  // instruction-sufficiency loop. Kept to the bare template: the only thing
  // filled in is where the export put the task and its report, so the agent
  // reads the feedback from disk instead of carrying hundreds of pasted lines.

  // The task slug the extracted bundle uses, taken from the uploaded zip name.
  function taskSlug(task) {
    try {
      var sd = submissionDoc(task);
      var f = (sd.upload_a_zip_file || {}).filename || "";
      var base = String(f).replace(/\.zip$/i, "").trim();
      if (base) return base;
    } catch (e) {}
    return taskId(task);
  }

  // One-line summary of why the platform returned this round, read from the
  // same payload fields the report renders: blocking quality-panel findings by
  // axis and severity, failed quality checks, tests no run passed, a BASE tier
  // and a human "Needs Revision". Empty when nothing is recognised.
  function returnReason(task) {
    var t = task || {};
    var sd = submissionDoc(t);
    var text = [sd.text_summary, sd.quality_check_summary].filter(Boolean).join("\n");
    var parts = [];

    var byAxis = {};
    var order = [];
    var re = /^\s*\d+\.\s*\[([^\]]+)\]\s*(MAJOR|MINOR)\s*:/gm;
    var m;
    while ((m = re.exec(String(sd.text_summary || "")))) {
      var axis = m[1].trim();
      var sev = m[2].charAt(0) + m[2].slice(1).toLowerCase();
      if (!byAxis[axis]) { byAxis[axis] = {}; order.push(axis); }
      byAxis[axis][sev] = (byAxis[axis][sev] || 0) + 1;
    }
    order.forEach(function (axis) {
      var s = byAxis[axis];
      var counts = ["Major", "Minor"].filter(function (k) { return s[k]; })
        .map(function (k) { return s[k] + " " + k; });
      parts.push(axis + " " + counts.join(", "));
    });

    var failed = [];
    var fre = /❌\s*fail\s*-\s*([A-Za-z0-9_]+)/g;
    while ((m = fre.exec(text))) {
      if (failed.indexOf(m[1]) < 0) failed.push(m[1]);
    }
    if (failed.length) parts.push("quality check fail: " + failed.join(", "));

    var tr = sd.test_results || {};
    var zero = 0, runs = 0;
    Object.keys(tr).forEach(function (name) {
      var results = tr[name] || [];
      runs = Math.max(runs, results.length);
      if (results.length && !results.some(function (r) { return r === "passed"; })) zero++;
    });
    if (zero) parts.push("Some tests not passed (" + zero + " test 0/" + runs + ")");

    if (String(sd.difficulty || "").toLowerCase() === "base") parts.push("BASE");

    var docs = collectAnswerDocs(t, sd);
    var decision = String(pickField(docs, ["radio-9552f", "review_decision", "submission_review_decision"]) || "").toLowerCase();
    if (decision === "needs_revision" || decision === "revision") parts.push("human review: Needs Revision");

    return parts.join(" / ");
  }

  // Keep the clipboard prompt compact: the detailed platform feedback already
  // lives in <task_id>.md beside the extracted task.
  function generateRevisePrompt(task, options) {
    var t = task || {};
    var opts = options || {};
    var slug = taskSlug(t);
    var id = taskId(t);
    var exportRoot = String(opts.exportRoot || "workspace/revision").replace(/\/+$/, "");
    var submissionRoot = String(opts.submissionRoot || "workspace/submissions").replace(/\/+$/, "");
    var taskRoot = exportRoot + "/" + id;
    var revisionsPath = taskRoot + "/revisions";
    // Round layout: revision/<uuid>/vN/ ("" = legacy flat export, counts as v1).
    var round = opts.round || 1;
    var rd = opts.roundDir == null ? "" : String(opts.roundDir);
    var base = rd ? taskRoot + "/" + rd : taskRoot;
    var sourceZip = taskRoot + "/" + (opts.sourceZip || ("revisions/" + slug + "-source.zip"));
    var nextRev = opts.nextRev || 1;

    var reason = returnReason(t) || "<tóm tắt lý do trả về>";

    var lines = [
      "Revise v" + round + " (" + reason + ")",
      "Task: " + base + "/" + slug,
      "Platform feedback v" + round + ": " + base + "/" + id + ".md"
    ];
    if (round > 1) {
      var prev = opts.prevRoundDir ? taskRoot + "/" + opts.prevRoundDir : taskRoot;
      lines.push("Feedback vòng trước: " + prev + "/" + id + ".md");
    }
    lines.push(
      "Yêu cầu:",
      "",
      "* Dùng task-revise-flag-remediation. Đọc \"Blocking stage\" trước và xử lý theo",
      "grading flow:",
      "   * panel/quality check: sửa theo ledger, quét cả nhóm lỗi (blueprint §5), không chỉ đúng ca được nêu;",
      "   * test 0/8: chạy bộ lọc 0/8, bỏ trap chứ không tiết lộ, dọn khắp fixtures/explanations/rubric;",
      "   * BASE: dừng lại và đề xuất task thay thế, không làm khó thêm;",
      "   * human review: sửa đúng từng note.",
      "* Khôi phục từ đúng source zip platform đã chấm; mỗi finding phải có receipt tái hiện",
      "trên bản cũ và receipt đóng trên bản mới. Finding không tái hiện được thì dispute kèm receipt.",
      "* Ưu tiên \"stop promising\" với promise không thuộc core; giữ nguyên phần khó.",
      "* Nếu chỉ sửa tests: giữ instruction, environment, solution byte-identical;",
      "clearance chỉ trục sound_verifier; không re-probe.",
      "* Nếu thu hẹp core: re-probe 1 cặp trên claude-opus-5 (dừng nếu không gọi được Opus 5).",
      "* Tự chạy hết các bước bắt buộc (closure gates, clearance, panel receipt,",
      "preflight --emit-zip --panel-report), không hỏi lại.",
      "* Cập nhật 3 explanation, difficulty, rubric và SUBMISSION note khớp bản mới.",
      "",
      "Lưu file:",
      "",
      "* Không sửa/ghi đè " + sourceZip + ".",
      "* Lưu bản mới tại " + revisionsPath + "/" + slug + "-rev" + nextRev + ".zip (không ghi đè rev cũ).",
      "* Đồng bộ đúng bytes sang " + submissionRoot + "/" + slug + ".zip để upload.",
      "",
      "Báo cáo ngắn: stage bị chặn, bảng finding → quyết định (backed/dropped/disputed),",
      "trục đã clearance, có re-probe không, đường dẫn ZIP.",
      ""
    );
    return lines.join("\n");
  }

  // ---- Markdown -> standalone HTML ----
  // Handles just the constructs generateMarkdown emits: ATX headings, pipe
  // tables, fenced code, blockquotes, `-` lists, `---` rules, inline bold /
  // code / links, and paragraphs. Enough for a readable offline report.
  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function inline(s) {
    var out = escapeHtml(s);
    out = out.replace(/`([^`]+)`/g, function (_, c) { return "<code>" + c + "</code>"; });
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (_, t, u) {
      return '<a href="' + u.replace(/"/g, "%22") + '">' + t + "</a>";
    });
    return out;
  }

  function markdownToHtml(md) {
    var lines = String(md).split("\n");
    var html = [];
    var i = 0;
    while (i < lines.length) {
      var line = lines[i];

      if (/^```/.test(line)) {
        var buf = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i])) { buf.push(lines[i]); i++; }
        i++;
        html.push("<pre><code>" + escapeHtml(buf.join("\n")) + "</code></pre>");
        continue;
      }
      if (/^\s*---\s*$/.test(line)) { html.push("<hr/>"); i++; continue; }
      var h = /^(#{1,6})\s+(.*)$/.exec(line);
      if (h) { var n = h[1].length; html.push("<h" + n + ">" + inline(h[2]) + "</h" + n + ">"); i++; continue; }
      if (/^>\s?/.test(line)) {
        var q = [];
        while (i < lines.length && /^>\s?/.test(lines[i])) { q.push(lines[i].replace(/^>\s?/, "")); i++; }
        html.push("<blockquote>" + inline(q.join(" ")) + "</blockquote>");
        continue;
      }
      // Pipe table: header row, separator row, then body rows.
      if (/^\s*\|.*\|\s*$/.test(line) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
        var cellsOf = function (row) {
          return row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(function (c) { return c.trim(); });
        };
        var head = cellsOf(line);
        i += 2;
        var rows = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) { rows.push(cellsOf(lines[i])); i++; }
        var t = ["<table><thead><tr>"];
        head.forEach(function (c) { t.push("<th>" + inline(c) + "</th>"); });
        t.push("</tr></thead><tbody>");
        rows.forEach(function (r) {
          t.push("<tr>");
          r.forEach(function (c) { t.push("<td>" + inline(c) + "</td>"); });
          t.push("</tr>");
        });
        t.push("</tbody></table>");
        html.push(t.join(""));
        continue;
      }
      if (/^\s*[-*]\s+/.test(line)) {
        var items = [];
        while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
          items.push("<li>" + inline(lines[i].replace(/^\s*[-*]\s+/, "")) + "</li>");
          i++;
        }
        html.push("<ul>" + items.join("") + "</ul>");
        continue;
      }
      if (/^\s*$/.test(line)) { i++; continue; }
      var para = [line];
      i++;
      while (i < lines.length && !/^\s*$/.test(lines[i]) && !/^(#{1,6}\s|>|```|\s*\||\s*[-*]\s)/.test(lines[i])) {
        para.push(lines[i]); i++;
      }
      html.push("<p>" + inline(para.join(" ")) + "</p>");
    }
    return html.join("\n");
  }

  function generateHtmlDoc(task) {
    var md = generateMarkdown(task);
    var id = taskId(task);
    var body = markdownToHtml(md);
    var css =
      "body{font:15px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;" +
      "max-width:900px;margin:2rem auto;padding:0 1.2rem;color:#1a1a1a}" +
      "h1,h2,h3{line-height:1.25;margin-top:1.6em}h1{border-bottom:2px solid #eee;padding-bottom:.3em}" +
      "h2{border-bottom:1px solid #eee;padding-bottom:.2em}" +
      "table{border-collapse:collapse;width:100%;margin:1em 0;font-size:14px}" +
      "th,td{border:1px solid #ddd;padding:6px 10px;text-align:left;vertical-align:top}" +
      "th{background:#f6f8fa}code{background:#f2f2f2;padding:.1em .35em;border-radius:4px;font-size:.9em}" +
      "pre{background:#f6f8fa;padding:1em;overflow:auto;border-radius:6px}pre code{background:none;padding:0}" +
      "blockquote{margin:1em 0;padding:.4em 1em;color:#555;border-left:4px solid #ddd}" +
      "hr{border:none;border-top:1px solid #eee;margin:2em 0}a{color:#0a58ca}" +
      "@media(prefers-color-scheme:dark){body{background:#0d1117;color:#c9d1d9}" +
      "th{background:#161b22}code,pre{background:#161b22}th,td{border-color:#30363d}" +
      "h1,h2{border-color:#30363d}blockquote{color:#8b949e;border-color:#30363d}}";
    return "<!doctype html>\n<html lang=\"vi\"><head><meta charset=\"utf-8\"/>" +
      "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>" +
      "<title>" + escapeHtml(id) + "</title><style>" + css + "</style></head><body>\n" +
      body + "\n</body></html>\n";
  }

  return {
    generateMarkdown: generateMarkdown,
    generateHtmlDoc: generateHtmlDoc,
    markdownToHtml: markdownToHtml,
    extractTasks: extractTasks,
    taskId: taskId,
    rawTaskId: rawTaskId,
    taskSlug: taskSlug,
    returnReason: returnReason,
    generateRevisePrompt: generateRevisePrompt
  };
});
