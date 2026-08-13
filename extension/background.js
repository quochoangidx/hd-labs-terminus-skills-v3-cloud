/*
 * Service worker: brokers the submission-zip download during a bundle export.
 * Task/revise payloads are no longer stored here — the popup reads the task open in
 * the active tab straight from that tab's content script.
 */
"use strict";

// Set by the popup for the duration of a bundle export so we can swallow the
// duplicate native download that clicking the page's "Download file" button
// kicks off (the popup fetches the bytes itself to extract them).
var suppressZipUntil = 0;

chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
  if (msg && msg.type === "tb-zip-url" && msg.url) {
    chrome.storage.local.set({ zipUrl: msg.url, zipUrlAt: Date.now() });
    return; // fire and forget
  }
  if (msg && msg.type === "tb-suppress-zip") {
    suppressZipUntil = Date.now() + (msg.ms || 20000);
    return;
  }
});

// Cancel the browser's own zip download during a bundle export; the popup is
// pulling the bytes over fetch to extract them, so the native copy is noise.
if (chrome.downloads && chrome.downloads.onCreated) {
  chrome.downloads.onCreated.addListener(function (item) {
    if (Date.now() > suppressZipUntil) return;
    var name = (item.filename || item.url || "");
    if (/\.zip(\?|$)/i.test(name)) {
      try { chrome.downloads.cancel(item.id); } catch (e) {}
    }
  });
}
