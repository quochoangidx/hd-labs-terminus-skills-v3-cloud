/* Read the task open in the active Revise tab and export it into the selected
   workspace root. No dropdown or Downloads fallback: a complete export always
   lands under workspace/revision/<task_id>/. */
"use strict";

var els = {
  taskMeta: document.getElementById("taskMeta"),
  refresh: document.getElementById("refresh"),
  pathInput: document.getElementById("pathInput"),
  browse: document.getElementById("browse"),
  exportBtn: document.getElementById("exportBtn"),
  copyBtn: document.getElementById("copyBtn"),
  diffZipBtn: document.getElementById("diffZipBtn"),
  status: document.getElementById("status"),
  pathHint: document.getElementById("pathHint"),
  openTab: document.getElementById("openTab")
};

var DIR_KEY = "dirHandle";
var WORKSPACE_LAYOUT_VERSION = 1;
// state.current = { task, task_id, project, difficulty, task_category } | null
var state = { current: null, exportedTasks: {} };
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
  var taskId = currentTaskId();
  var hasTask = !!(on && taskId);
  var hasWorkspace = !!dirHandle;
  var wasExported = !!(hasTask && state.exportedTasks[taskId]);
  els.exportBtn.disabled = !(hasTask && hasWorkspace) || wasExported;
  els.copyBtn.disabled = !wasExported;
  els.diffZipBtn.disabled = !wasExported;
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
    els.taskMeta.textContent = "Hãy mở trang Revise của một task trên experts.snorkel-ai.com.";
    setExportEnabled(false);
    return;
  }
  var resp = await sendToTab(tab.id, { type: "tb-get-current-task" });
  if (!resp || !resp.ok) {
    state.current = null;
    els.taskMeta.textContent = "Không đọc được tab Revise — hãy tải lại trang rồi mở lại tiện ích.";
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
        "hãy bấm <b>Làm mới ⟳</b> sau khi trang tải xong, hoặc chuyển sang trang Revise/Submission của task.";
    els.taskMeta.innerHTML =
      (uuid ? '<span class="pill cur">UID ' + esc(uuid.slice(0, 8)) + "…</span>" : "") + why;
    setExportEnabled(false);
    return;
  }
  state.current = metaFromTask(resp.task);
  if (dirHandle && !state.exportedTasks[state.current.task_id]) {
    try {
      if (await completeExportExists(state.current.task_id)) {
        state.exportedTasks[state.current.task_id] = true;
        await saveExportedTasks();
      }
    } catch (e) {}
  }
  renderCurrent();
}

function updatePathHint() {
  if (dirHandle) {
    els.pathInput.value = dirHandle.name;
    els.pathHint.innerHTML = 'Đích xuất: “' + esc(dirHandle.name) +
      '/revision/&lt;task_id&gt;/”. ZIP upload sau khi sửa nằm trong “' +
      esc(dirHandle.name) + '/submissions/”.';
  } else {
    els.pathInput.value = "";
    els.pathHint.innerHTML = 'Chọn thư mục <b>workspace</b> của repo trước khi xuất.';
  }
  setExportEnabled(!!state.current);
}

/* ---------- persistence ---------- */

async function loadState() {
  var s = await chrome.storage.local.get(["exportedTasks", "workspaceLayoutVersion"]);
  if (s.workspaceLayoutVersion !== WORKSPACE_LAYOUT_VERSION) {
    state.exportedTasks = {};
    try { await TBIDB.del(DIR_KEY); } catch (e) {}
    await saveExportedTasks();
  } else {
    state.exportedTasks = s.exportedTasks || {};
  }
  // Drop the old accumulated capture list — the popup no longer uses it.
  try {
    chrome.storage.local.remove([
      "captures", "lastTaskId", "exportPath", "saveAs", "useFolder", "bundle"
    ]);
  } catch (e) {}
  try { dirHandle = await TBIDB.get(DIR_KEY); } catch (e) { dirHandle = null; }
  updatePathHint();
  refreshCurrentTask();
}

function saveExportedTasks() {
  return chrome.storage.local.set({
    exportedTasks: state.exportedTasks,
    workspaceLayoutVersion: WORKSPACE_LAYOUT_VERSION
  });
}

function buildRevisePrompt() {
  if (!state.current || !state.current.task) throw new Error("Chưa có task đang mở.");
  var root = (dirHandle ? dirHandle.name : "workspace") + "/revision";
  return TBGen.generateRevisePrompt(state.current.task, {
    exportRoot: root,
    submissionRoot: (dirHandle ? dirHandle.name : "workspace") + "/submissions",
    exportReady: !!(dirHandle && state.exportedTasks[currentTaskId()])
  });
}

function currentTaskId() { return state.current ? state.current.task_id : ""; }

/* ---------- folder picking (File System Access) ---------- */

async function pickFolder() {
  if (typeof window.showDirectoryPicker !== "function") {
    setStatus("Trình duyệt này không hỗ trợ chọn thư mục workspace.", "err");
    return;
  }
  try {
    var handle = await window.showDirectoryPicker({ mode: "readwrite" });
    dirHandle = handle;
    await TBIDB.set(DIR_KEY, handle);
    state.exportedTasks = {};
    await saveExportedTasks();
    updatePathHint();
    setStatus('Đã chọn “' + handle.name + '” làm thư mục workspace.', "ok");
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

function submissionSlug() {
  var zipName = submissionZipName() || (currentTaskId() + "_submission.zip");
  return zipName.replace(/\.zip$/i, "") || "task";
}

async function completeExportExists(taskId) {
  if (!dirHandle || !taskId) return false;
  var permission = await dirHandle.queryPermission({ mode: "readwrite" });
  if (permission !== "granted") return false;
  try {
    var revisionDir = await dirHandle.getDirectoryHandle("revision");
    var taskDir = await revisionDir.getDirectoryHandle(taskId);
    var slug = submissionSlug();
    await taskDir.getFileHandle(taskId + ".md");
    await taskDir.getFileHandle("revise-prompt.md");
    await taskDir.getDirectoryHandle(slug);
    var revisionsDir = await taskDir.getDirectoryHandle("revisions");
    await revisionsDir.getFileHandle(slug + "-source.zip");
    return true;
  } catch (e) {
    if (e && e.name === "NotFoundError") return false;
    throw e;
  }
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
  if (!resp || !resp.ok) throw new Error("Không thấy nút tải submission trên trang Revise.");
  if (resp.url) return resp.url;

  // Clicked the button; poll storage for the captured presigned URL.
  for (var i = 0; i < 60; i++) {
    var s = await chrome.storage.local.get(["zipUrl", "zipUrlAt"]);
    if (s.zipUrl && s.zipUrlAt && s.zipUrlAt >= since) return s.zipUrl;
    await new Promise(function (r) { setTimeout(r, 500); });
  }
  throw new Error("Hết thời gian chờ liên kết tải .zip (30s).");
}

// Full bundle: <workspace>/revision/<uuid>/ with the report, immutable source
// ZIP, and extracted task contents.
async function exportBundle(taskId) {
  var ok = await ensurePermission(dirHandle);
  if (!ok) throw new Error("permission-denied");
  if (await completeExportExists(taskId)) {
    return "Task đã có sẵn trong “" + dirHandle.name + "/revision/" + taskId + "/”.";
  }

  var t = state.current.task;
  var zipName = submissionZipName() || (taskId + "_submission.zip");
  var slug = submissionSlug();
  var url;
  try {
    setStatus("Đang lấy liên kết tải submission…");
    url = await resolveZipUrl();
  } catch (e) {
    throw new Error("Không tải được ZIP nguồn: " + e.message);
  }

  setStatus("Đang tải " + zipName + "…");
  var res = await fetch(url);
  if (!res.ok) throw new Error("Tải ZIP nguồn thất bại (HTTP " + res.status + ").");
  var buf = await res.arrayBuffer();
  var mb = (buf.byteLength / 1048576).toFixed(1);

  // Create the destination only after the complete source ZIP is in memory.
  // Existing directories are never reused, so local remediation work cannot
  // be overwritten if extension storage is cleared.
  var revisionDir = await dirHandle.getDirectoryHandle("revision", { create: true });
  try {
    await revisionDir.getDirectoryHandle(taskId);
    throw new Error("workspace/revision/" + taskId +
      " đã tồn tại nhưng chưa hoàn chỉnh; không ghi đè working tree.");
  } catch (e) {
    if (!e || e.name !== "NotFoundError") throw e;
  }
  var taskDir = await revisionDir.getDirectoryHandle(taskId, { create: true });
  var sourceZipName = slug + "-source.zip";
  var summary = "Đã ghi " + taskId + ".md + revise-prompt.md";
  try {
    setStatus("Đang ghi báo cáo và ZIP nguồn…");
    await writeFileInto(taskDir, taskId + ".md", TBGen.generateMarkdown(t));
    await writeFileInto(taskDir, "revise-prompt.md", TBGen.generateRevisePrompt(t, {
      exportRoot: dirHandle.name + "/revision",
      submissionRoot: dirHandle.name + "/submissions",
      exportReady: true
    }));
    var revisionsDir = await taskDir.getDirectoryHandle("revisions", { create: true });
    await writeFileInto(revisionsDir, sourceZipName, new Uint8Array(buf));

    setStatus("Đang giải nén vào " + slug + "/…");
    var n = await TBUnzip.forEach(buf, function (name, data) {
      return writeFileInto(taskDir, slug + "/" + name, data);
    }, function (done, total) {
      setStatus("Đang giải nén… " + done + "/" + total);
    });
    summary += ", lưu revisions/" + sourceZipName + " và giải nén " + n +
      " tệp → " + slug + "/ (" + mb + "MB)";
  } catch (e) {
    try { await revisionDir.removeEntry(taskId, { recursive: true }); } catch (cleanupError) {}
    throw new Error("Không thể hoàn tất bundle: " + e.message + ". Đã dọn thư mục xuất dở.");
  }
  return summary + " → “" + dirHandle.name + "/revision/" + taskId + "/”";
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
      : "Không thấy ô “Download difficulty check results” trên trang Revise.");
  }
  if (resp.url) return resp.url;

  for (var i = 0; i < 60; i++) {
    var st = await chrome.storage.local.get(["zipUrl", "zipUrlAt"]);
    if (st.zipUrl && st.zipUrlAt && st.zipUrlAt >= since) return st.zipUrl;
    await new Promise(function (r) { setTimeout(r, 500); });
  }
  throw new Error("Hết thời gian chờ liên kết tải difficulty (30s).");
}

// Difficulty results belong to the already-exported revision task.
async function downloadDifficultyArtifact() {
  var taskId = currentTaskId();
  if (!taskId) throw new Error("Chưa có task đang mở.");
  if (!dirHandle || !state.exportedTasks[taskId]) {
    throw new Error("Hãy xuất task vào workspace trước.");
  }

  setStatus("Đang lấy liên kết difficulty check…");
  var url = await resolveDifficultyZipUrl();
  var name = difficultyFileName(taskId, url);

  var ok = await ensurePermission(dirHandle);
  if (!ok) throw new Error("permission-denied");
  var revisionDir = await dirHandle.getDirectoryHandle("revision");
  var taskDir = await revisionDir.getDirectoryHandle(taskId);

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
      return "Đã giải nén " + n + " tệp → “" + dirHandle.name + "/revision/" + taskId +
             "/difficulty-check/” (" + mb + "MB)";
    } catch (e) {
      await writeFileInto(taskDir, name, new Uint8Array(buf));
      return "Giải nén lỗi: " + e.message + " — đã giữ " + name + " (" + mb + "MB)";
    }
  }

  await writeFileInto(taskDir, name, new Uint8Array(buf));
  return "Đã ghi " + name + " → “" + dirHandle.name + "/revision/" + taskId +
    "/” (" + mb + "MB)";
}

async function exportCurrent() {
  var taskId = currentTaskId();
  if (!taskId) throw new Error("Chưa có task đang mở.");
  if (!dirHandle) throw new Error("Hãy chọn thư mục workspace trước.");
  if (await completeExportExists(taskId)) {
    state.exportedTasks[taskId] = true;
    await saveExportedTasks();
    setExportEnabled(true);
    return "Task đã có sẵn trong “" + dirHandle.name + "/revision/" + taskId + "/”.";
  }
  var result = await exportBundle(taskId);
  state.exportedTasks[taskId] = true;
  await saveExportedTasks();
  setExportEnabled(true);
  return result;
}

/* ---------- events ---------- */

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
  els.exportBtn.disabled = true;
  setStatus("Đang xuất…");
  try {
    setStatus(await exportCurrent(), "ok");
  } catch (e) {
    setStatus("Xuất thất bại: " + e.message, "err");
  } finally {
    setExportEnabled(!!state.current);
  }
});

els.copyBtn.addEventListener("click", async function () {
  if (!currentTaskId()) return;
  try {
    await navigator.clipboard.writeText(buildRevisePrompt());
    setStatus("Đã sao chép prompt Revise vào clipboard.", "ok");
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
    setExportEnabled(!!state.current);
  }
});

els.openTab.addEventListener("click", function () {
  chrome.tabs.create({ url: chrome.runtime.getURL("popup.html") });
});

// Re-read the active tab when the popup/tab regains focus (helps in full-tab mode
// after navigating between tasks).
window.addEventListener("focus", function () { refreshCurrentTask(); });

loadState();
