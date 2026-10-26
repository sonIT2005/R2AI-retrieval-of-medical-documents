---
description: Việc lớn nhiều giai đoạn, TỰ SỬA GIỮA CHỪNG (kiểu Agentic Data Scientist) — plan có tiêu chí + dấu hiệu hướng sai → vòng lặp stage → kiểm tiêu chí độc lập → phản tư → điều chỉnh/đổi hướng → báo cáo. Hook Stop giữ vòng lặp chạy đến khi đạt tiêu chí.
argument-hint: "<mục tiêu, vd: dựng pipeline baseline + eval chuẩn cho bài phân loại văn bản>"
---
Mục tiêu: $ARGUMENTS

PHA 1 — LẬP KẾ HOẠCH (phiên chính)
1. Đọc AGENTS.md, docs/PROGRESS.md, docs/CODEMAP.md (cần đọc code → explorer). Có dữ liệu thì kiểm tra nhanh trước (kích thước, cột, phân phối nhãn, giá trị thiếu) — không lập plan trên giả định chưa kiểm.
2. Viết docs/STAGES.md theo template:
   - Tiêu chí tổng: đo được bằng lệnh.
   - 3–7 stage, mỗi stage có tiêu chí riêng.
   - DẤU HIỆU HƯỚNG SAI viết TRƯỚC khi làm (vd. "baseline stage 2 < 0.55 F1", "train loss không giảm sau 1 epoch", "cùng lỗi 2 lần"). Đây là điều kiện để được phép đổi hướng — viết trước để không ngụy biện sau.
   - Quyền tự quyết và ngân sách.
3. Soát plan tối đa 2 vòng: hỏi advisor; việc lớn → giao researcher chạy hội đồng preset `plan`, 1 vòng, `--no-search` trên STAGES.md. Trình tôi duyệt.
4. Tôi duyệt xong: đặt `Trạng thái: đang chạy`, rồi chạy `python3 .claude/hooks/orchestrate_guard.py --start <số lượt tối đa trong Ngân sách>`. Hook chỉ giữ phiên vừa chạy lệnh này; sau /clear chạy `--claim` để phiên mới nhận vòng lặp.

PHA 2 — VÒNG LẶP TỰ SỬA (hook Stop sẽ nhắc bạn chạy tiếp cho tới khi đạt tiêu chí tổng)
Mỗi lượt:
a. Lấy stage "chưa làm" đầu tiên, đặt nó "đang làm".
b. Giao worker: mục tiêu, file, tiêu chí stage, dấu hiệu hướng sai liên quan.
c. Worker trả XONG → review (skill ponytail-review nếu có + scope-reviewer); có mục phải sửa → trả worker (tính vào ngân sách 3 lượt/stage).
   Worker trả KẸT / GIẢ ĐỊNH SAI / VƯỢT NGÂN SÁCH → bỏ qua review, sang bước d ngay (đây là "sửa giữa chừng").
d. Gọi criteria-checker: kiểm LẠI toàn bộ tiêu chí (có thể tụt). Không tự đánh [x].
e. Gọi stage-reflector với báo cáo worker + kết quả checker.
f. Áp dụng quyết định:
   - TIẾP TỤC / ĐIỀU CHỈNH: sửa STAGES.md theo đề xuất (không đụng stage đã xong, không đổi tiêu chí tổng).
   - ĐỔI HƯỚNG: hỏi advisor trước. Nếu reflector tự tin thấp hoặc không có hướng thay thế rõ → giao researcher chạy hội đồng preset `cheap`, 1 vòng, để lấy phương án. Rồi áp dụng; stage lỗi thời đánh "bỏ".
   - DỪNG-HỎI: đặt `Trạng thái: chờ người dùng — <câu hỏi>` rồi dừng.
g. Ghi 1 dòng vào "Nhật ký quyết định" (lượt · sự kiện · tiêu chí đạt x/y · quyết định · lý do + bằng chứng). Commit. Cập nhật PROGRESS.md.

PHA 3 — TỔNG KẾT (khi mọi tiêu chí tổng đạt)
Hỏi advisor trước khi báo xong. Viết docs/reports/<ngày>-<tên>.md: kết quả + số liệu, các lần ĐIỀU CHỈNH/ĐỔI HƯỚNG và lý do (lấy từ Nhật ký), nợ kỹ thuật (`shortcut:`), việc tiếp theo; đề xuất mục cho PLAN.md. Đặt `Trạng thái: xong` (hook tự tắt vòng lặp).
