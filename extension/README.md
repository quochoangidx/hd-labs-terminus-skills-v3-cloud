# Trích xuất & Đóng gói đánh giá Task TB

Tiện ích Chrome/Chromium (Manifest V3) dành cho reviewer trên
`experts.snorkel-ai.com`. Nó thu thập **toàn bộ payload đánh giá** của một task
(Difficulty / Solution / Verification explanation, các check độ khó và chất
lượng, thống kê agent, rubric, revision notes) rồi kết xuất thành nhiều dạng,
đặt tên theo **UUID của task**, ví dụ `f2e38a51-e838-4cb9-ba30-d5e4ed4a8ea6`.

Từ bản này, tiện ích không chỉ ghi mỗi file `.md`. Khi bạn chọn một thư mục
(vd `workspaces`), mỗi lần xuất nó sẽ:

1. Tạo thư mục con tên đúng bằng **UUID** ngay trong thư mục bạn chọn:
   `workspaces/<uuid>/`.
2. Ghi báo cáo **`<uuid>.md`** ngay trong thư mục đó.
3. Tải file **submission `.zip`** của task.
4. **Giải nén** `.zip` vào một **thư mục con theo tên task** (tên lấy từ tên file
   `.zip`), vd `express-gateway-hardening-polars/`.

Kết quả gọn trong `workspaces/<uuid>/`, đúng hai mục cạnh nhau: thư mục task đã
giải nén và file `.md`.

## Cách thu thập dữ liệu

SPA của Snorkel tự gọi API đánh giá với đúng phiên đăng nhập (cookie phiên +
`x-id-token` JWT). Thay vì tự xác thực lại, tiện ích quan sát trong suốt phản
hồi đó:

```
GET /api/v1/assignment/{project_id}/review-{review_task_type_id}
    -> { tasks: [ { task_documents: [ { submission_document: {...} } ], ... } ] }
```

- `interceptor.js` (world MAIN) vá `fetch`/`XMLHttpRequest`, chuyển tiếp JSON
  khớp mẫu, và bắt luôn **liên kết tải `.zip`** (URL presigned S3/CDN có chữ ký
  `X-Amz-Signature`, hoặc endpoint JSON trả về URL tải).
- `relay.js` (world ISOLATED) **giữ payload review mới nhất của chính tab đó**
  trong bộ nhớ và trả về task đang mở khi popup hỏi; nó cũng chuyển URL `.zip`
  cho service worker và kích hoạt nút "Download file" của trang khi được yêu cầu.
- `background.js` chỉ lưu URL `.zip` mới nhất vào `chrome.storage.local` và huỷ
  bản tải `.zip` native trùng khi popup đang tự tải để giải nén (không còn lưu
  danh sách task).
- `popup.js` dựng Markdown/HTML (`generate.js`), tải `.zip`, và giải nén bằng
  `unzip.js`.

Markdown sinh ra bám sát `../output.md` **nhưng bỏ** phần "Source API" (§1) và
"Appendix" (§12), còn lại 10 mục đánh số lại.

**§10 Reviewer Decision** phụ thuộc kết quả review, giống panel trên portal:
- **Accept** -> chỉ hiện **Acceptance Notes**.
- **Needs Revision** -> hiện **Revision Notes** + **Error Categories**.

Quyết định đọc từ câu trả lời review (`radio-9552f`) nếu có, hoặc suy ra từ loại
note đang tồn tại. Mã error-category ánh xạ sang nhãn qua `form_schema` của chính
task (kèm bảng dự phòng sẵn trong code).

## Task đang mở trong tab

Popup chỉ làm việc với **đúng task đang mở trong tab Review** — không còn
dropdown, không còn danh sách/lưu trữ nhiều task. Khi mở popup, nó hỏi tab
`experts.snorkel-ai.com` đang hoạt động xem đó là task nào (đọc UUID từ ô
"Click to copy" hoặc từ URL) rồi lấy payload mà chính tab đó vừa nhận được từ
API review, hiển thị nhãn "đang mở trong tab". Nút **Làm mới ⟳** đọc lại tab khi
bạn chuyển sang task khác.

Nếu popup chưa đọc được dữ liệu task, hãy **tải lại trang Review** một lần để
interceptor bắt được payload.

## Cài đặt (unpacked)

1. Mở `chrome://extensions`.
2. Bật **Developer mode** (góc trên phải).
3. Bấm **Load unpacked**, chọn thư mục `extension/` này.
4. Ghim tiện ích để thấy nút trên thanh công cụ.

## Sử dụng

1. Trên `experts.snorkel-ai.com`, mở trang **Review** của một task. Tiện ích tự
   bắt payload (biểu tượng hiện số đếm). Giữ nguyên tab này khi xuất, vì bước tải
   `.zip` cần nút "Download file" trên trang.
2. Bấm nút tiện ích. Task đang mở đã được chọn sẵn.
3. Bấm **Chọn…** để trỏ tới thư mục đích (vd `workspaces`). Lựa chọn được ghi
   nhớ.
4. Bật ô **Tạo thư mục `<uuid>`: ghi .md và tải .zip, giải nén vào thư mục con
   theo tên task** (mặc định bật), rồi bấm **Xuất .md**.

Kết quả trong `workspaces/<uuid>/`:

```
workspaces/
└─ c9622b76-0ac0-4b18-8740-68063ad29141/
   ├─ c9622b76-...-29141.md              # báo cáo Markdown
   └─ express-gateway-hardening-polars/  # nội dung task đã giải nén
      ├─ environment/
      ├─ solution/
      ├─ tests/
      ├─ instruction.md
      └─ task.toml
```

Nếu giải nén lỗi (CORS, hết thời gian chờ…), tiện ích giữ lại file `.zip` gốc
trong `<uuid>/` làm dự phòng, còn `.md` vẫn được ghi.

## Các chế độ lưu

Tiện ích trình duyệt không thể lặng lẽ ghi vào một đường dẫn tuyệt đối bất kỳ,
nên có ba cách, và lựa chọn được **ghi nhớ** tới khi bạn đổi:

| Chế độ | Cách chọn | Ghi vào đâu | Đóng gói .zip |
|---|---|---|---|
| **Thư mục trực tiếp** | Bấm **Chọn…** rồi chọn thư mục (vd `workspaces`) | `<thư mục>/<uuid>/…` | ✅ tải + giải nén |
| **Thư mục con Downloads** | Gõ đường dẫn vào ô (vd `tb100-reviewer`) | `…/Downloads/<đường dẫn>/<uuid>.md` | ❌ chỉ ghi `.md` |
| **Hỏi mỗi lần** | Tích "Lưu thành… mỗi lần" | Hộp thoại native chọn vị trí từng lần | ❌ chỉ ghi `.md` |

Luồng đầy đủ (tạo thư mục + tải + giải nén) **chỉ chạy ở chế độ Thư mục trực
tiếp**, vì chỉ File System Access API mới cho phép tạo thư mục con và ghi các
file giải nén vào nơi bạn chọn. Hai chế độ còn lại chỉ ghi `.md` (giữ tương thích
cũ).

Ghi chú:
- Lần ghi đầu mỗi phiên, trình duyệt có thể hỏi xác nhận quyền ghi vào thư mục.
- Sửa ô nhập đường dẫn sẽ chuyển về chế độ **Thư mục con Downloads**.
- Chọn thư mục từ popup nhỏ có thể làm popup tự đóng trên vài bản Linux. Dùng
  **Mở trong tab ↗** để có trình chọn thư mục ổn định. Lựa chọn vẫn được lưu.
- **Sao chép** đưa Markdown lên clipboard, không ghi file.
- **Tải difficulty .zip** lấy riêng tệp ở ô "Download difficulty check results".
  Ở chế độ thư mục, nội dung được giải nén vào `<uuid>/difficulty-check/`; ngược
  lại tệp rơi vào `Downloads/<uuid>/`. Nút báo lỗi nếu task chưa chạy difficulty check.
- **Chép prompt Revise** dựng sẵn prompt sửa lỗi "Some test not passed + Instruction
  Sufficiency", điền sẵn slug task, bảng test 0/N, danh sách test pass mỏng (rerun
  risk) và toàn bộ khối feedback không rỗng. Bản xuất theo thư mục cũng ghi kèm
  `<uuid>/revise-prompt.md`.

## Cách tải và giải nén `.zip`

Bám theo đúng logic của `scripts/snorkel-submitter-extract.js` (bản CLI), nhưng
chạy trong trình duyệt:

1. Popup nhờ content script tìm liên kết `.zip`: đọc thẳng `href` trên thẻ tải
   nếu có, nếu không thì bấm nút **"Download file"** để SPA tạo URL presigned.
2. `interceptor.js` bắt URL presigned đó và lưu lại qua service worker.
3. Popup `fetch()` URL (được phép cross-origin nhờ `host_permissions` cho
   `*.amazonaws.com` / `*.cloudfront.net`), lấy `ArrayBuffer`.
4. Giải nén bằng `unzip.js` vào thư mục con `<tên-task>/`: đọc
   End-Of-Central-Directory, duyệt central directory, và bung từng entry (stored
   copy nguyên, deflate qua `DecompressionStream("deflate-raw")` của trình
   duyệt, không cần thư viện ngoài). Có hỗ trợ Zip64 cho archive lớn. Chỉ giữ
   lại file `.zip` gốc khi giải nén lỗi.
5. Trong lúc đó, bản tải native mà nút "Download file" kích hoạt bị service
   worker huỷ để tránh trùng (popup đã tự lấy bytes).

Nếu không lấy được URL (trang đổi cấu trúc, hết thời gian chờ, CORS chặn), bước
`.zip` được bỏ qua nhưng `.md` vẫn ghi, kèm thông báo lý do.

## CLI offline (cùng bộ generate)

`extract-cli.js` dùng lại `generate.js` để chuyển payload đã lưu hoặc file `.har`
thành các file `<uuid>.md`:

```bash
node extract-cli.js experts.snorkel-ai.com.har ./out
node extract-cli.js review-response.json ./out
```

Nó quét `.har` tìm mọi phản hồi review (base64 hoặc plain), khử trùng theo UUID
và ghi một file mỗi task.

## Danh sách file

| File | Vai trò |
|---|---|
| `manifest.json` | Manifest MV3 (quyền `storage`, `downloads`, `tabs`; host: snorkel-ai + amazonaws + cloudfront) |
| `interceptor.js` | Bắt mạng ở world MAIN (payload review + URL `.zip`) |
| `relay.js` | Cầu nối world ISOLATED: giữ payload tab, trả task đang mở, kích hoạt nút tải |
| `background.js` | Lưu URL `.zip` mới nhất, huỷ bản tải native trùng |
| `popup.html/.css/.js` | Giao diện xuất (task đang mở trong tab, thư mục, đóng gói .zip) |
| `generate.js` | Sinh Markdown báo cáo (dùng chung popup + CLI; còn helper HTML cho dùng ngoài) |
| `unzip.js` | Giải nén ZIP trong trình duyệt (stored + deflate-raw, hỗ trợ Zip64) |
| `idb.js` | IndexedDB để nhớ handle thư mục đã chọn |
| `extract-cli.js` | Bản CLI Node đi kèm |

## Xử lý sự cố

- **"Không tìm thấy tab experts.snorkel-ai.com đang mở"** khi xuất: mở lại trang
  Review của task trong một tab và giữ nó khi bấm xuất.
- **`.zip` bị bỏ qua**: kiểm tra trang Review có nút "Download file" xanh không;
  thử **Mở trong tab ↗** để popup không tự đóng giữa chừng khi tải file lớn.
- **Task đang mở chưa được chọn**: tải lại trang Review một lần để interceptor
  bắt payload, rồi mở lại popup.
- **File lớn (200MB+)**: dùng **Mở trong tab ↗**; tab đầy đủ không bị đóng khi mất
  focus như popup nhỏ.
