/* Popup logic: read the task open in the active Review tab, choose a remembered
   export folder, write <uuid>.md. No dropdown, no captured-task list — the popup
   always targets the single task currently shown in the tab. */
"use strict";

var els = {
  taskMeta: document.getElementById("taskMeta"),
  refresh: document.getElementById("refresh"),
  pathInput: document.getElementById("pathInput"),
  browse: document.getElementById("browse"),
  saveAs: document.getElementById("saveAs"),
  bundle: document.getElementById("bundle"),
  exportBtn: document.getElementById("exportBtn"),
  copyBtn: document.getElementById("copyBtn"),
  diffZipBtn: document.getElementById("diffZipBtn"),
  promptBtn: document.getElementById("promptBtn"),
  status: document.getElementById("status"),
  pathHint: document.getElementById("pathHint"),
  openTab: document.getElementById("openTab")
};

var DIR_KEY = "dirHandle";
// state.current = { task, task_id, project, difficulty, task_category } | null
var state = { current: null, exportPath: "", saveAs: false, useFolder: false, bundle: true };
var dirHandle = null;

function setStatus(msg, kind) {
  els.status.textContent = msg || "";
  els.status.className = "status" + (kind ? " " + kind : "");
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>]/g, function (ch) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[ch];
  });
}

function setExportEnabled(on) {
  els.exportBtn.disabled = !on;
  els.copyBtn.disabled = !on;
  els.diffZipBtn.disabled = !on;
  els.promptBtn.disabled = !on;
}

/* ---------- current task (read live from the active tab) ---------- */

// Turn a raw task payload into the compact shape the popup renders/exports.
function metaFromTask(t) {
  var id = t && t.task_id && t.task_id.id;
  var sd = {};
  try { sd = t.task_documents[0].submission_document || {}; } catch (e) {}
  return {
    task: t,
    task_id: id || "",
    project: t.project || "",
    difficulty: sd.difficulty || "",
    task_category: sd.task_category || t.task_category || ""
  };
}

function renderCurrent() {
  var c = state.current;
  if (!c || !c.task_id) { setExportEnabled(false); return; }
  els.taskMeta.innerHTML =
    '<span class="pill cur">đang mở trong tab</span>' +
    (c.difficulty ? '<span class="pill">' + esc(c.difficulty.toUpperCase()) + "</span>" : "") +
    (c.task_category ? '<span class="pill">' + esc(c.task_category) + "</span>" : "") +
    (c.project ? esc(c.project) + " · " : "") +
    '<span class="mono">' + esc(c.task_id) + "</span>";
  setExportEnabled(true);
}

// Ask the open experts.snorkel-ai.com tab for the task it is currently showing.
async function refreshCurrentTask() {
  var tab = await findSnorkelTab();
  if (!tab) {
    state.current = null;
    els.taskMeta.textContent = "Hãy mở trang Review của một task trên experts.snorkel-ai.com.";
    setExportEnabled(false);
    return;
  }
  var resp = await sendToTab(tab.id, { type: "tb-get-current-task" });
  if (!resp || !resp.ok) {
    state.current = null;
    els.taskMeta.textContent = "Không đọc được tab Review — hãy tải lại trang rồi mở lại tiện ích.";
    setExportEnabled(false);
    return;
  }
  if (!resp.task) {
    state.current = null;
    var uuid = resp.uuid || "";
    // The interceptor reports how many same-origin API responses it sniffed.
    // Zero means the content scripts loaded after the page fetched its data
    // (reload fixes it); non-zero with no marker hit means the payload never
    // came over the wire on this route.
    var seen = resp.seen || { n: 0, hits: [] };
    var why = seen.n === 0
      ? "chưa thấy phản hồi API nào — hãy <b>tải lại trang</b> (F5) rồi mở lại tiện ích."
      : "đã soi " + seen.n + " phản hồi API nhưng không có dữ liệu task; " +
        "hãy bấm <b>Làm mới ⟳</b> sau khi trang tải xong, hoặc chuyển sang trang Review/Submission của task.";
    els.taskMeta.innerHTML =
      (uuid ? '<span class="pill cur">UID ' + esc(uuid.slice(0, 8)) + "…</span>" : "") + why;
    setExportEnabled(false);
    return;
  }
  state.current = metaFromTask(resp.task);
  renderCurrent();
}

function updatePathHint() {
  if (state.useFolder && dirHandle) {
    if (els.bundle && els.bundle.checked) {
      els.pathHint.innerHTML = 'Xuất vào “' + esc(dirHandle.name) +
        '/<uuid>/”: ghi <b>.md</b>, tải <b>.zip</b> và <b>giải nén</b> vào thư mục con theo tên task. ' +
        'Cần mở sẵn tab Review của task để lấy được liên kết .zip.';
    } else {
      els.pathHint.innerHTML = 'Đang ghi <b>trực tiếp</b> vào thư mục “' + esc(dirHandle.name) +
        '”. Sửa ô nhập để chuyển lại thư mục con trong Downloads.';
    }
  } else {
    els.pathHint.innerHTML =
      "Văn bản nhập = thư mục con trong thư mục <b>Downloads</b> của trình duyệt. " +
      "Dùng <b>Chọn…</b> để ghi trực tiếp vào thư mục bất kỳ (bật gói .zip + giải nén).";
  }
}

/* ---------- persistence ---------- */

async function loadState() {
  var s = await chrome.storage.local.get(["exportPath", "saveAs", "useFolder", "bundle"]);
  state.exportPath = s.exportPath || "";
  state.saveAs = !!s.saveAs;
  state.useFolder = !!s.useFolder;
  state.bundle = s.bundle == null ? true : !!s.bundle;
  els.pathInput.value = state.exportPath;
  els.saveAs.checked = state.saveAs;
  els.bundle.checked = state.bundle;
  // Drop the old accumulated capture list — the popup no longer uses it.
  try { chrome.storage.local.remove(["captures", "lastTaskId"]); } catch (e) {}
  try { dirHandle = await TBIDB.get(DIR_KEY); } catch (e) { dirHandle = null; }
  if (!dirHandle) state.useFolder = false;
  updatePathHint();
  refreshCurrentTask();
}

function savePrefs() {
  return chrome.storage.local.set({
    exportPath: state.exportPath,
    saveAs: state.saveAs,
    useFolder: state.useFolder,
    bundle: state.bundle
  });
}

/* ---------- markdown build ---------- */

function buildMarkdown() {
  if (!state.current || !state.current.task) throw new Error("Chưa có task đang mở.");
  return TBGen.generateMarkdown(state.current.task);
}

// Where the export lands, so the prompt's paths match what is on disk: the
// picked folder's name, or the Downloads subfolder typed into the path box.
function exportRoot() {
  if (state.useFolder && dirHandle) return dirHandle.name;
  return sanitizeSubpath(els.pathInput.value);
}

function buildRevisePrompt() {
  if (!state.current || !state.current.task) throw new Error("Chưa có task đang mở.");
  return TBGen.generateRevisePrompt(state.current.task, { root: exportRoot() });
}

function currentTaskId() { return state.current ? state.current.task_id : ""; }
function fileNameFor(taskId) { return taskId + ".md"; }

/* ---------- folder picking (File System Access) ---------- */

async function pickFolder() {
  if (typeof window.showDirectoryPicker !== "function") {
    setStatus("Trình duyệt này không hỗ trợ ghi thư mục trực tiếp; sẽ dùng Downloads.", "err");
    return;
  }
  try {
    var handle = await window.showDirectoryPicker({ mode: "readwrite" });
    dirHandle = handle;
    await TBIDB.set(DIR_KEY, handle);
    state.useFolder = true;
    state.exportPath = handle.name;
    els.pathInput.value = handle.name;
    await savePrefs();
    updatePathHint();
    setStatus('Đã ghi nhớ thư mục “' + handle.name + '” để xuất trực tiếp.', "ok");
  } catch (e) {
    if (e && e.name === "AbortError") return; // người dùng đã hủy
    setStatus("Không mở được thư mục: " + e.message, "err");
  }
}

async function ensurePermission(handle) {
  var opts = { mode: "readwrite" };
  if ((await handle.queryPermission(opts)) === "granted") return true;
  return (await handle.requestPermission(opts)) === "granted";
}

/* ---------- export ---------- */

async function writeToFolder(taskId, md) {
  var ok = await ensurePermission(dirHandle);
  if (!ok) throw new Error("permission-denied");
  var fh = await dirHandle.getFileHandle(fileNameFor(taskId), { create: true });
  var w = await fh.createWritable();
  await w.write(md);
  await w.close();
}

/* ---------- bundle export (folder + zip + extract) ---------- */

// The submission zip's filename as stored in the current task payload.
function submissionZipName() {
  try {
    var t = state.current.task;
    var sd = t.task_documents[0].submission_document || {};
    var u = sd.upload_a_zip_file || {};
    return u.filename || "";
  } catch (e) { return ""; }
}

// Write `bytes` (string or Uint8Array) to a relative path under `rootDir`,
// creating intermediate folders. Leading "./" and any ".." segments are dropped.
async function writeFileInto(rootDir, relPath, bytes) {
  var parts = String(relPath).replace(/\\/g, "/").split("/")
    .filter(function (s) { return s && s !== "." && s !== ".."; });
  var name = parts.pop();
  if (!name) return;
  var dir = rootDir;
  for (var i = 0; i < parts.length; i++) {
    dir = await dir.getDirectoryHandle(parts[i], { create: true });
  }
  var fh = await dir.getFileHandle(name, { create: true });
  var w = await fh.createWritable();
  await w.write(bytes);
  await w.close();
}

function findSnorkelTab() {
  return new Promise(function (resolve) {
    chrome.tabs.query({ url: "https://experts.snorkel-ai.com/*" }, function (tabs) {
      if (!tabs || !tabs.length) return resolve(null);
      var active = tabs.filter(function (t) { return t.active; })[0];
      resolve(active || tabs[0]);
    });
  });
}

function sendToTab(tabId, msg) {
  return new Promise(function (resolve) {
    chrome.tabs.sendMessage(tabId, msg, function (resp) {
      if (chrome.runtime.lastError) return resolve(null);
      resolve(resp);
    });
  });
}

// Ask the page for the submission zip URL. Reads a direct href if present,
// otherwise clicks "Download file" and waits for the interceptor to capture
// the presigned URL (stored by the service worker as `zipUrl`).
async function resolveZipUrl() {
  var tab = await findSnorkelTab();
  if (!tab) throw new Error("Không tìm thấy tab experts.snorkel-ai.com đang mở.");

  var since = Date.now();
  await chrome.runtime.sendMessage({ type: "tb-suppress-zip", ms: 30000 });
  var resp = await sendToTab(tab.id, { type: "tb-resolve-zip" });
  if (!resp || !resp.ok) throw new Error("Không thấy nút tải submission trên trang Review.");
  if (resp.url) return resp.url;

  // Clicked the button; poll storage for the captured presigned URL.
  for (var i = 0; i < 60; i++) {
    var s = await chrome.storage.local.get(["zipUrl", "zipUrlAt"]);
    if (s.zipUrl && s.zipUrlAt && s.zipUrlAt >= since) return s.zipUrl;
    await new Promise(function (r) { setTimeout(r, 500); });
  }
  throw new Error("Hết thời gian chờ liên kết tải .zip (30s).");
}

// Full bundle: <picked>/<uuid>/ with the report (.md), the .zip, and its
// extracted contents.
async function exportBundle(taskId) {
  var ok = await ensurePermission(dirHandle);
  if (!ok) throw new Error("permission-denied");

  var taskDir = await dirHandle.getDirectoryHandle(taskId, { create: true });
  var t = state.current.task;

  // 1. Markdown report, sitting at <uuid>/<uuid>.md (no HTML).
  setStatus("Đang ghi báo cáo .md…");
  await writeFileInto(taskDir, taskId + ".md", TBGen.generateMarkdown(t));
  // Paste-ready remediation prompt, pre-filled with this task's 0/N table and
  // platform feedback blocks.
  await writeFileInto(taskDir, "revise-prompt.md",
    TBGen.generateRevisePrompt(t, { root: exportRoot() }));

  // 2. Fetch the submission zip. Its contents land in a subfolder named after
  //    the zip (the task slug): <uuid>/express-gateway-hardening-polars/…
  var zipName = submissionZipName() || (taskId + "_submission.zip");
  var slug = zipName.replace(/\.zip$/i, "") || "task";
  var summary = "Đã ghi " + taskId + ".md + revise-prompt.md";
  var url;
  try {
    setStatus("Đang lấy liên kết tải submission…");
    url = await resolveZipUrl();
  } catch (e) {
    return summary + ". Bỏ qua .zip: " + e.message;
  }

  setStatus("Đang tải " + zipName + "…");
  var res = await fetch(url);
  if (!res.ok) return summary + ". Tải .zip thất bại (HTTP " + res.status + ").";
  var buf = await res.arrayBuffer();
  var mb = (buf.byteLength / 1048576).toFixed(1);

  // 3. Extract into <uuid>/<slug>/. Keep the raw .zip only if extraction fails,
  //    so a successful run gives the clean two-item layout (<slug>/ + .md).
  try {
    setStatus("Đang giải nén vào " + slug + "/…");
    var n = await TBUnzip.forEach(buf, function (name, data) {
      return writeFileInto(taskDir, slug + "/" + name, data);
    }, function (done, total) {
      setStatus("Đang giải nén… " + done + "/" + total);
    });
    summary += ", giải nén " + n + " tệp → " + slug + "/ (" + mb + "MB)";
  } catch (e) {
    await writeFileInto(taskDir, zipName, new Uint8Array(buf));
    summary += ". Giải nén lỗi: " + e.message + " (đã giữ " + zipName + ")";
  }
  return summary + " → “" + dirHandle.name + "/" + taskId + "/”";
}

/* ---------- difficulty-check artifact (separate button) ---------- */

// The S3 key the platform stamps on the task once the difficulty check ran.
// Empty means the check has not produced an artifact yet.
function difficultyArtifactKey() {
  try {
    var sd = state.current.task.task_documents[0].submission_document || {};
    return sd.difficulty_check_artifact_s3_key || "";
  } catch (e) { return ""; }
}

function difficultyFileName(taskId, url) {
  var key = difficultyArtifactKey();
  var base = String(key).split("?")[0].split("/").pop();
  if (!base && url) base = String(url).split("?")[0].split("/").pop();
  if (!base || !/\.[a-z0-9]{1,8}$/i.test(base)) base = taskId + "_difficulty_check.zip";
  return base;
}

// Same handshake as resolveZipUrl, aimed at the difficulty-results card.
async function resolveDifficultyZipUrl() {
  var tab = await findSnorkelTab();
  if (!tab) throw new Error("Không tìm thấy tab experts.snorkel-ai.com đang mở.");

  var since = Date.now();
  await chrome.runtime.sendMessage({ type: "tb-suppress-zip", ms: 30000 });
  var resp = await sendToTab(tab.id, { type: "tb-resolve-difficulty-zip" });
  if (!resp || !resp.ok) {
    throw new Error(resp && resp.reason === "button-missing"
      ? "Nút tải difficulty đang bị vô hiệu (task chưa chạy difficulty check)."
      : "Không thấy ô “Download difficulty check results” trên trang Review.");
  }
  if (resp.url) return resp.url;

  for (var i = 0; i < 60; i++) {
    var st = await chrome.storage.local.get(["zipUrl", "zipUrlAt"]);
    if (st.zipUrl && st.zipUrlAt && st.zipUrlAt >= since) return st.zipUrl;
    await new Promise(function (r) { setTimeout(r, 500); });
  }
  throw new Error("Hết thời gian chờ liên kết tải difficulty (30s).");
}

// Folder mode: fetch the bytes ourselves and extract into <uuid>/difficulty-check/.
// Otherwise hand the presigned URL to the browser's download manager.
async function downloadDifficultyArtifact() {
  var taskId = currentTaskId();
  if (!taskId) throw new Error("Chưa có task đang mở.");

  setStatus("Đang lấy liên kết difficulty check…");
  var url = await resolveDifficultyZipUrl();
  var name = difficultyFileName(taskId, url);

  if (!(state.useFolder && dirHandle) || els.saveAs.checked) {
    var sub = state.useFolder ? "" : sanitizeSubpath(els.pathInput.value);
    var filename = (sub ? sub + "/" : "") + taskId + "/" + name;
    await new Promise(function (resolve, reject) {
      chrome.downloads.download(
        { url: url, filename: filename, saveAs: !!els.saveAs.checked, conflictAction: "overwrite" },
        function (id) {
          var err = chrome.runtime.lastError;
          if (err) reject(new Error(err.message)); else resolve(id);
        }
      );
    });
    return "Đã lưu Downloads/" + filename;
  }

  var ok = await ensurePermission(dirHandle);
  if (!ok) throw new Error("permission-denied");
  var taskDir = await dirHandle.getDirectoryHandle(taskId, { create: true });

  setStatus("Đang tải " + name + "…");
  var res = await fetch(url);
  if (!res.ok) throw new Error("Tải thất bại (HTTP " + res.status + ").");
  var buf = await res.arrayBuffer();
  var mb = (buf.byteLength / 1048576).toFixed(1);

  if (/\.zip$/i.test(name)) {
    try {
      setStatus("Đang giải nén vào difficulty-check/…");
      var n = await TBUnzip.forEach(buf, function (entry, data) {
        return writeFileInto(taskDir, "difficulty-check/" + entry, data);
      }, function (done, total) {
        setStatus("Đang giải nén… " + done + "/" + total);
      });
      return "Đã giải nén " + n + " tệp → “" + dirHandle.name + "/" + taskId +
             "/difficulty-check/” (" + mb + "MB)";
    } catch (e) {
      await writeFileInto(taskDir, name, new Uint8Array(buf));
      return "Giải nén lỗi: " + e.message + " — đã giữ " + name + " (" + mb + "MB)";
    }
  }

  await writeFileInto(taskDir, name, new Uint8Array(buf));
  return "Đã ghi " + name + " → “" + dirHandle.name + "/" + taskId + "/” (" + mb + "MB)";
}

function sanitizeSubpath(p) {
  return String(p || "")
    .trim()
    .replace(/\\/g, "/")
    .split("/")
    .filter(function (seg) { return seg && seg !== "." && seg !== ".."; })
    .join("/");
}

function downloadViaBrowser(taskId, md, forceSaveAs) {
  var sub = state.useFolder ? "" : sanitizeSubpath(els.pathInput.value);
  var filename = (sub ? sub + "/" : "") + fileNameFor(taskId);
  var url = "data:text/markdown;charset=utf-8," + encodeURIComponent(md);
  return new Promise(function (resolve, reject) {
    chrome.downloads.download(
      { url: url, filename: filename, saveAs: !!forceSaveAs, conflictAction: "overwrite" },
      function (id) {
        var err = chrome.runtime.lastError;
        if (err) reject(new Error(err.message));
        else resolve({ id: id, filename: filename });
      }
    );
  });
}

async function exportCurrent() {
  var taskId = currentTaskId();
  if (!taskId) throw new Error("Chưa có task đang mở.");
  var md = buildMarkdown();
  var name = fileNameFor(taskId);

  // Full bundle: folder mode + bundle toggle. Falls back to plain .md below
  // if the folder loses write permission mid-run.
  if (state.useFolder && dirHandle && els.bundle.checked && !els.saveAs.checked) {
    try {
      return await exportBundle(taskId);
    } catch (e) {
      if (e.message !== "permission-denied") throw e;
    }
  }

  if (els.saveAs.checked) {
    await downloadViaBrowser(taskId, md, true);
    return "Đã lưu " + name;
  }
  if (state.useFolder && dirHandle) {
    try {
      await writeToFolder(taskId, md);
      return "Đã ghi " + name + " → “" + dirHandle.name + "”";
    } catch (e) {
      if (e.message !== "permission-denied") throw e;
      // mất quyền ghi thư mục → chuyển sang Downloads
      var d = await downloadViaBrowser(taskId, md, false);
      return "Bị từ chối quyền ghi thư mục; đã lưu vào Downloads/" + d.filename;
    }
  }
  var res = await downloadViaBrowser(taskId, md, false);
  return "Đã lưu Downloads/" + res.filename;
}

/* ---------- events ---------- */

els.pathInput.addEventListener("input", function () {
  // Manual edit means the user wants a Downloads subfolder, not the picked folder.
  state.useFolder = false;
  state.exportPath = els.pathInput.value;
  savePrefs();
  updatePathHint();
});

els.saveAs.addEventListener("change", function () {
  state.saveAs = els.saveAs.checked;
  savePrefs();
});

els.bundle.addEventListener("change", function () {
  state.bundle = els.bundle.checked;
  savePrefs();
  updatePathHint();
});

els.browse.addEventListener("click", pickFolder);

els.refresh.addEventListener("click", function () {
  setStatus("Đang đọc task đang mở…");
  refreshCurrentTask().then(function () {
    // The reason lives in taskMeta (it knows what the interceptor saw); don't
    // paper over it with a generic status line.
    setStatus(state.current ? "" : "Chưa đọc được task — xem lý do ở trên.", state.current ? "" : "err");
  });
});

els.exportBtn.addEventListener("click", async function () {
  if (!currentTaskId()) return;
  setStatus("Đang xuất…");
  try {
    setStatus(await exportCurrent(), "ok");
  } catch (e) {
    setStatus("Xuất thất bại: " + e.message, "err");
  }
});

els.copyBtn.addEventListener("click", async function () {
  if (!currentTaskId()) return;
  try {
    await navigator.clipboard.writeText(buildMarkdown());
    setStatus("Đã sao chép Markdown vào clipboard.", "ok");
  } catch (e) {
    setStatus("Sao chép thất bại: " + e.message, "err");
  }
});

els.diffZipBtn.addEventListener("click", async function () {
  if (!currentTaskId()) return;
  els.diffZipBtn.disabled = true;
  try {
    setStatus(await downloadDifficultyArtifact(), "ok");
  } catch (e) {
    setStatus("Tải difficulty thất bại: " + e.message, "err");
  } finally {
    els.diffZipBtn.disabled = false;
  }
});

els.promptBtn.addEventListener("click", async function () {
  if (!currentTaskId()) return;
  try {
    await navigator.clipboard.writeText(buildRevisePrompt());
    setStatus("Đã chép prompt Revise vào clipboard.", "ok");
  } catch (e) {
    setStatus("Chép prompt thất bại: " + e.message, "err");
  }
});

els.openTab.addEventListener("click", function () {
  chrome.tabs.create({ url: chrome.runtime.getURL("popup.html") });
});

// Re-read the active tab when the popup/tab regains focus (helps in full-tab mode
// after navigating between tasks).
window.addEventListener("focus", function () { refreshCurrentTask(); });

loadState();
