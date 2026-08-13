/*
 * ISOLATED-world content script.
 *
 * Bridges the MAIN-world interceptor (which sees page network responses but not
 * chrome.* APIs) to the extension's service worker, and lets the popup drive
 * the page's own "Download file" control so we can grab the submission bundle.
 */
(function () {
  "use strict";

  // The last review payload this tab fetched. The popup reads the task open in
  // THIS tab from here — no accumulated list, no chrome.storage of captures.
  var lastPayload = null;
  // {n: apiResponsesSniffed, hits: [urlsCarryingTheMarker]} — popup diagnostics.
  var lastSeen = { n: 0, hits: [] };

  // ---- interceptor -> this tab / service worker ----
  window.addEventListener("message", function (ev) {
    if (ev.source !== window) return;
    var d = ev.data;
    if (!d || d.__tbExtractor !== true) return;
    try {
      if (d.kind === "capture") {
        lastPayload = d.payload || null;
      } else if (d.kind === "seen") {
        lastSeen = d.seen || lastSeen;
      } else if (d.kind === "zipurl") {
        chrome.runtime.sendMessage({ type: "tb-zip-url", url: d.url });
      }
    } catch (e) {
      // Service worker asleep or context invalidated; ignore.
    }
  });

  // Pick the task matching the UUID shown on the page; fall back to the single
  // task the review API returned for this page.
  function pickTask(uuid) {
    if (!lastPayload || !Array.isArray(lastPayload.tasks)) return null;
    var tasks = lastPayload.tasks;
    if (uuid) {
      for (var i = 0; i < tasks.length; i++) {
        var t = tasks[i];
        if (t && t.task_id && t.task_id.id === uuid) return t;
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

    // Reviewer page: a copy-to-clipboard span.
    var spans = document.querySelectorAll('span[title="Click to copy"]');
    for (var i = 0; i < spans.length; i++) {
      var t = (spans[i].textContent || "").trim();
      if (uuidRe.test(t)) return t;
    }
    // Submitter page: the header shows "UID:" beside a plain span. Take the
    // first UUID that starts a span's text (a trailing copy button adds markup).
    var all = document.querySelectorAll("span, div");
    for (var j = 0; j < all.length; j++) {
      if (all[j].querySelector("span, div")) continue;
      var s2 = (all[j].textContent || "").trim();
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
      sendResponse({ ok: true, uuid: uuid, task: pickTask(uuid), seen: lastSeen });
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
