// popup.js
const $ = (id) => document.getElementById(id);
const projectSelect = $("projectSelect");
const syncBtn = $("syncBtn");
const reloadBtn = $("reloadBtn");
const statusEl = $("status");
const loginBadge = $("loginBadge");

// Gửi message tới background, KÈM timeout để popup không bao giờ treo vô hạn
// nếu service worker chết hoặc network treo.
function send(msg, timeoutMs = 30000) {
  return new Promise((resolve) => {
    let done = false;
    const timer = setTimeout(() => {
      if (done) return;
      done = true;
      resolve({ ok: false, error: "Hết thời gian chờ (timeout). Thử lại hoặc reload trang Snorkel." });
    }, timeoutMs);
    try {
      chrome.runtime.sendMessage(msg, (res) => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        if (chrome.runtime.lastError) {
          resolve({ ok: false, error: chrome.runtime.lastError.message });
        } else {
          resolve(res ?? { ok: false, error: "Không nhận được phản hồi từ background." });
        }
      });
    } catch (e) {
      if (done) return;
      done = true;
      clearTimeout(timer);
      resolve({ ok: false, error: e.message });
    }
  });
}

function setStatus(text, kind = "info") {
  statusEl.textContent = text;
  statusEl.className = "status " + kind;
}

function setBadge(text, kind) {
  loginBadge.textContent = text;
  loginBadge.className = "badge badge-" + kind;
}

// Bật/tắt nút Đồng bộ — bắt buộc phải chọn project
function refreshSyncBtn() {
  syncBtn.disabled = !projectSelect.value;
}

async function checkLogin() {
  setBadge("Đang kiểm tra…", "unknown");
  const res = await send({ type: "CHECK_LOGIN" });
  if (res?.ok) {
    setBadge("Đã đăng nhập", "ok");
    return true;
  }
  setBadge("Chưa đăng nhập", "err");
  setStatus(res?.message || "Chưa đăng nhập Snorkel.", "err");
  return false;
}

async function loadProjects() {
  projectSelect.disabled = true;
  projectSelect.innerHTML = '<option value="">— Đang tải project… —</option>';
  refreshSyncBtn();

  const res = await send({ type: "GET_PROJECTS" });
  if (!res?.ok) {
    setStatus(res?.error || "Không lấy được danh sách project.", "err");
    projectSelect.innerHTML = '<option value="">— Lỗi tải project —</option>';
    return;
  }
  const projects = res.projects || [];
  if (projects.length === 0) {
    projectSelect.innerHTML = '<option value="">— Không có project —</option>';
    return;
  }
  // sắp xếp theo tên cho dễ tìm
  projects.sort((a, b) => a.name.localeCompare(b.name));
  projectSelect.innerHTML =
    '<option value="">— Chọn project —</option>' +
    projects
      .map((p) => `<option value="${p.id}" data-name="${escapeHtml(p.name)}">${escapeHtml(p.name)}</option>`)
      .join("");
  projectSelect.disabled = false;
  setStatus(`Đã tải ${projects.length} project. Chọn 1 project để đồng bộ.`, "info");
  refreshSyncBtn();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

async function doSync() {
  const projectId = projectSelect.value;
  if (!projectId) {
    setStatus("Bạn phải chọn project trước khi đồng bộ.", "err");
    return;
  }
  const projectName = projectSelect.selectedOptions[0]?.dataset.name || "";

  syncBtn.disabled = true;
  reloadBtn.disabled = true;

  // đếm giây để người dùng biết đang chạy chứ không treo
  let secs = 0;
  setStatus("⏳ Đang lấy dữ liệu & ghi Sheet… (0s)", "info");
  const ticker = setInterval(() => {
    secs++;
    setStatus(`⏳ Đang lấy dữ liệu & ghi Sheet… (${secs}s)`, "info");
  }, 1000);

  const res = await send({ type: "SYNC_PROJECT", projectId, projectName }, 90000);

  clearInterval(ticker);
  reloadBtn.disabled = false;
  refreshSyncBtn();

  if (!res?.ok) {
    setStatus("Lỗi: " + (res?.error || "không rõ"), "err");
    return;
  }
  const sheet = res.sheet || {};
  const added = sheet.added ?? 0;
  const skipped = sheet.skipped ?? 0;
  const received = sheet.received ?? res.total ?? 0;
  setStatus(
    `✓ Đồng bộ xong "${projectName}".\n` +
      `Lấy về: ${received} • Ghi mới: ${added} • Bỏ qua trùng: ${skipped}`,
    "ok"
  );
}

// ---- events ----
projectSelect.addEventListener("change", refreshSyncBtn);
syncBtn.addEventListener("click", doSync);

reloadBtn.addEventListener("click", async () => {
  reloadBtn.disabled = true;
  setStatus("Đang kiểm tra đăng nhập…", "info");
  const ok = await checkLogin();
  if (ok) await loadProjects();
  reloadBtn.disabled = false;
});

// ---- init ----
// KHÔNG fetch gì khi mở popup → popup hiện NGAY, không lag.
// Chỉ scan/fetch project khi người dùng bấm "Tải danh sách project".
setStatus('Bấm "Tải danh sách project" để bắt đầu.', "info");
