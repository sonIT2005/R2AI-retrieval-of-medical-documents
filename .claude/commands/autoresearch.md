---
description: Chạy thí nghiệm tự động qua đêm (port từ karpathy/autoresearch) — sửa đúng file cho phép → chạy có giới hạn thời gian → giữ nếu tốt hơn ngưỡng nhiễu, không thì hoàn tác → lặp tới deadline. Hook Stop giữ vòng lặp chạy.
argument-hint: "<tag, vd oct12> [mục tiêu ngắn]"
---
Tag / mục tiêu: $ARGUMENTS

Chế độ này dành cho phần "vặn" có thước đo rõ ràng (kiến trúc, loss, optimizer, augment, hyperparameter…) khi pipeline + eval chuẩn đã ổn. Không dùng để dựng pipeline mới (dùng /orchestrate). Hai chế độ không chạy cùng lúc — hook từ chối bật nếu chế độ kia đang chạy.

THIẾT LẬP (làm cùng tôi, một lần)
1. Kiểm tra điều kiện, thiếu cái nào thì dừng và báo:
   - Eval chuẩn đã chốt và `eval/**` đã bật trong .claude/protected_paths.txt; split cố định.
   - Có tập HOLDOUT riêng mà vòng lặp không bao giờ dùng để quyết định giữ/bỏ (chỉ đo khi kết thúc). Không có holdout thì đề xuất tách một phần từ train trước.
   - Đã đo nhiễu seed của baseline (chạy 2–3 seed). Ngưỡng nhiễu = khoảng 2 × độ lệch chuẩn.
   - Máy đang chạy Claude Code có GPU dùng được.
2. Thống nhất và ghi vào docs/autoresearch/<tag>/program.md:
   - File được sửa (1–2 file, vd `src/train.py`).
   - Lệnh chạy 1 thí nghiệm có giới hạn thời gian cố định, ghi log vào thư mục tag, vd `timeout 15m python src/train.py --time-budget-min 10 > docs/autoresearch/<tag>/run.log 2>&1`.
   - Cách đọc metric từ log (vd `grep "^val_f1:" docs/autoresearch/<tag>/run.log`), hướng tối ưu (max/min), ngưỡng nhiễu.
   - Deadline (vd 07:00) hoặc số thí nghiệm tối đa; lệnh đo holdout.
3. `git checkout -b autoresearch/<tag>` (nhánh chưa tồn tại). Bật vòng lặp:
   `python3 .claude/hooks/autoresearch_guard.py --start --tag <tag> --editable <file1,file2> --direction <max|min> --until <HH:MM> --noise <ngưỡng>`
   Từ lúc này hook chỉ cho sửa các file trong --editable (cộng thư mục kết quả và docs tiến độ).
4. Thí nghiệm đầu tiên luôn là baseline, chạy nguyên trạng.

VÒNG LẶP (không hỏi tôi có chạy tiếp không — hook Stop sẽ nhắc bạn chạy tiếp cho tới deadline)
Trong chế độ này phiên chính tự sửa code (không giao worker) để vòng lặp nhanh.
1. Xem git state, 15 dòng cuối results.tsv, và nguồn ý tưởng: docs/PLAN.md, SYNTHESIS gần nhất trong docs/council/, docs/research/, docs/analysis/.
2. Chọn MỘT ý tưởng, sửa chỉ các file được phép.
3. `git commit -am "ar: <mô tả ngắn>"`.
4. Chạy lệnh thí nghiệm (redirect toàn bộ output vào log, không dùng tee, không in log vào context).
5. Đọc metric bằng grep. Trống = crash → `tail -n 50` log. Lỗi vặt (typo, import) thì sửa và chạy lại, tối đa 2 lần; ý tưởng hỏng thì ghi crash và bỏ.
6. Ghi 1 dòng vào docs/autoresearch/<tag>/results.tsv (phân cách bằng TAB, không commit file này): `commit  metric  memory_gb  status  description`, status ∈ keep | discard | crash.
7. Tốt hơn best hiện tại một khoảng > ngưỡng nhiễu → keep (giữ commit). Không thì `git reset --hard HEAD~1`.
8. Tiêu chí đơn giản: cải thiện rất nhỏ mà thêm nhiều code rối thì không đáng giữ; xoá code mà kết quả bằng hoặc tốt hơn thì giữ.
9. Cứ 5 lần keep: chạy lại bản best với seed khác. Không giữ được mức cải thiện → coi là nhiễu, quay về bản best đã xác nhận trước đó, ghi chú vào results.tsv.
10. 10 lần discard liên tiếp: đừng tiếp tục vặn tham số nhỏ. Đọc lại phân tích lỗi, kết hợp các lần suýt thắng, hoặc thử thay đổi mạnh hơn (kiến trúc, loss, cách biểu diễn dữ liệu).
Thí nghiệm vượt quá 2 lần thời lượng dự kiến → kill, ghi crash, hoàn tác.

KẾT THÚC (khi hook báo hết giờ)
- Đo holdout cho baseline và best (lần duy nhất dùng holdout).
- Viết docs/autoresearch/<tag>/SUMMARY.md: baseline → best (val và holdout), các thay đổi được giữ và đóng góp ước tính của từng cái, cái nào có thể là nhiễu hoặc overfit val (val tăng mà holdout không tăng), ý tưởng tiếp theo.
- Thêm 1 dòng tổng hợp vào docs/EXPERIMENTS.md, đưa ý tưởng tiếp theo vào docs/PLAN.md, cập nhật PROGRESS.md.
- Không merge nhánh autoresearch vào nhánh chính — để tôi xem SUMMARY rồi quyết định.
