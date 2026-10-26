---
description: Tắt vòng lặp /orchestrate ngay (hook Stop sẽ không ép chạy tiếp nữa)
---
Chạy `python3 .claude/hooks/orchestrate_guard.py --stop`, đặt `Trạng thái: dừng — <lý do người dùng dừng>` trong docs/STAGES.md, ghi 1 dòng vào Nhật ký quyết định, cập nhật PROGRESS.md. Báo lại: stage nào đang dở, tiêu chí nào đã/chưa đạt.
