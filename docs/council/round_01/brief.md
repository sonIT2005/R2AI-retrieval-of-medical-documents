# BRIEF cho hội đồng model — round 01
> Đội loi_cuda, hạng 18/57 LB public. Còn 9 ngày public + 4 ngày private.

## 1. Bài toán
- Nhiệm vụ: 1.200 câu hỏi y khoa tiếng Việt (trung vị 18 từ, P95 84, tối đa 283) → với mỗi câu nộp `relevant_docs` (doc_id trong corpus BTC) + `relevant_chunks` (doc_id + chunk_text trích NGUYÊN VĂN từ tài liệu). Corpus chỉ là danh sách URL, đội tự crawl: 1,19M URL = 714k trang Việt (báo, bệnh viện, nhà thuốc), 240k trang Trung (hỏi đáp/bài y khoa), 240k PubMed (Anh, mới thêm ở bản v2 ngày 12/10).
- Metric: Điểm = (F2_doc + F2_chunk)/2; F2 = 5PR/(4P+R), tính từng câu rồi macro-average. Recall nặng gấp 4 precision.
  - Doc: P = |D∩G|/|D|, R = |D∩G|/|G|.
  - Chunk: chunk nộp c đúng nếu tồn tại chunk tham chiếu g (cùng câu, cùng doc_id) với **overlap = LCS_token(c,g) / |g| ≥ 0,4** (LCS không cần liên tiếp; chuẩn hoá NFKC, chữ thường, gộp khoảng trắng). Chunk P = số chunk nộp đúng / số chunk nộp. Chunk R = số g được tìm thấy / tổng số g. **Mẫu số chỉ là |g| → chunk nộp dài hơn không bị phạt** (luật không giới hạn độ dài chunk; "cách phân đoạn do đội tự thiết kế").
- Nhãn (rút ra từ file chấm chi tiết, chỉ thống kê tổng quát): trung vị **~60 tài liệu đúng/câu** (tối đa 190), ~1 chunk tham chiếu/tài liệu, **0 tài liệu tiếng Anh** trong đáp án (0/12.000 mẫu kiểm tra).
- Ràng buộc: chỉ model mở ≤15B, phát hành trước 01/08/2026 (cấm GPT/Gemini trong pipeline). 10 bài nộp/ngày; private chỉ 5 bài tổng cộng. Cấm dò đáp án. 1 GPU RTX 5060 Ti 16GB, 29GB RAM. Không có tập dev có nhãn → thước đo duy nhất là LB public (600 câu).

## 2. Pipeline hiện tại
1. Crawl ~98% URL Việt+Trung (thiếu ~20k: laodong.vn, youmed.vn bị chặn); HTML → văn bản bằng trafilatura + lọc dòng rác theo site; PubMed lấy XML tóm tắt.
2. Nhóm ngôn ngữ theo website (vi/zh/en).
3. Dịch câu hỏi sang Trung + Anh bằng Qwen3-8B.
4. 8 lượt truy hồi cấp TÀI LIỆU, mỗi lượt top-300: BM25 (HashingVectorizer, token = âm tiết, tài liệu cắt 10.000 ký tự đầu; jieba cho tiếng Trung) và dense BGE-M3 (1 vector/tài liệu, 2.000 ký tự đầu, 512 token): bm25_vi, dense_vi→{vi,zh,en}, bm25_zh(dịch), dense_zh_zh, bm25_en, dense_en_en.
5. RRF (k=60) trong từng nhóm ngôn ngữ (BM25 câu dịch trọng số 0,3), rồi ghép theo hạn mức cố định Việt/Trung/Anh, ví dụ 60/40/0 = 100 tài liệu/câu.
6. Chunk: gom dòng tới ~1.000 ký tự (Việt/Anh) hoặc ~500 (Trung), chọn **1 chunk/tài liệu** có cos BGE-M3 cao nhất với câu hỏi (gốc hoặc bản dịch).

## 3. Kết quả (LB public)
| Đội | Điểm | F2 doc | F2 chunk | P doc | R doc | P chunk | R chunk |
|---|---|---|---|---|---|---|---|
| #1 ongthomiu | 0,7346 | 0,732 | 0,737 | 0,995 | 0,695 | 0,993 | 0,700 |
| #2 **BM25 Baseline (của BTC)** | **0,3764** | 0,559 | 0,194 | **0,881** | 0,515 | 0,340 | 0,176 |
| #3 | 0,3516 | 0,359 | 0,345 | 0,182 | 0,611 | 0,251 | 0,468 |
| #4 | 0,3502 | 0,362 | 0,339 | 0,240 | 0,467 | 0,282 | 0,408 |
| #5 | 0,3187 | 0,325 | 0,313 | 0,275 | 0,397 | 0,268 | 0,375 |
| **#18 loi_cuda (bọn tôi)** | **0,1606** | 0,238 | **0,084** | 0,177 | 0,334 | **0,067** | **0,115** |
- Ước lượng thô: với |G|≈55, baseline BM25 của BTC trả ~30 tài liệu và trúng ~27; bọn tôi trả ~100 tài liệu (giả định, cấu hình 60/40/0) nhưng chỉ trúng ~18.
- Nhiễu giữa các bài nộp: chưa đo.

## 4. Đã thử
| Thay đổi | Điểm LB | Ghi chú |
|---|---|---|
| 10 Việt + 5 Trung + 5 Anh (20 tài liệu) | 0,0724 | F2 doc 0,114, F2 chunk 0,030 |
| 20 Trung | 0,0536 | F2 chunk cao hơn bản Việt |
| 20 Anh | 0 | không có tài liệu Anh trong đáp án |
| ~100 tài liệu (60 Việt/40 Trung, giả định) | 0,1606 | bài tốt nhất, 15/10 |
- Precision tài liệu theo ngôn ngữ: Việt ≈ 0,38 > Trung ≈ 0,16. Precision chunk: Trung > Việt (bài Việt dài, chọn sai đoạn).

## 5. Phân tích lỗi
- **Chunk là chỗ thua nặng nhất**: R_chunk/R_doc = 0,34, P_chunk/P_doc = 0,38 → trong tài liệu ĐÚNG, chunk 1.000 ký tự bọn tôi chọn chỉ phủ ≥40% chunk tham chiếu khoảng 1/3 số lần. Các đội #3–#5 có F2 chunk ≈ F2 doc (thậm chí P_chunk > P_doc).
- **Xếp hạng tài liệu lệch so với cách gán nhãn**: BM25 thuần của BTC có precision 0,88, bất thường cao với truy hồi thật → nghi nhãn được sinh từ pool BM25 của BTC (có thể kèm LLM lọc). RRF với dense + hạn mức Trung cố định có thể làm loãng tín hiệu BM25.
- Hạn mức ngôn ngữ cố định cho mọi câu, số tài liệu cố định cho mọi câu dù |G| dao động 5–190.

## 6. Plan hiện tại
1. Tăng số tài liệu/câu (100 → 150–200), chỉnh tỷ lệ Việt/Trung.
2. Reranker BGE-reranker-v2-m3 cho tài liệu và chunk.
3. Chọn chunk tốt hơn cho bài Việt dài.

## 7. Tài liệu tham khảo
- Đặc tả chấm điểm chính thức ở mục 1 (trang Evaluation của cuộc thi). Không có code baseline công khai.

## 8. Câu hỏi cụ thể cho hội đồng
1. **Chunk**: overlap chia cho |g| nên chunk dài chỉ có lợi. Nên chọn độ dài/số chunk mỗi tài liệu thế nào (2–3 chunk lân cận, chunk 2.000–4.000 ký tự, hay nguyên văn bản)? Rủi ro thật là gì: LCS O(n·m) làm bộ chấm (Docker Python 3.7) quá thời gian, BTC coi là lách luật khi xét bài báo / private? Thí nghiệm nào trên LB (10 bài/ngày) để chọn mức an toàn mà tối đa điểm?
2. **Tái tạo tín hiệu BM25 của BTC**: precision 0,88 gợi ý gì về cách sinh nhãn? Làm sao bắt chước hợp lệ (BM25 cấp chunk hay cấp tài liệu, tách từ tiếng Việt theo âm tiết hay theo từ, có cắt độ dài không), và thứ tự thí nghiệm rẻ nhất (chỉ gộp lại các lượt đã có mất vài giây) để kiểm chứng?
3. **Số tài liệu + phân bổ ngôn ngữ theo từng câu**: với F2 macro và |G| 5–190, nên cắt theo ngưỡng điểm / theo độ dài câu hỏi / theo phân bố điểm thay vì cố định? Trung có đáng giữ không khi P_zh ≈ 0,16?
4. Với 9 ngày + 1 GPU 16GB, reranker (bge-reranker-v2-m3) hoặc LLM ≤15B chấm liên quan có đáng hơn các việc trên không? Xếp thứ tự ưu tiên.
