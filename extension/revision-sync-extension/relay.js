/*
 * ISOLATED-world content script.
 *
 * Bridges the MAIN-world interceptor (which sees page network responses but not
 * chrome.* APIs) to the extension's service worker, and lets the popup drive
 * the page's own "Download file" control so we can grab the submission bundle.
 */
(function () {
  "use strict";

  // The last task/revise payload this tab fetched. The popup reads the task open in
  // THIS tab from here — no accumulated list, no chrome.storage of captures.
  var lastPayload = null;
  // form_schema from /api/v1/projects/{id}; used for error-category labels.
  var lastSchema = null;
  // API route the last capture came from (written into task-payload.json).
  var lastUrl = "";
  // {n: apiResponsesSniffed, hits: [urlsCarryingTheMarker]} — popup diagnostics.
  var lastSeen = { n: 0, hits: [] };

  // ---- interceptor -> this tab / service worker ----
  window.addEventListener("message", function (ev) {
    if (ev.source !== window) return;
    var d = ev.data;
    if (!d || d.__tbExtractor !== true) return;
    try {
      if (d.kind === "capture") {
        var incoming = d.payload || null;
        if (payloadScore(incoming) >= payloadScore(lastPayload)) {
          lastPayload = incoming;
          lastUrl = d.url || "";
        }
      } else if (d.kind === "schema") {
        lastSchema = d.schema || null;
      } else if (d.kind === "seen") {
        lastSeen = d.seen || lastSeen;
      } else if (d.kind === "zipurl") {
        chrome.runtime.sendMessage({ type: "tb-zip-url", url: d.url });
      }
    } catch (e) {
      // Service worker asleep or context invalidated; ignore.
    }
  });

  // Rank captures so a later, emptier response (config schema, list views)
  // cannot evict the full task payload: 2 = answers + evaluations, 1 = answers,
  // 0 = shape only.
  var SCHEMA_KEYS = ["type", "enum", "oneOf", "anyOf", "allOf", "$ref", "items"];
  function docHasAnswers(sd) {
    return Object.keys(sd || {}).some(function (k) {
      if (k === "upload_a_zip_file") return false;
      var v = sd[k];
      if (v === null || v === undefined || v === "") return false;
      if (typeof v === "object" && !Array.isArray(v)) {
        var ks = Object.keys(v);
        return ks.length > 0 && !ks.every(function (x) { return SCHEMA_KEYS.indexOf(x) >= 0; });
      }
      return true;
    });
  }
  function payloadScore(p) {
    if (!p || !Array.isArray(p.tasks) || !p.tasks.length) return -1;
    var best = 0;
    p.tasks.forEach(function (t) {
      var sd = {};
      try { sd = t.task_documents[0].submission_document || {}; } catch (e) {}
      var sc = docHasAnswers(sd) ? 1 : 0;
      if (sc && Array.isArray(t.evaluations) && t.evaluations.length) sc = 2;
      if (sc > best) best = sc;
    });
    return best;
  }

  // Mirrors TBGen.rawTaskId (generate.js is not loaded in content scripts).
  function taskUuid(t) {
    if (!t || typeof t !== "object") return "";
    var tid = t.task_id;
    if (tid && typeof tid === "object" && tid.id) return String(tid.id);
    if (typeof tid === "string" && tid) return tid;
    var keys = ["task_uuid", "uuid", "id"];
    for (var i = 0; i < keys.length; i++) {
      var v = t[keys[i]];
      if (typeof v === "string" && v) return v;
      if (v && typeof v === "object" && v.id) return String(v.id);
    }
    return "";
  }

  // Pick the task matching the UUID shown on the page; fall back to the single
  // task payload returned for this page.
  function pickTask(uuid) {
    if (!lastPayload || !Array.isArray(lastPayload.tasks)) return null;
    var tasks = lastPayload.tasks;
    if (uuid) {
      for (var i = 0; i < tasks.length; i++) {
        var t = tasks[i];
        if (taskUuid(t) === uuid) return t;
      }
    }
    return tasks[0] || null;
  }

  // ---- popup -> page: find/trigger the submission download ----
  // Two strategies, cheapest first:
  //   1. Read a direct .zip href off the download control (no click, no native
  //      download side effect).
  //   2. Click "Download file" so the SPA generates the presigned URL, which
  //      the interceptor then captures as a "zipurl" message.
  function findDownloadCard() {
    return (
      document.querySelector('[data-testid^="field-s3FileUploader"]') ||
      document.querySelector(".bg-success-subtle.rounded-lg") ||
      document.querySelector(".bg-global-success-background-subtle.rounded-lg") ||
      document.querySelector(".rounded-lg.border-green-200") ||
      document.querySelector('.rounded-lg[class*="green-"]')
    );
  }

  function readZipFilename(card) {
    if (!card) return "";
    var el = card.querySelector(".text-color-success") ||
             card.querySelector(".text-green-800") ||
             card.querySelector(".font-medium");
    if (el && /\.zip$/i.test((el.textContent || "").trim())) {
      return (el.textContent || "").trim();
    }
    var leafs = card.querySelectorAll("div, span, p, a");
    for (var i = 0; i < leafs.length; i++) {
      if (leafs[i].children.length > 0) continue;
      var t = (leafs[i].textContent || "").trim();
      if (/^\S+\.zip$/i.test(t)) return t;
    }
    return "";
  }

  function directHref(card) {
    var scope = card || document;
    var anchors = scope.querySelectorAll('a[href]');
    for (var i = 0; i < anchors.length; i++) {
      var h = anchors[i].getAttribute("href") || "";
      if (/\.zip(\?|$)/i.test(h) || /[?&]X-Amz-Signature=/i.test(h)) {
        return anchors[i].href;
      }
    }
    return "";
  }

  // The task UUID shown on the page the user is actually looking at, so the
  // popup targets the open task instead of whatever was captured last.
  function currentTaskUuid() {
    var uuidRe = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    var loose = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

    // Revise/reviewer page: a copy-to-clipboard span.
    var spans = document.querySelectorAll('span[title="Click to copy"]');
    for (var i = 0; i < spans.length; i++) {
      var t = (spans[i].textContent || "").trim();
      if (uuidRe.test(t)) return t;
    }
    // Submitter page: the header shows "UID:" beside a span whose own text is
    // the UUID followed by a copy <button><span><svg/></span></button>. A
    // "leaf only" test skips it, so read each element's direct text nodes.
    var all = document.querySelectorAll("span, div");
    for (var j = 0; j < all.length; j++) {
      var s2 = "";
      var kids = all[j].childNodes;
      for (var k = 0; k < kids.length; k++) {
        if (kids[k].nodeType === 3) s2 += kids[k].nodeValue;
      }
      s2 = s2.trim();
      if (!s2) continue;
      if (uuidRe.test(s2)) return s2;
      var m2 = s2.match(loose);
      if (m2 && s2.indexOf(m2[0]) === 0) return m2[0];
    }
    var m = location.href.match(loose);
    return m ? m[0] : "";
  }

  chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
    if (!msg) return;

    if (msg.type === "tb-get-current-task") {
      var uuid = currentTaskUuid();
      var picked = pickTask(uuid);
      // FormBlocks task payloads omit form_schema; borrow the project's.
      if (picked && !picked.form_schema && lastSchema) picked.form_schema = lastSchema;
      sendResponse({
        ok: true, uuid: uuid, task: picked, seen: lastSeen, sourceUrl: lastUrl,
        zipName: readZipFilename(findDownloadCard())
      });
      return;
    }

    // The "Download difficulty check results" control lives in its own field
    // card. Same two strategies as the submission bundle: direct href first,
    // otherwise click and let the interceptor capture the presigned URL.
    if (msg.type === "tb-resolve-difficulty-zip") {
      var dHost = document.querySelector('[data-testid="field-difficulty_check_artifact_s3_key"]');
      if (!dHost) {
        sendResponse({ ok: false, reason: "field-missing", url: "", clicked: false });
        return;
      }
      var dHref = directHref(dHost);
      if (dHref) {
        sendResponse({ ok: true, url: dHref, clicked: false });
        return;
      }
      var dBtn = dHost.querySelector("button");
      if (dBtn && !dBtn.disabled) {
        dBtn.click();
        sendResponse({ ok: true, url: "", clicked: true });
      } else {
        sendResponse({ ok: false, reason: "button-missing", url: "", clicked: false });
      }
      return;
    }

    if (msg.type !== "tb-resolve-zip") return;
    var card = findDownloadCard();
    var filename = readZipFilename(card);
    var href = directHref(card);
    if (href) {
      sendResponse({ ok: true, filename: filename, url: href, clicked: false });
      return; // sync response
    }
    var btn = (card && card.querySelector('button[title="Download file"]')) ||
              document.querySelector('button[title="Download file"]');
    if (btn) {
      btn.click(); // interceptor will capture the presigned URL as "zipurl"
      sendResponse({ ok: true, filename: filename, url: "", clicked: true });
    } else {
      sendResponse({ ok: false, filename: filename, url: "", clicked: false });
    }
  });
})();
