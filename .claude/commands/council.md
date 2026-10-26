---
description: Nhiều model cùng suy nghĩ để cải thiện — subagent researcher điều phối hội đồng 8 model (độc lập → phản biện chéo ẩn danh → bỏ phiếu), kiểm chứng với code, rồi phiên chính review
argument-hint: "[preset: stuck | plan | cheap | all] [số vòng, mặc định 2] [no-search] [research pro|deep]"
---
Tham số: $ARGUMENTS (trống = preset mặc định trong config, 2 vòng, có tra cứu web ở vòng 1; ghi "no-search" để tắt tra cứu).

1. Giao cho subagent researcher, kèm: câu hỏi nghiên cứu cụ thể (rút từ PROGRESS/PLAN hiện tại), preset và số vòng ở trên.
2. Khi researcher trả về — bạn (phiên chính, effort high) REVIEW + VERIFY:
   - Mở SYNTHESIS.md. Tự kiểm tra lại 1–2 khẳng định quan trọng nhất trong code/log (không tin mù researcher hay hội đồng).
   - Cảnh báo leakage/bug → đưa lên đầu PLAN.
   - Hỏi advisor trước khi chốt plan mới nếu thay đổi hướng đi lớn.
3. Cập nhật docs/PLAN.md: chèn top 3–5 mục hợp lệ, cột Nguồn ghi `council-rXX/<ID>`; mục bị loại ghi vào "Đã loại" kèm lý do.
4. Cho tôi xem: cảnh báo (nếu có), bảng top 5 kèm điểm phiếu và nhãn kiểm chứng, đề xuất bước tiếp theo. KHÔNG triển khai khi tôi chưa đồng ý.
