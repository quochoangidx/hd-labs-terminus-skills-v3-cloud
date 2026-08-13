/*
 * MAIN-world content script.
 *
 * The Snorkel SPA fetches the comprehensive task/revise payload itself (with the
 * correct session cookie + x-id-token JWT). Rather than re-authenticate, we
 * transparently observe those responses by patching fetch + XMLHttpRequest,
 * and hand any matching JSON to the ISOLATED-world relay via postMessage.
 */
(function () {
  "use strict";

  // The payload we want ships from more than one route: reviewer/revise queues
  // and the submitter's own task page
  // both return the same {tasks:[{task_documents:[...]}]} shape under different
  // paths. Rather than chase route names, we sniff any same-origin API response
  // for the marker key — a cheap indexOf on the raw text, no JSON.parse unless
  // it hits.
  var MARKER = '"task_documents"';

  function isApiUrl(url) {
    try {
      var u = new URL(url, location.href);
      if (u.origin !== location.origin) return false;
      return u.pathname.indexOf("/api/") === 0 || u.pathname.indexOf("/api/") > 0;
    } catch (e) {
      return /\/api\//.test(String(url));
    }
  }

  // Diagnostics for the popup: which API routes we looked at, which carried the
  // marker. Surfaced when the popup cannot find a task.
  var seen = { n: 0, hits: [] };
  function note(url, hit) {
    seen.n++;
    if (hit && seen.hits.indexOf(url) < 0 && seen.hits.length < 8) seen.hits.push(url);
    try {
      window.postMessage({ __tbExtractor: true, kind: "seen", seen: seen }, location.origin);
    } catch (e) {}
  }

  // A presigned S3/CDN link to the submission bundle: a .zip URL, or any URL
  // that carries an AWS signature. We forward these so the popup can pull the
  // bytes itself (host_permissions let the extension page bypass CORS) and
  // extract into the task folder — mirroring the CLI's "click Download" step.
  function isZipUrl(url) {
    var s = String(url || "");
    if (/[?&]X-Amz-Signature=/i.test(s)) return true;
    return /\.zip(\?|$)/i.test(s);
  }

  function postZipUrl(url) {
    try {
      window.postMessage({ __tbExtractor: true, kind: "zipurl", url: String(url) }, location.origin);
    } catch (e) {}
  }

  // Only endpoints that plausibly hand back a download URL are worth parsing,
  // so we don't clone+JSON every response on a busy SPA.
  function isDownloadIsh(url) {
    return /download|presign|signed|artifact|submission|s3|blob|file/i.test(String(url || ""));
  }

  // Pull a download URL out of a JSON download-endpoint response, whatever the
  // portal calls the field.
  function zipUrlFromJson(obj) {
    if (!obj || typeof obj !== "object") return null;
    var keys = ["url", "downloadUrl", "download_url", "signedUrl", "signed_url", "presignedUrl", "presigned_url", "href"];
    for (var i = 0; i < keys.length; i++) {
      var v = obj[keys[i]];
      if (typeof v === "string" && isZipUrl(v)) return v;
    }
    return null;
  }

  function isTask(x) {
    return !!(x && typeof x === "object" && Array.isArray(x.task_documents) && x.task_documents.length);
  }

  // Normalize whatever the route returned into {tasks:[...]}, or null.
  function normalizeTasks(obj) {
    if (!obj || typeof obj !== "object") return null;
    var candidates = [obj.tasks, obj.results, obj.items, obj.data && obj.data.tasks];
    for (var i = 0; i < candidates.length; i++) {
      var c = candidates[i];
      if (Array.isArray(c) && c.some(isTask)) return { tasks: c.filter(isTask) };
    }
    if (isTask(obj)) return { tasks: [obj] };
    if (isTask(obj.task)) return { tasks: [obj.task] };
    if (obj.data && isTask(obj.data)) return { tasks: [obj.data] };
    return null;
  }

  // Parse only when the raw text carries the marker key.
  function tasksFromText(txt) {
    if (!txt || txt.indexOf(MARKER) < 0) return null;
    try { return normalizeTasks(JSON.parse(txt)); } catch (e) { return null; }
  }

  function post(payload, url) {
    try {
      window.postMessage({ __tbExtractor: true, kind: "capture", url: url, payload: payload }, location.origin);
    } catch (e) { /* ignore */ }
  }

  // ---- patch fetch ----
  var origFetch = window.fetch;
  if (typeof origFetch === "function") {
    window.fetch = function () {
      var args = arguments;
      var p = origFetch.apply(this, args);
      try {
        var first = args[0];
        var url = first && first.url ? first.url : String(first);
        if (isApiUrl(url)) {
          p.then(function (res) {
            try {
              var ct = res.headers.get("content-type") || "";
              if (ct.indexOf("json") < 0) return;
              res.clone().text().then(function (txt) {
                var norm = tasksFromText(txt);
                note(url, !!norm);
                if (norm) post(norm, url);
              }).catch(function () {});
            } catch (e) {}
          }).catch(function () {});
        }
        // The download itself: either a direct GET of the presigned zip, or a
        // small JSON endpoint that hands back the signed URL.
        if (isZipUrl(url)) {
          postZipUrl(url);
        } else if (isDownloadIsh(url)) {
          p.then(function (res) {
            try {
              var ct = res.headers.get("content-type") || "";
              if (ct.indexOf("json") >= 0) {
                res.clone().json().then(function (j) {
                  var z = zipUrlFromJson(j);
                  if (z) postZipUrl(z);
                }).catch(function () {});
              }
            } catch (e) {}
          }).catch(function () {});
        }
      } catch (e) {}
      return p;
    };
  }

  // ---- patch XMLHttpRequest ----
  var OrigOpen = XMLHttpRequest.prototype.open;
  var OrigSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url) {
    try { this.__tbUrl = url; } catch (e) {}
    return OrigOpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function () {
    try {
      var xhr = this;
      if (xhr.__tbUrl && isZipUrl(xhr.__tbUrl)) postZipUrl(xhr.__tbUrl);
      xhr.addEventListener("load", function () {
        try {
          if (xhr.__tbUrl && isApiUrl(xhr.__tbUrl) &&
              (xhr.responseType === "" || xhr.responseType === "text")) {
            var norm = tasksFromText(xhr.responseText);
            note(xhr.__tbUrl, !!norm);
            if (norm) post(norm, xhr.__tbUrl);
          }
          if (xhr.__tbUrl && isDownloadIsh(xhr.__tbUrl) &&
              (xhr.responseType === "" || xhr.responseType === "text")) {
            var body = xhr.responseText;
            if (body && body.charAt(0) === "{") {
              var z = zipUrlFromJson(JSON.parse(body));
              if (z) postZipUrl(z);
            }
          }
        } catch (e) {}
      });
    } catch (e) {}
    return OrigSend.apply(this, arguments);
  };
})();
