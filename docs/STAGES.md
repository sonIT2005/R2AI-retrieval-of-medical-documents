# STAGES — <mục tiêu>
> /orchestrate tạo và cập nhật file này. Hook Stop đọc dòng "Trạng thái" và mục "Tiêu chí tổng" để quyết định vòng lặp chạy tiếp hay dừng.
> Chỉ criteria-checker đánh [x], kèm bằng chứng. Vòng trước: <docs/archive/STAGES-<ngày>-<tên>.md nếu có>

Trạng thái: lập kế hoạch
<!-- Các giá trị: lập kế hoạch · đang chạy · chờ người dùng — <câu hỏi> · dừng — <lý do> · xong -->

## Bối cảnh (<ngày giờ>)
- Điểm hiện tại: <local / LB, hạng> · mục tiêu và vì sao
- Harness dùng để chấm: <lệnh eval chuẩn / cổng so sánh>
- Đã loại (đừng lặp): <hướng đã thử thất bại, xem EXPERIMENTS>
- Ý chưa thử: <nguồn, ước lượng khả năng thành công>

## Quyền tự quyết & ngân sách
- Tự điều chỉnh stage chưa làm: có
- Tự đổi hướng (khi chạm dấu hiệu hướng sai): có   <!-- "không" = mọi lần đổi hướng đều hỏi người dùng -->
- Tối đa 3 lượt sửa / stage · tối đa 40 lượt cho cả vòng lặp

## Tiêu chí tổng
- [ ] <đo được, vd: `python eval/evaluate.py --run results/baseline` chạy được và xuất metrics.json + predictions.csv>
- [ ] <vd: macro-F1 local ≥ 0.70 trên split cố định>

## Dấu hiệu hướng sai (viết TRƯỚC khi làm)
- <vd: baseline stage 2 có macro-F1 < 0.55 → hướng đặc trưng hiện tại không đủ>
- <vd: train loss không giảm sau 1 epoch dù model overfit được 1 batch nhỏ>
- Cùng một lỗi lặp lại 2 lần trong một stage

## Stage 1: <tên> — chưa làm
<!-- trạng thái stage: chưa làm · đang làm · xong · bỏ (lý do) -->
- Mục tiêu:
- File dự kiến:
- Tiêu chí (lệnh → kết quả mong đợi):
  - [ ] `<lệnh>` → <kết quả>
- Rủi ro:
- Bằng chứng:

## Nhật ký quyết định
| Lượt | Sự kiện | Tiêu chí đạt | Quyết định | Lý do + bằng chứng |
|---|---|---|---|---|
