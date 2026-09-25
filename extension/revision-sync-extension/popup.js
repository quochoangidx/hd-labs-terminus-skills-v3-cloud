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
  // exportedTasks[taskId] = latest round number already on disk (0/absent = none).
  var round = hasTask ? (state.exportedTasks[taskId] || 0) : 0;
  var wasExported = round > 0;
  // Export stays available: each click pulls the platform's current state
  // into the next round folder vN/.
  els.exportBtn.disabled = !(hasTask && hasWorkspace);
  els.exportBtn.textContent = "Xuất v" + (round + 1);
  els.copyBtn.disabled = !wasExported;
  els.copyBtn.textContent = wasExported ? "Sao chép v" + round : "Sao chép";
  els.diffZipBtn.disabled = !wasExported;
}

/* ---------- current task (read live from the active tab) ---------- */

// Turn a raw task payload into the compact shape the popup renders/exports.
// `pageUuid` (read off the open page) covers payloads that carry no task id.
function metaFromTask(t, pageUuid, pageZipName) {
  // Submission-page payloads can lack the task id and the zip filename. Stamp
  // them from the page so generate.js (report, prompt, slug) agrees with the
  // export folder instead of falling back to "unknown-task".
  if (!TBGen.rawTaskId(t) && pageUuid) t.task_id = pageUuid;
  var sd = {};
  try { sd = t.task_documents[0].submission_document || {}; } catch (e) {}
  if (pageZipName) {
    var up = sd.upload_a_zip_file;
    if (!up || typeof up !== "object") {
      sd.upload_a_zip_file = { filename: pageZipName };
    } else if (!up.filename && !(up.value && up.value.filename)) {
      up.filename = pageZipName;
    }
  }
  var id = TBGen.rawTaskId(t);
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
  if (!c || !c.task_id) {
    if (c) els.taskMeta.textContent = "Đã bắt được payload nhưng không tìm thấy UUID của task — hãy bấm Làm mới ⟳.";
    setExportEnabled(false);
    return;
  }
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
    if (seen.n && seen.urls && seen.urls.length) {
      why += "<br><small>API đã thấy:<br>" + seen.urls.map(esc).join("<br>") + "</small>";
    }
    els.taskMeta.innerHTML =
      (uuid ? '<span class="pill cur">UID ' + esc(uuid.slice(0, 8)) + "…</span>" : "") + why;
    setExportEnabled(false);
    return;
  }
  state.current = metaFromTask(resp.task, resp.uuid, resp.zipName);
  state.current.sourceUrl = String(resp.sourceUrl || "").split("?")[0];
  if (dirHandle) {
    try {
      var scan = await scanRounds(state.current.task_id, false);
      if (scan.latest !== (state.exportedTasks[state.current.task_id] || 0)) {
        state.exportedTasks[state.current.task_id] = scan.latest;
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

// Prompt for the latest round on disk, with the next free revN.
async function buildRevisePrompt() {
  if (!state.current || !state.current.task) throw new Error("Chưa có task đang mở.");
  var scan = await scanRounds(currentTaskId(), false);
  if (!scan.latest) throw new Error("Task chưa được xuất.");
  return TBGen.generateRevisePrompt(state.current.task,
    promptOptions(scan, scan.latest, submissionSlug()));
}

function promptOptions(scan, round, slug) {
  var ws = dirHandle ? dirHandle.name : "workspace";
  return {
    exportRoot: ws + "/revision",
    submissionRoot: ws + "/submissions",
    round: round,
    roundDir: roundDir(scan, round),
    prevRoundDir: round > 1 ? roundDir(scan, round - 1) : null,
    sourceZip: sourceZipRel(scan, round, slug),
    nextRev: scan.nextRev
  };
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

// True when the submission document carries at least one real answer besides
// the uploaded ZIP. A JSON-Schema-only capture ({type:[...]}) has none.
function hasAnswers(t) {
  var sd;
  try { sd = t.task_documents[0].submission_document || {}; } catch (e) { return false; }
  return Object.keys(sd).some(function (k) {
    if (k === "upload_a_zip_file") return false;
    var v = sd[k];
    if (v === null || v === undefined || v === "") return false;
    if (typeof v === "object" && !Array.isArray(v)) {
      var keys = Object.keys(v);
      return keys.length && !keys.every(function (x) {
        return ["type", "enum", "oneOf", "anyOf", "allOf", "$ref", "items"].indexOf(x) >= 0;
      });
    }
    return true;
  });
}

/* ---------- rounds: revision/<uuid>/vN/ ----------
 * Each Export pulls the platform's current feedback + submission ZIP into the
 * next round folder vN/ (report, prompt, payload, <slug>-source.zip, extracted
 * <slug>/). Local repairs are packed as revisions/<slug>-revM.zip, numbered
 * across rounds. An export from before rounds existed (flat <uuid>.md at the
 * task root, source in revisions/) counts as v1. */

async function scanRounds(taskId, create) {
  var empty = { taskDir: null, latest: 0, legacy: false, nextRev: 1 };
  if (!dirHandle || !taskId) return empty;
  if ((await dirHandle.queryPermission({ mode: "readwrite" })) !== "granted") return empty;
  var taskDir;
  try {
    var revisionDir = await dirHandle.getDirectoryHandle("revision", { create: !!create });
    taskDir = await revisionDir.getDirectoryHandle(taskId, { create: !!create });
  } catch (e) {
    if (e && e.name === "NotFoundError") return empty;
    throw e;
  }
  var latest = 0, legacy = false, maxRev = 0;
  for await (var entry of taskDir.entries()) {
    var name = entry[0], h = entry[1];
    var m = /^v(\d+)$/.exec(name);
    if (m && h.kind === "directory") {
      try { await h.getFileHandle(taskId + ".md"); latest = Math.max(latest, +m[1]); } catch (e) {}
    }
    if (name === taskId + ".md" && h.kind === "file") legacy = true;
  }
  if (legacy) latest = Math.max(latest, 1);
  try {
    var revs = await taskDir.getDirectoryHandle("revisions");
    for await (var r of revs.keys()) {
      var rm = /-rev(\d+)\.zip$/i.exec(r);
      if (rm) maxRev = Math.max(maxRev, +rm[1]);
    }
  } catch (e) {}
  return { taskDir: taskDir, latest: latest, legacy: legacy, nextRev: maxRev + 1 };
}

// Folder of round N relative to revision/<uuid>/ ("" = legacy flat v1).
function roundDir(scan, round) {
  return (round === 1 && scan.legacy) ? "" : "v" + round;
}

function sourceZipRel(scan, round, slug) {
  var d = roundDir(scan, round);
  return d ? d + "/" + slug + "-source.zip" : "revisions/" + slug + "-source.zip";
}

async function dirAt(taskDir, rel) {
  var dir = taskDir;
  var parts = rel ? rel.split("/") : [];
  for (var i = 0; i < parts.length; i++) dir = await dir.getDirectoryHandle(parts[i]);
  return dir;
}

async function readText(dir, name) {
  try { return await (await (await dir.getFileHandle(name)).getFile()).text(); }
  catch (e) { return null; }
}

async function readBytes(taskDir, rel) {
  var parts = rel.split("/");
  var name = parts.pop();
  try {
    var dir = await dirAt(taskDir, parts.join("/"));
    return new Uint8Array(await (await (await dir.getFileHandle(name)).getFile()).arrayBuffer());
  } catch (e) { return null; }
}

function sameBytes(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  for (var i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
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

// One round: pull the platform's current feedback + submission ZIP into
// revision/<uuid>/vN/. Earlier rounds and revisions/ are never touched.
async function exportBundle(taskId) {
  var ok = await ensurePermission(dirHandle);
  if (!ok) throw new Error("permission-denied");

  var t = state.current.task;
  if (!hasAnswers(t)) {
    throw new Error("dữ liệu bắt được không có câu trả lời/feedback nào (API: " +
      (state.current.sourceUrl || "?") + "). Hãy tải lại trang (F5) rồi bấm Làm mới ⟳.");
  }
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
  var bytes = new Uint8Array(buf);
  var mb = (buf.byteLength / 1048576).toFixed(1);
  var report = TBGen.generateMarkdown(t);

  // Touch the disk only after the complete source ZIP is in memory.
  var scan = await scanRounds(taskId, true);
  var taskDir = scan.taskDir;
  var where = dirHandle.name + "/revision/" + taskId + "/";

  // Same ZIP and same feedback as the latest round: nothing new to pull.
  if (scan.latest) {
    var lastDir = await dirAt(taskDir, roundDir(scan, scan.latest));
    if (sameBytes(bytes, await readBytes(taskDir, sourceZipRel(scan, scan.latest, slug))) &&
        (await readText(lastDir, taskId + ".md")) === report) {
      return { round: scan.latest, msg: "Platform chưa có gì mới so với v" + scan.latest +
        " — giữ nguyên “" + where + (roundDir(scan, scan.latest) || "") + "”." };
    }
  }

  var round = scan.latest + 1;
  var rel = "v" + round;
  var dir = await taskDir.getDirectoryHandle(rel, { create: true });
  var opts = promptOptions(scan, round, slug);
  try {
    setStatus("Đang ghi v" + round + ": báo cáo và ZIP nguồn…");
    await writeFileInto(dir, "task-payload.json", JSON.stringify(
      Object.assign({ _captured_from: state.current.sourceUrl || "" }, t), null, 2));
    await writeFileInto(dir, "revise-prompt.md", TBGen.generateRevisePrompt(t, opts));
    await writeFileInto(dir, slug + "-source.zip", bytes);

    setStatus("Đang giải nén vào " + rel + "/" + slug + "/…");
    var n = await TBUnzip.forEach(buf, function (name, data) {
      return writeFileInto(dir, slug + "/" + name, data);
    }, function (done, total) {
      setStatus("Đang giải nén… " + done + "/" + total);
    });
    // The report goes last: scanRounds only counts a vN that has it, so a
    // round interrupted before this point is never picked up as complete.
    await writeFileInto(dir, taskId + ".md", report);
    return { round: round, msg: "Đã tạo v" + round + ": " + taskId + ".md, revise-prompt.md, " +
      slug + "-source.zip và giải nén " + n + " tệp → " + slug + "/ (" + mb + "MB) → “" +
      where + rel + "/”" };
  } catch (e) {
    try { await taskDir.removeEntry(rel, { recursive: true }); } catch (cleanupError) {}
    throw new Error("Không thể hoàn tất v" + round + ": " + e.message + ". Đã dọn thư mục dở.");
  }
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
  var scan = await scanRounds(taskId, false);
  if (!scan.latest) throw new Error("Hãy xuất task vào workspace trước.");
  var rd = roundDir(scan, scan.latest);
  var taskDir = await dirAt(scan.taskDir, rd);
  var shown = dirHandle.name + "/revision/" + taskId + "/" + (rd ? rd + "/" : "");

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
      return "Đã giải nén " + n + " tệp → “" + shown + "difficulty-check/” (" + mb + "MB)";
    } catch (e) {
      await writeFileInto(taskDir, name, new Uint8Array(buf));
      return "Giải nén lỗi: " + e.message + " — đã giữ " + name + " (" + mb + "MB)";
    }
  }

  await writeFileInto(taskDir, name, new Uint8Array(buf));
  return "Đã ghi " + name + " → “" + shown + "” (" + mb + "MB)";
}

async function exportCurrent() {
  var taskId = currentTaskId();
  if (!taskId) throw new Error("Chưa có task đang mở.");
  if (!dirHandle) throw new Error("Hãy chọn thư mục workspace trước.");
  var result = await exportBundle(taskId);
  state.exportedTasks[taskId] = result.round;
  await saveExportedTasks();
  setExportEnabled(true);
  return result.msg;
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
    await navigator.clipboard.writeText(await buildRevisePrompt());
    setStatus("Đã sao chép prompt Revise v" + (state.exportedTasks[currentTaskId()] || "") + " vào clipboard.", "ok");
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
