# Snorkel Sync — Chrome Extension

Lấy danh sách project từ Snorkel Experts, chọn 1 project, bấm **Đồng bộ** để kéo toàn bộ
assignments của project đó và ghi lên **Google Sheet**.

## Cơ chế

- **Token đăng nhập tự lấy:** extension không yêu cầu dán token. Service worker lắng nghe các
  request mà chính trang `experts.snorkel-ai.com` gửi đi (qua `webRequest`) để bắt header
  `authorization: Bearer ...` và `x-id-token`, lưu tạm trong `chrome.storage.session`.
  → Vì vậy bạn phải **đang đăng nhập và đã mở/refresh trang Snorkel** thì extension mới có token.
- **Kiểm tra đăng nhập:** nút Đồng bộ gọi `GET /api/v1/projects` với token đã bắt. Nếu 401/403
  → báo "chưa đăng nhập / token hết hạn".
- **Bắt buộc chọn project:** nút Đồng bộ chỉ bật khi đã chọn 1 project trong dropdown.
- **Ghi Google Sheet:** data gửi tới một Google Apps Script Web App (xem `apps-script/Code.gs`).
  Mỗi project = 1 tab; mỗi lần đồng bộ ghi đè bản mới nhất + thêm dòng vào tab `_SyncLog`.

## Cài đặt

### 1. Deploy Apps Script (Google Sheet)

1. Tạo / mở Google Sheet.
2. **Extensions → Apps Script**, dán nội dung `apps-script/Code.gs`.
3. **Deploy → New deployment → Web app**
   - Execute as: **Me**
   - Who has access: **Anyone**
4. Copy URL `.../exec`.

### 2. Cài extension

1. Chrome → `chrome://extensions`
2. Bật **Developer mode**.
3. **Load unpacked** → chọn thư mục `extension/`.

### 3. Cấu hình & dùng

1. Mở `https://experts.snorkel-ai.com`, đăng nhập, để trang load xong (để bắt token).
2. Mở popup extension → mục **Cài đặt** → dán URL Apps Script → **Lưu cài đặt**.
3. Badge hiển thị **Đã đăng nhập** → chọn project trong dropdown → bấm **Đồng bộ**.
4. Mở Google Sheet xem kết quả.

## Lưu ý

- Token Snorkel hết hạn ~1 giờ. Nếu báo lỗi 401, chỉ cần **refresh trang Snorkel** rồi đồng bộ lại.
- Icon trong `icons/` là placeholder màu xanh — thay bằng icon thật nếu muốn.
- `response.json` ở thư mục cha là dữ liệu mẫu để tham khảo cấu trúc API.
