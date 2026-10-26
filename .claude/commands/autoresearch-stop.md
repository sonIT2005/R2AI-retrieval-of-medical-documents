---
description: Dừng /autoresearch ngay (hook Stop không ép chạy tiếp nữa, gỡ giới hạn file được sửa)
---
Chạy `python3 .claude/hooks/autoresearch_guard.py --stop`. Nếu đang có thí nghiệm dở: kill tiến trình, `git reset --hard` về commit keep gần nhất, ghi dòng "crash — dừng tay" vào results.tsv. Sau đó viết SUMMARY.md theo mục KẾT THÚC trong /autoresearch (bỏ qua holdout nếu tôi không yêu cầu).
