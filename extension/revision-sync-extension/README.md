# Revision Task TB3

Tiện ích Chrome/Chromium (Manifest V3) dành cho luồng Revise trên
`experts.snorkel-ai.com`. Nó thu thập **toàn bộ payload task/revise** của một task
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

SPA của Snorkel tự gọi API task/revise với đúng phiên đăng nhập (cookie phiên +
`x-id-token` JWT). Thay vì tự xác thực lại, tiện ích quan sát trong suốt phản
hồi có cấu trúc task, bất kể route cụ thể của màn hình:

```
GET /api/v1/assignment/{project_id}/review-{review_task_type_id}
    -> { tasks: [ { task_documents: [ { submission_document: {...} } ], ... } ] }
```

- `interceptor.js` (world MAIN) vá `fetch`/`XMLHttpRequest`, chuyển tiếp JSON
  khớp mẫu, và bắt luôn **liên kết tải `.zip`** (URL presigned S3/CDN có chữ ký
  `X-Amz-Signature`, hoặc endpoint JSON trả về URL tải).
- `relay.js` (world ISOLATED) **giữ payload task/revise mới nhất của chính tab đó**
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

Popup chỉ làm việc với **đúng task đang mở trong tab Revise** — không còn
dropdown, không còn danh sách/lưu trữ nhiều task. Khi mở popup, nó hỏi tab
`experts.snorkel-ai.com` đang hoạt động xem đó là task nào (đọc UUID từ ô
"Click to copy" hoặc từ URL) rồi lấy payload mà chính tab đó vừa nhận được từ
API task/revise, hiển thị nhãn "đang mở trong tab". Nút **Làm mới ⟳** đọc lại tab khi
bạn chuyển sang task khác.

Nếu popup chưa đọc được dữ liệu task, hãy **tải lại trang Revise** một lần để
interceptor bắt được payload.

## Cài đặt (unpacked)

1. Mở `chrome://extensions`.
2. Bật **Developer mode** (góc trên phải).
3. Bấm **Load unpacked**, chọn thư mục `extension/` này.
4. Ghim tiện ích để thấy nút trên thanh công cụ.

## Sử dụng

1. Trên `experts.snorkel-ai.com`, mở trang **Revise** của một task. Tiện ích tự
   bắt payload (biểu tượng hiện số đếm). Giữ nguyên tab này khi xuất, vì bước tải
   `.zip` cần nút "Download file" trên trang.
2. Bấm nút tiện ích. Task đang mở đã được chọn sẵn.
3. Bấm **Chọn…** để trỏ tới thư mục `workspace` của repo. Lựa chọn được ghi
   nhớ.
4. Bấm **Xuất**. Đây là lúc extension tải ZIP, giữ bản nguồn và giải nén task.
5. Sau khi xuất thành công, nút **Sao chép** được mở để đưa prompt Revise đã
   điền sẵn vào clipboard.

Kết quả trong `workspace/revision/<uuid>/`, chia theo **vòng** (`v1`, `v2`, …).
Mỗi lần bấm **Xuất vN** sẽ lấy feedback + ZIP hiện tại trên platform vào một thư
mục vòng mới; các vòng cũ và `revisions/` không bao giờ bị ghi đè:

```
workspace/
├─ revision/
│  └─ d1ec597f-4793-4a1e-b1bf-683231e61cf8/
│     ├─ v1/
│     │  ├─ d1ec597f-...md                   # feedback vòng 1
│     │  ├─ revise-prompt.md                 # prompt của vòng 1
│     │  ├─ task-payload.json                # payload thô (debug)
│     │  ├─ tbrain-storm-...-source.zip      # ZIP platform vòng 1 (bất biến)
│     │  └─ tbrain-storm-.../                # task đã giải nén để sửa
│     ├─ v2/ …                               # sau khi upload rev1 và bị trả lại
│     └─ revisions/
│        ├─ tbrain-storm-...-rev1.zip        # bản sửa, đánh số xuyên suốt các vòng
│        └─ tbrain-storm-...-rev2.zip
└─ submissions/
   └─ tbrain-storm-....zip                   # bản mới nhất để upload
```

- Nếu ZIP và feedback giống hệt vòng mới nhất, Xuất không tạo vòng mới.
- **Sao chép vN** đưa prompt của vòng mới nhất: sửa trong `vN/<slug>/`, đọc
  `vN/<uuid>.md` (kèm feedback vòng trước để đối chiếu), và lưu `revM` kế tiếp
  chưa dùng trong `revisions/`.
- Bản xuất kiểu cũ (`<uuid>.md` nằm thẳng trong thư mục task, source ZIP trong
  `revisions/`) được tính là v1; vòng tiếp theo là `v2/`.
- **Tải difficulty .zip** giải nén vào `difficulty-check/` của vòng mới nhất.

## Quy tắc thư mục

Trình duyệt yêu cầu người dùng cấp quyền thư mục qua **Chọn…**. Extension xem
thư mục được chọn là root `workspace`; không có fallback sang Downloads hoặc
“Lưu thành…” vì các chế độ đó tạo prompt trỏ tới task chưa tồn tại.

Task chỉ được tải khi bấm **Xuất**. **Sao chép** và **Tải difficulty .zip** bị
khóa cho tới khi task đang mở đã xuất thành công vào
`workspace/revision/<task_id>/`.

Ghi chú:
- Khi nâng từ layout cũ, extension xóa lựa chọn thư mục cũ một lần và yêu cầu
  chọn lại `workspace` để tránh xuất nhầm ra ngoài `revision/`.
- Lần ghi đầu mỗi phiên, trình duyệt có thể hỏi xác nhận quyền ghi vào thư mục.
- Chọn thư mục từ popup nhỏ có thể làm popup tự đóng trên vài bản Linux. Dùng
  **Mở trong tab ↗** để có trình chọn thư mục ổn định. Lựa chọn vẫn được lưu.
- **Sao chép** đưa prompt Revise đã điền sẵn task, đường dẫn, feedback và quy
  ước đóng gói `source/revN` lên clipboard.
- **Tải difficulty .zip** lấy riêng tệp ở ô "Download difficulty check results".
  Nội dung được giải nén vào `revision/<uuid>/difficulty-check/`. Nút báo lỗi
  nếu task chưa chạy difficulty check.
- Prompt Revise điền sẵn đường dẫn task, báo cáo `.md`, ZIP nguồn bất biến,
  revision kế tiếp và ZIP upload ổn định. Agent tự đọc feedback từ báo
  cáo thay vì nhận hàng trăm dòng trong clipboard. Bản xuất cũng ghi kèm
  `revision/<uuid>/revise-prompt.md`.

## Cách tải và giải nén `.zip`

Bám theo đúng logic của `scripts/snorkel-submitter-extract.js` (bản CLI), nhưng
chạy trong trình duyệt:

1. Popup nhờ content script tìm liên kết `.zip`: đọc thẳng `href` trên thẻ tải
   nếu có, nếu không thì bấm nút **"Download file"** để SPA tạo URL presigned.
2. `interceptor.js` bắt URL presigned đó và lưu lại qua service worker.
3. Popup `fetch()` URL (được phép cross-origin nhờ `host_permissions` cho
   `*.amazonaws.com` / `*.cloudfront.net`), lấy `ArrayBuffer`.
4. Ghi ZIP gốc vào `revision/<uuid>/revisions/<slug>-source.zip`, rồi giải nén bằng
   `unzip.js` vào thư mục con `<tên-task>/`: đọc
   End-Of-Central-Directory, duyệt central directory, và bung từng entry (stored
   copy nguyên, deflate qua `DecompressionStream("deflate-raw")` của trình
   duyệt, không cần thư viện ngoài). Có hỗ trợ Zip64 cho archive lớn.
5. Trong lúc đó, bản tải native mà nút "Download file" kích hoạt bị service
   worker huỷ để tránh trùng (popup đã tự lấy bytes).

Nếu không lấy được URL hoặc giải nén thất bại, thao tác Xuất báo lỗi và các nút
phụ vẫn bị khóa; prompt không được coi là sẵn sàng khi task chưa có working tree.

## CLI offline (cùng bộ generate)

`extract-cli.js` dùng lại `generate.js` để chuyển payload đã lưu hoặc file `.har`
thành các file `<uuid>.md`:

```bash
node extract-cli.js experts.snorkel-ai.com.har ./out
node extract-cli.js revise-response.json ./out
```

Nó quét `.har` tìm mọi phản hồi task/revise (base64 hoặc plain), khử trùng theo UUID
và ghi một file mỗi task.

## Danh sách file

| File | Vai trò |
|---|---|
| `manifest.json` | Manifest MV3 (quyền `storage`, `downloads`, `tabs`; host: snorkel-ai + amazonaws + cloudfront) |
| `interceptor.js` | Bắt mạng ở world MAIN (payload task/revise + URL `.zip`) |
| `relay.js` | Cầu nối world ISOLATED: giữ payload tab, trả task đang mở, kích hoạt nút tải |
| `background.js` | Lưu URL `.zip` mới nhất, huỷ bản tải native trùng |
| `popup.html/.css/.js` | Giao diện xuất (task đang mở trong tab, thư mục, đóng gói .zip) |
| `generate.js` | Sinh Markdown báo cáo (dùng chung popup + CLI; còn helper HTML cho dùng ngoài) |
| `unzip.js` | Giải nén ZIP trong trình duyệt (stored + deflate-raw, hỗ trợ Zip64) |
| `idb.js` | IndexedDB để nhớ handle thư mục đã chọn |
| `extract-cli.js` | Bản CLI Node đi kèm |

## Xử lý sự cố

- **"Không tìm thấy tab experts.snorkel-ai.com đang mở"** khi xuất: mở lại trang
  Revise của task trong một tab và giữ nó khi bấm xuất.
- **`.zip` bị bỏ qua**: kiểm tra trang Revise có nút "Download file" xanh không;
  thử **Mở trong tab ↗** để popup không tự đóng giữa chừng khi tải file lớn.
- **Task đang mở chưa được chọn**: tải lại trang Revise một lần để interceptor
  bắt payload, rồi mở lại popup.
- **File lớn (200MB+)**: dùng **Mở trong tab ↗**; tab đầy đủ không bị đóng khi mất
  focus như popup nhỏ.
