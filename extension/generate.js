/*
 * TB Task Review Extractor — Markdown generator (universal).
 *
 * Works both in the browser (exposes `window.TBGen`) and in Node
 * (`module.exports`). Given ONE task object (an element of the review API's
 * `tasks[]` array) it returns a comprehensive Markdown report.
 *
 * Source of the data:
 *   GET https://experts.snorkel-ai.com/api/v1/assignment/{project_id}/review-{review_task_type_id}
 *   -> { tasks: [ { task_documents: [ { submission_document: {...} } ], ... } ] }
 *
 * Sections mirror the platform's right-hand review panel. (The original
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

  function taskId(task) {
    return (task && task.task_id && task.task_id.id) || "unknown-task";
  }

  function submissionDoc(task) {
    try {
      return task.task_documents[0].submission_document || {};
    } catch (e) {
      return {};
    }
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
    lines.push(typeof body === "string" ? body.replace(/\s+$/, "") : String(body));
    lines.push("```", "");
  }

  function code(v) {
    return "`" + (v === undefined || v === null ? "" : v) + "`";
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
    w("# Terminal Bench 2.0 — Task Review Report");
    w("");
    w("> Comprehensive task information extracted from the Snorkel Experts review API.");
    w("> This is the same data that populates the task's right-hand **review panel** " +
      "(Difficulty Explanation, Solution Explanation, checks, rubrics, agent runs, etc.).");
    w("");

    // -------- 1. Task Identity & Metadata --------
    w("## 1. Task Identity & Metadata");
    w("");
    w("| Field | Value |");
    w("|---|---|");
    w("| Project | " + code(t.project) + " |");
    w("| Project ID | " + code(t.project_id && t.project_id.id) + " |");
    w("| Assignment ID | " + code(t.assignment_id && t.assignment_id.id) + " |");
    w("| Task ID | " + code(t.task_id && t.task_id.id) + " |");
    w("| Submission ID | " + code(t.submission_id && t.submission_id.id) + " |");
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
    w("Overall: **Difficulty: " + String(g("difficulty", "")).toUpperCase() +
      " · Status: " + (g("solvable") ? "Solvable" : "Not solvable") +
      "** (all tests passed by at least one agent run).");
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
    w("_Generated by TB Task Review Extractor from the Snorkel Experts review API._");

    return L.join("\n") + "\n";
  }

  // ---- Revise prompt (flag remediation) ----
  // Builds the paste-ready prompt for the "Some tests not passed by any agent
  // run" + instruction-sufficiency revision loop, pre-filled with this task's
  // slug, its 0/N test table, and every non-empty platform feedback block.

  // The task slug the repo folder uses, taken from the uploaded bundle name.
  function taskSlug(task) {
    try {
      var sd = submissionDoc(task);
      var f = (sd.upload_a_zip_file || {}).filename || "";
      var base = String(f).replace(/\.zip$/i, "").trim();
      if (base) return base;
    } catch (e) {}
    return taskId(task);
  }

  // Split the per-test results into the two buckets the remediation skill acts
  // on: never passed (0/N -> the blocking flag) and barely passed (<=2/N ->
  // rerun risk that must not be pruned blindly).
  function testBuckets(task) {
    var sd = submissionDoc(task);
    var tr = sd.test_results || {};
    var zero = [], thin = [], runs = 0;
    Object.keys(tr).forEach(function (name) {
      var r = tr[name] || [];
      runs = Math.max(runs, r.length);
      var npass = r.filter(function (x) { return x === "passed"; }).length;
      if (!r.length) return;
      if (npass === 0) zero.push({ name: name, pass: 0, total: r.length });
      // Thin = survived, but not on every run. A test that passed all its runs
      // is healthy no matter how few runs there were.
      else if (npass <= 2 && npass < r.length) thin.push({ name: name, pass: npass, total: r.length });
    });
    return { zero: zero, thin: thin, runs: runs };
  }

  function promptBlock(title, body) {
    var text = String(body == null ? "" : body).replace(/\s+$/, "");
    if (!text) return "";
    return "### " + title + "\n\n```\n" + text + "\n```\n\n";
  }

  function generateRevisePrompt(task) {
    var t = task || {};
    var sd = submissionDoc(t);
    var slug = taskSlug(t);
    var b = testBuckets(t);
    var P = [];
    function w(s) { P.push(s === undefined ? "" : s); }

    w("2. Revise (Some test not passed và Instruction Sufficiency)");
    w("Revise task tại:");
    w("");
    w(slug);
    w("");
    w("Platform feedback:");
    w("");

    // Concrete per-test evidence first — this is what the skill classifies.
    if (b.zero.length) {
      w("#### Tests không có agent run nào pass (0/" + b.runs + ")");
      w("");
      b.zero.forEach(function (x) { w("- `" + x.name + "` — 0/" + x.total); });
      w("");
    } else if (b.runs) {
      w("#### Tests không có agent run nào pass");
      w("");
      w("_(không có test 0/N trong dữ liệu difficulty check hiện tại)_");
      w("");
    }
    if (b.thin.length) {
      w("#### Tests pass rất ít (rerun risk — cân nhắc kỹ trước khi prune)");
      w("");
      b.thin.forEach(function (x) { w("- `" + x.name + "` — " + x.pass + "/" + x.total); });
      w("");
    }

    // Then the raw platform blocks, verbatim, so nothing is paraphrased away.
    var blocks =
      promptBlock("Difficulty check — text summary", sd.text_summary) +
      promptBlock("Quality check summary", sd.quality_check_summary) +
      promptBlock("TB 3.0 Rubric Feedback Checks", sd.tb_3_rubric_feedback_checks) +
      promptBlock("Agent review", sd.test_review) +
      promptBlock("Test Quality Report", sd.test_quality_judge_report) +
      promptBlock("CI checks summary", sd.ci_checks_summary);

    // Reviewer's own words outrank the automated blocks when present.
    var docs = collectAnswerDocs(t, sd);
    var revisionNotes = pickField(docs, ["textarea-revision_notes", "revision_notes"]);
    var errorCats = normalizeErrorCategories(
      pickField(docs, ["multiselect-error-categories", "error_categories"]), t);
    var reviewer = promptBlock("Revision notes (reviewer)", revisionNotes);
    if (errorCats.length) {
      reviewer += "### Error Categories\n\n" +
        errorCats.map(function (c) { return "- " + c; }).join("\n") + "\n\n";
    }

    w((reviewer + blocks).replace(/\s+$/, ""));
    w("");
    w("- Sử dụng task-revise-flag-remediation để phân loại từng test 0/N, kiểm tra");
    w("instruction sufficiency và correlated blind spots trước khi quyết định");
    w("disclose, parametrize, prune hoặc bổ sung reference data.");
    w("- Hãy xác minh từng feedback bằng code, instruction và verifier trước khi sửa.");
    w("Tự động xử lý toàn bộ blocker trong phạm vi task, chạy lại Oracle/NOP và");
    w("preflight, giữ nguyên evidence về difficulty, rồi tạo ZIP thay thế sẵn sàng");
    w("upload. Không che lỗi bằng cách nới assertion hoặc xóa coverage quan trọng.");
    w("");

    return P.join("\n");
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
    taskSlug: taskSlug,
    generateRevisePrompt: generateRevisePrompt
  };
});
