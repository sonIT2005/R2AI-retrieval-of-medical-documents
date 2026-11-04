@AGENTS.md

# Dành riêng cho Claude Code — "agent tree"

```
Opus (advisor, on call) ──► Opus — phiên chính · effort high · lên kế hoạch + quyết định
                                 │
                       hooks: luật cứng chạy bằng code (nạp trí nhớ, chặn đường dẫn bảo vệ)
                                 │
              giao việc cho subagents · effort medium (worker: Sonnet · còn lại: Opus)
        ┌────────────────────────┼─────────────────────────────┐
     worker                  explorer                     researcher
  sửa code + chạy test     đọc code, không sửa     hội đồng 8 model (council.py):
                                                     độc lập → phản biện chéo → bỏ phiếu
        └────────────────────────┼─────────────────────────────┘
                                 ▼
                 quay về phiên chính · effort high · review + verify
```

## Phân vai
- Phiên chính: lên kế hoạch, quyết định, giao việc, REVIEW + VERIFY kết quả trả về (tự chạy lại eval, đọc diff). Phiên chính hạn chế tự sửa code dài — giao worker.
- worker: thực thi một việc đã được định nghĩa rõ (file nào, xong khi nào).
- explorer: đọc code thay phiên chính, trả về tóm tắt có `file:dòng`.
- researcher: điều phối hội đồng nhiều model qua `tools/council.py`, kiểm chứng với code, viết SYNTHESIS.
- Tự sửa giữa chừng (/orchestrate): criteria-checker kiểm lại toàn bộ tiêu chí độc lập với worker; stage-reflector chẩn đoán lỗi cài đặt / giả định sai / hướng sai và quyết định TIẾP TỤC · ĐIỀU CHỈNH · ĐỔI HƯỚNG · DỪNG-HỎI. Hook Stop (orchestrate_guard.py) giữ vòng lặp chạy đến khi đạt tiêu chí tổng.
- Hỗ trợ: error-analyst (phân tích lỗi có số liệu), code-mapper (CODEMAP), scope-reviewer (soát phạm vi diff).

## Advisor (Opus thứ hai — độc lập với phiên chính)
Tham khảo advisor ở 3 thời điểm: TRƯỚC khi chốt một plan, khi cùng một lỗi lặp lại lần thứ 2, và TRƯỚC khi báo "xong" một mốc. Các lượt thường ngày thì không cần. Advisor chỉ cho lời khuyên; phiên chính tự quyết và tự áp dụng. Nếu bằng chứng trong code mâu thuẫn với lời khuyên, nói rõ mâu thuẫn thay vì làm theo.

## Lệnh
`/iterate` (1 thí nghiệm) · `/orchestrate` (việc lớn nhiều stage, tự sửa giữa chừng) · `/orchestrate-stop` · `/autoresearch` (thí nghiệm tự động qua đêm) · `/autoresearch-stop` · `/analyze` · `/council` · `/debate` · `/handoff` · `/map`

## Công cụ ngoài (nếu đã cài)
- Ponytail (plugin): viết ít code nhất cần thiết, không cắt validation/bảo mật. Review bằng skill ponytail-review; gom nợ bằng ponytail-debt. Khi luật Ponytail và AGENTS.md khác nhau, AGENTS.md (phạm vi, eval, file bảo vệ) thắng.
- Context7 (MCP, khai báo trong .mcp.json): tra tài liệu thư viện đúng phiên bản trước khi viết code dùng API lạ.
- Headroom: nén output công cụ (log train, JSON, kết quả grep) trước khi vào context. Nếu thấy dòng `Advisor unavailable` sau khi bật Headroom, báo tôi.

## Cách làm việc
- Đọc rộng → explorer hoặc code-mapper. Sửa code → worker. Giữ context phiên chính gọn.
- Thay đổi chạm > 3 file hoặc đụng kiến trúc → trình plan (plan mode), hỏi advisor, chờ tôi duyệt.
- Kết quả hội đồng là tín hiệu, không phải bằng chứng: các model ngoài không thấy code.
- Agent team chỉ dùng cho `/debate` hoặc feature web lớn chia rõ thư mục; mỗi teammate sở hữu thư mục riêng.
- Phiên đã dài → `/handoff` trước. Sau compact hoặc /clear, hook SessionStart tự nạp lại PROGRESS.md.
