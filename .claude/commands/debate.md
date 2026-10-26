---
description: Agent team tranh luận các giả thuyết khi điểm bị kẹt (cần bật CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1)
---
Bối cảnh: điểm đang kẹt. Đọc docs/PROGRESS.md, docs/EXPERIMENTS.md, báo cáo mới nhất trong docs/analysis/ và SYNTHESIS gần nhất trong docs/council/ (nếu có).

Tạo một agent team gồm 3–4 teammates. Mỗi teammate giữ MỘT giả thuyết khác nhau về nguyên nhân, đặt tên rõ ràng, ví dụ:
- hyp-data: dữ liệu/nhãn (nhiễu nhãn, mất cân bằng, train–test shift)
- hyp-eval: eval/leakage/bug pipeline
- hyp-model: giới hạn model/kiến trúc/loss
- hyp-train: thiết lập train (lr, epoch, augment, tiền xử lý)

Luật cho teammates:
- Chỉ ĐỌC code và chạy phân tích nhanh (mỗi lệnh < 5 phút). KHÔNG sửa code trong src/, KHÔNG train dài.
- Tìm bằng chứng ủng hộ VÀ bác bỏ giả thuyết của mình; nhắn tin phản biện giả thuyết của teammate khác như một cuộc tranh luận khoa học.
- Mỗi người ghi vào file riêng docs/analysis/debate_<ngày>/<tên>.md (tránh ghi đè nhau).

Lead (bạn): đợi tất cả xong rồi mới tổng hợp vào docs/analysis/debate_<ngày>/CONCLUSION.md: giả thuyết còn đứng vững, bằng chứng, 1–2 thí nghiệm quyết định → chèn lên đầu docs/PLAN.md. Không tự triển khai.
Nếu agent teams chưa được bật, làm tương tự bằng các subagent chạy song song.
