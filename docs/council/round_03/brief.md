# BRIEF cho hội đồng model — round 03
> Đội loi_cuda. LB public tốt nhất 0,3018 (hạng 9/50). Còn 6 ngày public (đến 31/10 07:00, 10 bài/ngày) + private (5 bài tổng).
> Mục tiêu: một BƯỚC NHẢY +0,05…+0,10, không phải tinh chỉnh +0,002.

## 1. Bài toán (tóm tắt)
- 1.200 câu hỏi y khoa tiếng Việt (trung vị 18 từ, tối đa 283) → nộp `relevant_docs` + `relevant_chunks` (doc_id + đoạn trích nguyên văn).
- Corpus tự crawl: 699k trang Việt (báo/bệnh viện/nhà thuốc, TB 3.553 ký tự), 237k trang Trung (hỏi đáp, TB 870 ký tự), 240k PubMed Anh (0 nhãn → bỏ).
- Điểm = (F2_doc + F2_chunk)/2, F2 = 5PR/(4P+R) theo từng câu rồi macro. Chunk đúng nếu LCS_token(c,g)/|g| ≥ 0,4 với chunk tham chiếu cùng doc_id (chunk nộp dài không bị phạt).
- Nhãn (chỉ thống kê tổng quát): trung vị ~60 tài liệu đúng/câu (5…190), ~1 chunk tham chiếu/tài liệu.
- Ràng buộc: model mở ≤15B phát hành trước 01/08/2026; 1 GPU RTX 5060 Ti 16GB, 128GB RAM; file nộp < 100 MB (Cloudflare 413) — bzip2/LZMA trong ZIP được chấp nhận; không có dev có nhãn.

## 2. Pipeline hiện tại (đạt 0,3018)
1. trafilatura → văn bản; câu hỏi dịch sang Trung bằng Qwen3-8B.
2. Lượt top-300: BM25 Việt (âm tiết), BGE-M3 dense 1 vector/tài liệu (2.000 ký tự đầu), BM25 Trung (jieba, câu dịch), BGE-M3 dense câu Việt→tài liệu Trung, câu Trung→tài liệu Trung.
3. RRF (k=60) trong từng ngôn ngữ (bm25_vi ×0,33, bm25_zh ×0,3), ghép 175 Việt + 75 Trung = 250 tài liệu/câu.
4. Chunk: chỉ cho 100 tài liệu đầu (85 Việt + 15 Trung), chọn đoạn 1.000 ký tự có cos BGE-M3 cao nhất rồi mở rộng nguyên văn tới 4.000 ký tự (Trung 2.000). F2_chunk/F2_doc ≈ 0,81.

## 3. Kết quả LB (đã nộp ~45 bài, những bài quan trọng)
| Thay đổi | Điểm | F2 doc | F2 chunk | P doc | R doc |
|---|---|---|---|---|---|
| Ban đầu (đồng đội) 100 tài liệu, chunk 1.000 | 0,1606 | 0,2375 | 0,0837 | 0,177 | 0,334 |
| + chunk 4.000 ký tự | 0,2207 | 0,2309 | 0,2104 | | |
| + 300 tài liệu, chunk chỉ cho 100 đầu | 0,2456 | 0,2736 | 0,2176 | 0,116 | 0,555 |
| + bm25_vi trọng số 1 → 0,33 | 0,2736 | 0,3038 | 0,2434 | 0,131 | 0,601 |
| + Việt/Trung 120/180 → 210/90 | 0,2934 | 0,3228 | 0,2641 | 0,140 | 0,630 |
| + chunk top-100 = 85 Việt/15 Trung | 0,2968 | 0,3228 | 0,2709 | | |
| **+ 250 tài liệu (175/75)** | **0,3018** | **0,3328** | 0,2709 | 0,157 | 0,599 |
- Số tài liệu (cấu hình mới): 400 → F2doc 0,302 · 350 → 0,313 · 300 → 0,323 · 250 → 0,333 (chưa thấy đỉnh).
- Không giúp / tệ hơn: BM25 thuần (P@30 0,156); vector phần sau tài liệu (max-sim cửa sổ 1.800–5.400 ký tự: −0,04); bge-reranker-v2-m3 xếp lại (đầu bài 1.500 ký tự: −0,012; RRF với nó: ±0); bm25_vi 0,1 hoặc 0,5 (tệ hơn 0,33); RRF k=30 (−0,003), k=100 (+0,001); bỏ bm25_zh (±0); chunk 95/5, 100/0 (tệ hơn 85/15).
- Bảng xếp hạng: 0,487 · 0,427 · 0,408 · 0,376 (tài khoản BTC) · 0,352 · 0,350 · 0,319 · 0,311 · **0,302 (bọn tôi)**.

## 4. Quan sát
- Doc là đòn bẩy: P doc chỉ 0,157 ở 250 tài liệu; F2 doc tăng khi GIẢM số tài liệu → xếp hạng chưa đủ sắc, và số tài liệu cố định cho mọi câu dù |G| dao động 5…190.
- Vector phần sau tài liệu làm TỆ đi → có thể nhãn được sinh từ phần đầu tài liệu (hoặc retriever gán nhãn chỉ nhìn đầu bài).
- Tài liệu Việt có precision cao hơn Trung nhiều; tỉ lệ tối ưu ~70/30.

## 5. Ý tưởng đang cân nhắc (chưa làm)
(a) Đổi/ghép embedding mạnh hơn: Qwen3-Embedding-0.6B/4B/8B (06/2025), multilingual-e5-large-instruct, BGE-M3 sparse + ColBERT (cùng model). Mã hoá lại 1,16M tài liệu: 0.6B ~2–3 giờ, 4B ~10+ giờ trên 5060 Ti.
(b) Số tài liệu THEO TỪNG CÂU (cắt theo phân bố điểm: cos/RRF so với top-1, số tài liệu vượt ngưỡng) thay vì 250 cố định.
(c) Reranker mạnh hơn: Qwen3-Reranker-4B/8B (06/2025), hoặc LLM Qwen3-8B chấm liên quan trên top-150.
(d) Mở rộng câu hỏi bằng Qwen3-8B (HyDE / từ khoá y khoa / tách câu hỏi dài nhiều ý).
(e) Tăng số chunk (110–120) nhờ LZMA nhỏ hơn bzip2 6%.

## 8. Câu hỏi cho hội đồng
1. Với 6 ngày, 1 GPU 16GB, ~60 lượt nộp: XẾP HẠNG (a)…(e) theo (kỳ vọng × xác suất thành công)/chi phí để có +0,05 trở lên. Hướng nào các đội 0,40+ nhiều khả năng đang dùng?
2. (b) cụ thể: tín hiệu nào từ điểm truy hồi (không dùng nhãn) dự đoán |G| tốt nhất? Thiết kế 2–3 bài nộp để hiệu chỉnh mà không overfit public.
3. Vì sao vector phần sau tài liệu lại làm tệ đi — điều đó gợi ý gì về cách nhãn được tạo và nên khai thác thế nào?
4. Chiến lược 5 bài private.
