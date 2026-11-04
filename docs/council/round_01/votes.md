# Bảng xếp hạng đồng thuận — round_01

| Hạng | ID | Đề xuất | Của | Điểm | Người bầu |
|---|---|---|---|---|---|
| 1 | M3-A | "Một chunk duy nhất, dài nhất có thể" — và không bao giờ >1 chunk/tài liệu | qwen | 8 | M2, M4, M1 |
| 2 | M1-A | Nộp thuần danh sách bm25_vi đã lưu | grok | 6 | M2, M4, M3 |
| 3 | M3-B | Bỏ quota ngôn ngữ + bỏ RRF, xếp hạng BM25 toàn cục, quét N để vẽ H(N) và cắt ở ngưỡng p ≥ F2/5 | qwen | 5 | M2, M4, M1 |
| 4 | M1-B | Một chunk nguyên văn dài, giữ nguyên tập tài liệu | grok | 3 | M3 |
| 5 | M2-C | Trước tiên đo nhiễu LB, rồi mới chạy 1 thí nghiệm chunk dài hơn | minimax | 1 | M3 |
| 6 | M4-B | Bỏ dense/RRF và hạn mức ngôn ngữ — chỉ nộp BM25 Việt thuần với whole-doc chunk | deepseek | 1 | M1 |
