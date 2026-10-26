# SYNTHESIS — council round_02 (2026-10-23)
Hội đồng: GPT-6 Luna (plan_critic), GLM-5.3 (simplifier), Gemini 4 Argon (pragmatist), Kimi K3 (alternative). 2 vòng, 4/4.

## Cảnh báo
- (GPT, GLM) F2_doc của G (0,2309) thấp hơn A (0,2375) dù cùng cấu hình → bản dựng lại trên máy này khác bản của đồng đội
  (thiếu db_extra ~20k trang crawl bổ sung). Không diff được vì không có file A. Chấp nhận: so sánh mọi bài mới với G/H.

## Đề xuất (đã kiểm chứng với code)
| Đề xuất | Phiếu | Nhãn code | Ghi chú |
|---|---|---|---|
| **Tách N_doc > N_chunk** (doc_id gần như 0 byte; chunk chỉ cho top ~100–115, L bậc thang) — M1-A, M4-A | 7–8 | **hợp lệ, có sẵn** `--chunk-docs N` (make_submission.py:142) | Định dạng nộp không bắt buộc mỗi doc có chunk |
| Bỏ tiếng Anh | (M4-A) | **đã kiểm**: H 40/60/0 = 0,2280 > G 0,2207 | +0,007 |
| Max-sim cấp chunk làm điểm tài liệu (dùng lại embedding chunk của bước chọn chunk) — M3-A, M4-B | 2+2 | hợp lệ; cache `results/chunk_cache.pkl` có vector chunk theo doc | cần đo offline: % argmax sau ký tự 2.000 |
| Vector đuôi (text[1800:3800]) cho tài liệu Việt dài — M2-C | 2 | hợp lệ; ~380k bài, ~1,2 giờ GPU | chỉ làm nếu max-sim cho thấy nội dung đúng hay nằm sau 2.000 |
| Reranker bge-reranker-v2-m3 trên top-200, dùng luôn để định tâm chunk — M1-B, GLM-C | 1 | hợp lệ, chưa có code | M (3–6 giờ GPU dùng chung) |
| Khử near-dup (MinHash) — Kimi-C | 0 | chưa kiểm | cổng offline <5% thì bỏ |

## Bất đồng
- Kimi: không cần nộp ZH-only riêng, suy được offline. GLM/Gemini: muốn 1 bài VI-only 100 để đo đóng góp Trung.
- Gemini đề xuất công thức trộn sigmoid 0,65/0,20/0,15 — GLM bác là quá phức tạp, cắt bỏ.

## Kế hoạch đã chọn
1. (đang làm) N_doc = 200 / 300 (80/120/0, 120/180/0), chunk cho 100 tài liệu đầu = đúng chunk của H → đo riêng tác dụng độ sâu.
2. L bậc thang + N_chunk ~110–120 để tận dụng ngân sách byte.
3. Max-sim chunk → rồi reranker nếu còn thời gian GPU.
