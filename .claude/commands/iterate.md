---
description: Chạy 1 vòng thí nghiệm — phiên chính lên kế hoạch → worker thực thi → phiên chính review + verify → log
argument-hint: "[ID mục trong PLAN — trống = mục đầu tiên]"
---
Mục cần làm: $ARGUMENTS (nếu trống, lấy mục "todo" đầu tiên trong docs/PLAN.md).

Phiên chính (bạn) — LÊN KẾ HOẠCH:
1. Viết ra: Giả thuyết · Thay đổi DUY NHẤT · Files sẽ sửa · Kết quả mong đợi · Tiêu chí bác bỏ. Ghi vào mục "Đang làm" của docs/PROGRESS.md.
2. Cần hiểu code trước? → giao explorer, chỉ nhận tóm tắt.
3. Kế hoạch đụng > 3 file hoặc đổi hướng → hỏi advisor trước khi làm.
4. Đảm bảo working tree sạch (commit hoặc stash).

Worker — THỰC THI:
5. Giao worker: mục tiêu, danh sách file, lệnh test/eval chứng minh xong.

Phiên chính — REVIEW + VERIFY:
6. Đọc diff (`git diff`), tự chạy lại lệnh eval chuẩn trong AGENTS.md — không chỉ tin con số worker báo.
7. So với best (cùng split, cùng seed). Chênh nhỏ hơn nhiễu seed → "không kết luận".
8. Ghi docs/EXPERIMENTS.md: 1 dòng + 2–3 câu kết luận VÌ SAO tăng/giảm.
9. Tốt hơn → commit `[exp-NNN] ...`, cập nhật "Điểm tốt nhất". Không tốt hơn → hoàn tác code, giữ log, đánh dấu mục PLAN "đã thử".
10. Review: skill ponytail-review (nếu Ponytail đã cài — bắt lỗi, bảo mật, test thiếu, kể cả ngoài diff) + scope-reviewer (phạm vi, đường dẫn bảo vệ, eval). Cập nhật PROGRESS.md.
11. Thí nghiệm thứ 3 liên tiếp không cải thiện → gọi stage-reflector với docs/EXPERIMENTS.md để chẩn đoán (lỗi cài đặt hay hướng sai), rồi đề xuất /analyze, /council stuck hoặc /debate theo kết quả.
