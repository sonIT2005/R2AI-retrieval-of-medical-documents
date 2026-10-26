---
description: Lưu toàn bộ trạng thái trước khi hết context, trước /clear, hoặc trước khi chuyển sang tool khác (Antigravity…)
---
Cập nhật docs/PROGRESS.md đầy đủ theo đúng template, sao cho một agent KHÁC (Claude phiên mới, Antigravity, Codex…) đọc xong làm tiếp được mà không cần hỏi:
- Mục tiêu hiện tại, Điểm tốt nhất, Đang làm dở gì (file nào, hàm nào, trạng thái), Bước tiếp theo cụ thể (kèm lệnh chạy), Bẫy đã biết.
- "Đã xong" chỉ giữ 10 dòng mới nhất; phần cũ chuyển sang docs/archive/PROGRESS_ARCHIVE.md.
- Nếu codebase thay đổi cấu trúc trong phiên này → cập nhật docs/CODEMAP.md.
- Nếu Ponytail đã cài: chạy skill ponytail-debt để gom các comment `shortcut:` thành sổ nợ; ghi đường dẫn sổ nợ vào PROGRESS.md.
- git add các file liên quan (không add data/, results/, .env) và commit `wip: handoff <tóm tắt>`.
Cuối cùng in ra một prompt ngắn (≤ 5 dòng) để dán vào phiên mới hoặc tool khác.
