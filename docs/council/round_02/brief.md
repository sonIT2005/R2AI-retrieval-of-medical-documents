# BRIEF cho hội đồng model — round 02
> Đội loi_cuda. LB public hiện 0,2207 (~hạng 12/57). Còn 8 ngày public (đến 31/10 07:00) + 4 ngày private (5 bài tổng).

## 1. Bài toán
- 1.200 câu hỏi y khoa tiếng Việt (trung vị 18 từ, tối đa 283) → mỗi câu nộp `relevant_docs` + `relevant_chunks` (doc_id + chunk_text trích NGUYÊN VĂN). Corpus là URL đội tự crawl: 698k trang Việt, 237k Trung, 240k PubMed Anh (đã làm sạch 1.175.104 = 98,4%).
- Điểm = (F2_doc + F2_chunk)/2, F2 = 5PR/(4P+R), tính từng câu rồi macro. Chunk đúng nếu LCS_token(c,g)/|g| ≥ 0,4 với chunk tham chiếu g cùng doc_id → chunk nộp dài không bị phạt.
- Thống kê nhãn (chỉ tổng quát): trung vị ~60 tài liệu đúng/câu (5–190), ~1 chunk tham chiếu/tài liệu, 0 tài liệu tiếng Anh.
- Ràng buộc: model mở ≤15B phát hành trước 01/08/2026; 10 bài/ngày; không có dev có nhãn (LB public 600 câu là thước đo duy nhất); cấm dò đáp án.
- **Ràng buộc mới phát hiện: Cloudflare của leaderboard trả 413 cho file > 100 MB.** Nén bzip2 trong ZIP được chấp nhận (nhỏ hơn deflate ~35%). Ngân sách ≈ 95 MB bzip2 ≈ 420 MB JSON cho 1.200 câu. Chữ Trung 3 byte/ký tự.
- Tài nguyên: 1 RTX 5060 Ti 16GB (dùng chung với job khác), 36 luồng, 128GB RAM. Mã hoá BGE-M3 toàn corpus mất ~4 giờ.

## 2. Pipeline hiện tại
1. trafilatura → văn bản sạch; nhóm ngôn ngữ theo website.
2. Câu hỏi dịch sang Trung/Anh bằng Qwen3-8B.
3. 8 lượt top-300 cấp TÀI LIỆU: BM25 (âm tiết / jieba) và BGE-M3 dense (**1 vector/tài liệu, chỉ 2.000 ký tự đầu, 512 token**). Lượt: bm25_vi, dense_vi_vi, dense_vi_zh, dense_vi_en, bm25_zh(dịch, ×0,3), dense_zh_zh, bm25_en(×0,3), dense_en_en.
4. RRF (k=60) trong từng nhóm ngôn ngữ, rồi ghép theo hạn mức cố định Việt/Trung/Anh.
5. Chunk: cắt ~1.000 ký tự (Trung 500), chọn 1 chunk/tài liệu theo cos BGE-M3 với câu hỏi, rồi **mở rộng nguyên văn ra hai phía tới L ký tự** (Trung L/2).
- Độ trùng top-40 giữa các lượt: bm25_vi∩dense_vi_vi = 15%; dense_vi_zh∩dense_zh_zh = 28%; bm25_zh∩dense_zh_zh = 15%.

## 3. Kết quả LB (public)
| Bài | Điểm | F2 doc | F2 chunk | P doc | R doc | P chunk | R chunk |
|---|---|---|---|---|---|---|---|
| A: 40 Việt+50 Trung+10 Anh, chunk 1.000 | 0,1606 | 0,2375 | 0,0837 | 0,177 | 0,334 | 0,067 | 0,115 |
| B: chỉ bm25_vi, 30 tài liệu, chunk 1.000 | 0,0549 | 0,0975 | 0,0122 | 0,156 | 0,104 | 0,019 | 0,014 |
| C: chỉ bm25_vi, 60 | 0,0701 | 0,1240 | 0,0163 | 0,125 | 0,153 | 0,017 | 0,021 |
| D: chỉ bm25_vi, 100 | 0,0793 | 0,1392 | 0,0193 | 0,102 | 0,194 | 0,014 | 0,028 |
| E: = C, chunk L=2.000 | 0,1007 | 0,1240 | 0,0775 | 0,125 | 0,153 | 0,081 | 0,095 |
| F: = C, chunk L=4.000 | 0,1171 | 0,1240 | 0,1101 | 0,125 | 0,153 | 0,111 | 0,135 |
| **G: = A dựng lại, chunk L=4.000** | **0,2207** | 0,2309 | 0,2104 | 0,174 | 0,322 | 0,160 | 0,289 |
| H: 40 Việt+60 Trung+0 Anh, L=4.000 | (đang chấm) | | | | | | |
- Các đội khác: #3 0,3516 (P doc 0,18, R doc 0,61, P chunk 0,25, R chunk 0,47); #4 0,3502 (0,24/0,47/0,28/0,41); #5 0,3187 (0,27/0,40/0,27/0,37). #1 0,7346 (P≈0,99) — không với tới bằng cách hợp lệ.
- Sai lầm đã rút ra: dòng "BM25 Baseline" 0,3764 (P doc 0,88) là bài nộp của TÀI KHOẢN BTC (tên tài khoản), không phải hệ BM25 thật → đừng suy luận gì về cách sinh nhãn từ nó.

## 4. Phân tích
- Chunk đã gần giải xong: F2_chunk/F2_doc = 0,91 ở L=4.000. **Đòn bẩy chính giờ là tài liệu**: R doc 0,32 so với 0,47–0,61 của #3/#4.
- Dense mạnh hơn BM25 rõ rệt ở tiếng Việt (bm25_vi thuần P@30 = 0,156 so với ~0,38 của nhóm Việt sau RRF).
- Precision biên của bm25_vi: 30→60 ≈ 0,093, 60→100 ≈ 0,068 — vẫn > F2/5 ≈ 0,046 → thêm tài liệu vẫn có lợi, nhưng bị chặn bởi ngân sách byte (150 tài liệu × L=4.000 = 119 MB bzip2, quá ngưỡng).
- Tài liệu Việt dài (TB 3.553 ký tự) nhưng vector chỉ nhìn 2.000 ký tự đầu.

## 5. Plan hiện tại (chưa làm)
1. Quét N lớn hơn (150–200) với L nhỏ hơn cho phần đuôi để vừa ngân sách.
2. Trọng số RRF trong nhóm Việt (dense > BM25).
3. Reranker bge-reranker-v2-m3 trên top-200.
4. Index dense cấp chunk (nhiều vector/tài liệu) thay vì 1 vector/2.000 ký tự đầu.

## 8. Câu hỏi cho hội đồng
1. Với 8 ngày, 1 GPU 16GB dùng chung và ~80 lượt nộp, **xếp thứ tự ưu tiên** các hướng tăng R doc từ 0,32 lên ≥ 0,5 mà không làm P doc rơi dưới ~0,15: (a) tăng N, (b) đổi trọng số/cách gộp RRF, (c) reranker cross-encoder, (d) dense cấp chunk / max-sim, (e) mở rộng câu hỏi bằng Qwen3-8B (HyDE, sinh từ khoá), (f) phân bổ Việt/Trung theo từng câu. Mỗi hướng: thí nghiệm rẻ nhất để kiểm, tiêu chí bác bỏ.
2. **Phân bổ ngân sách byte** (~420 MB JSON / 1.200 câu ≈ 350 KB/câu) giữa số tài liệu N và độ dài chunk L, khi F2_chunk/F2_doc đã 0,91 ở L=4.000 và 0,63 ở L=2.000: nên dùng L thay đổi theo thứ hạng tài liệu (dài cho top, ngắn cho đuôi)? Cách nào chọn vị trí chunk tốt hơn để L ngắn vẫn trúng?
3. Chiến lược private (5 bài tổng): nên giữ bài nào làm "an toàn"?
