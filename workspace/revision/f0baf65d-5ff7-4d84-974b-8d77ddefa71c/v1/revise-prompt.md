Revise v1 (Sound Verifier 1 Major, 3 Minor)
Task: workspace/revision/f0baf65d-5ff7-4d84-974b-8d77ddefa71c/v1/tbrain-car-rental-agreement-billing
Platform feedback v1: workspace/revision/f0baf65d-5ff7-4d84-974b-8d77ddefa71c/v1/f0baf65d-5ff7-4d84-974b-8d77ddefa71c.md
Yêu cầu:

* Dùng task-revise-flag-remediation. Đọc "Blocking stage" trước và xử lý theo
grading flow:
   * panel/quality check: sửa theo ledger, quét cả nhóm lỗi (blueprint §5), không chỉ đúng ca được nêu;
   * test 0/8: chạy bộ lọc 0/8, bỏ trap chứ không tiết lộ, dọn khắp fixtures/explanations/rubric;
   * BASE: dừng lại và đề xuất task thay thế, không làm khó thêm;
   * human review: sửa đúng từng note.
* Khôi phục từ đúng source zip platform đã chấm; mỗi finding phải có receipt tái hiện
trên bản cũ và receipt đóng trên bản mới. Finding không tái hiện được thì dispute kèm receipt.
* Ưu tiên "stop promising" với promise không thuộc core; giữ nguyên phần khó.
* Nếu chỉ sửa tests: giữ instruction, environment, solution byte-identical;
clearance chỉ trục sound_verifier; không re-probe.
* Nếu thu hẹp core: re-probe 1 cặp trên claude-opus-5 (dừng nếu không gọi được Opus 5).
* Tự chạy hết các bước bắt buộc (closure gates, clearance, panel receipt,
preflight --emit-zip --panel-report), không hỏi lại.
* Cập nhật 3 explanation, difficulty, rubric và SUBMISSION note khớp bản mới.

Lưu file:

* Không sửa/ghi đè workspace/revision/f0baf65d-5ff7-4d84-974b-8d77ddefa71c/v1/tbrain-car-rental-agreement-billing-source.zip.
* Lưu bản mới tại workspace/revision/f0baf65d-5ff7-4d84-974b-8d77ddefa71c/revisions/tbrain-car-rental-agreement-billing-rev1.zip (không ghi đè rev cũ).
* Đồng bộ đúng bytes sang workspace/submissions/tbrain-car-rental-agreement-billing.zip để upload.

Báo cáo ngắn: stage bị chặn, bảng finding → quyết định (backed/dropped/disputed),
trục đã clearance, có re-probe không, đường dẫn ZIP.
