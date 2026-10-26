# M4 = glm (z-ai/glm-5.3) — vai: simplifier — vòng 2

## 1. Nhận xét từng thành viên
- **M1**: Điểm mạnh nhất vòng này — suy luận `P_chunk > P_doc ⇒ N_chunk < N_doc` (từ số liệu #3/#4) biến câu hỏi format chưa biết thành đòn bẩy gần miễn phí, cộng phát hiện lệch `F2_doc` 0,2375→0,2309 giữa bài A và G (nondeterminism khi "dựng lại"). | Lỗ hổng: Bước 1 đổi **cùng lúc** quota + trọng số RRF + dựng lại pipeline → không quy kết được nguyên nhân; quota 140 Vi/40 Zh dựa trên precision biên của **bm25_vi thu thuần**, chưa từng đo của fused; Đề xuất B nhồi ≥3 tham số tự do chưa kiểm (cửa sổ trượt triple-sum, fusion 0,65/0,35, ngưỡng động N(q)∈[70,230]).
- **M2**: Điểm mạnh — kỷ luật phương pháp tốt nhất: đo byte trên **file ZIP thật sau nén**, nhiễu LB ≈ ±0,01 nên không đốt slot cho delta nhỏ hơn, chờ H trước khi đổi phân bổ. | Lỗ hổng: quá thụ động, kỳ vọng đề xuất chỉ +0,005–0,03 — không đủ đóng khoảng cách 0,13 tới #3 trong 8 ngày; chính M2 kỳ vọng đề xuất B của mình "<0–0,01" thì không nên nằm trong top-3.
- **M3**: Điểm mạnh — thiết kế **thí nghiệm offline 0-slot** tốt nhất: đo % argmax-chunk nằm sau ký tự 2.000, đo near-dup trong top-100 — quyết định được cả nhánh tail-vector mà không tốn lượt nộp. | Lỗ hổng: Đề xuất HyDE (M3-B) tự mâu thuẫn với chẩn đoán của chính M3 (dense Việt đã mạnh, sinh văn bản giả y khoa dễ sai thuật ngữ, GPU dùng chung); "union top-500 các lượt" vẫn không kéo được tài liệu vô hình với **mọi** biểu diễn hiện có — tức M3-A vẫn phải encode đuôi, chi phí bị đánh giá thấp.
- **M4 (tôi, vòng trước)**: Sai ở ngưỡng — tôi ghép pha loãng chunk vào ngưỡng độ sâu (0,06–0,07); nếu mở rộng **chỉ doc_id** (không kèm chunk) thì chỉ pha loãng F2_doc, ngưỡng ~F2/5 ≈ 0,046 của brief là đúng. Cũng nên giảm 3 bài chẩn đoán của tôi xuống 1–2 vì H miễn phí + dụng cụ offline của M3 thay thế được.

## 2. Tôi đổi quan điểm thế nào (giữ / bỏ / sửa gì, vì sao)
- **Bỏ** ngưỡng 0,06–0,07 của tôi, **giữ** 0,046 cho mở rộng doc-only: đúng như M1-A chứng minh bằng bất đẳng thức P_chunk>P_doc; chunk-dilution chỉ áp dụng nếu thêm cả chunk.
- **Chấp nhận** N_doc ≠ N_chunk là ưu tiên số 1 (rẻ nhất, kỳ vọng lớn nhất), nhưng **giảm số thay đổi đồng thời** so với M1: giữ nguyên bảng xếp hạng G, đóng băng artifact dịch/làm sạch (khắc phục lệch A-vs-G), để H quyết định quota.
- **Giữ** quan điểm của tôi + M2: xóa tiếng Anh (0 nhãn), cắt HyDE khỏi lộ trình chính, không đốt slot cho delta < 0,01.
- **Giảm hình态** M1-B: giữ reranker (khoảng cách tới #3 là chất lượng xếp hạng ở độ sâu) nhưng bỏ sliding-window, sigmoid fusion, ngưỡng động — xem Đề xuất C.

## 3. Đề xuất cuối (tối đa 3)

### Đề xuất A: Doc-only depth + chunk bậc thang, không đổi bảng xếp hạng G (dựa trên: M1-A, M2)
- **Giả thuyết:** F2_doc chỉ phụ thuộc (T_q, N_q); doc_id ~20–25 byte nên nộp tới N_doc≈200 vẫn lời khi precision biên fused ≥ ~0,05; chunk chỉ cần cho top ~110 với L bậc thang để giữ ngân sách byte.
- **Cách làm cụ thể:** (1) Diff local `relevant_docs` bài A vs G để chặn nondeterminism (M1), đóng băng artifact dịch/làm sạch + xếp hạng; (2) xóa 3 lượt tiếng Anh, dùng kết quả H (đang chấm, miễn phí) để chọn quota Vi/Zh; (3) nộp `relevant_docs` = top-200 (quota theo H), `relevant_chunks` = top-110 (hạng 1–40: L≈4.000; hạng 41–110: L≈2.200) — tổng byte ≈ hoặc < bài G vì giảm L phần đuôi, doc_id chỉ thêm vài KB; (4) đo file ZIP-bzip2 thật, chừa 10–15% dưới 95 MB (M2).
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** 1–2 slot: (i) chỉ dịch quota (bỏ Anh), giữ N=100 làm nền; (ii) N_doc=200 + bậc thang L. Bác bỏ nếu `F2_doc` không tăng ≥ +0,02 (vượt nhiễu ±0,01) → precision biên fused < 0,05 → đóng băng độ sâu ~120, dồn nguồn sang Đề xuất C. Nếu format từ chối chunks ⊂ docs → quay về N_doc = N_chunk.
- **Kỳ vọng:** +0,04–0,07 (0,2207 → 0,26–0,29) | Tự tin: cao | Chi phí: S

### Đề xuất B: Bộ đo offline 0-slot trước khi viết thêm dòng code (dựa trên: M3-A, M3-C, M2)
- **Giả thuyết:** Ba con số (vị trí argmax-chunk, tỷ lệ near-dup, byte thật) quyết định thứ tự mọi nhánh còn lại và đo được không tốn lượt nộp.
- **Cách làm cụ thể:** (i) M3-A: với top-500 fused của 1.200 câu, đo % tài liệu có cửa sổ giống-query nhất nằm sau ký tự 2.000; (ii) M3-C: MinHash Jaccard ≥ 0,8 trên top-100 của 50 câu ngẫu nhiên; (iii) nén thử file thật.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** argmax-sau-2.000 < 15% → bỏ cả M1-C lẫn M3-A (tail-vector vô nghĩa); near-dup < 5% → bỏ dedup; byte vượt → hạ bậc L. Các ngưỡng này chọn trước, không chỉnh sau khi thấy số.
- **Kỳ vọng:** giá trị định hướng cho ≥ +0,05 về sau, trực tiếp +0–0,02 | Tự tin: cao (về giá trị thông tin) | Chi phí: S

### Đề xuất C: Reranker giản lược — chỉ chấm top-200, điểm dùng luôn để chọn tâm chunk (dựa trên: M1-B, đã cắt phức tạp)
- **Giả thuyết:** Khoảng cách tới #3 là chất lượng xếp hạng ở độ sâu (P tương đương ~0,17 vs 0,18 nhưng T≈2×); cross-encoder đưa tài liệu đúng lên đầu → cùng N_doc=200 đạt T cao hơn.
- **Cách làm cụ thể:** `bge-reranker-v2-m3` fp16, max_length=512, trên top-200 fused (~240k cặp, chạy đêm 3–6h trên 5060 Ti), **cache điểm theo (câu, doc)**; N_doc/N_chunk/L giữ như Đề xuất A; tâm mở rộng chunk = chunk có điểm reranker cao nhất (thay cos BGE-M3) — trả lời câu hỏi 2 của brief. **Bỏ** sliding-window triple-sum, sigmoid 0,65/0,35, ngưỡng động N(q) của M1-B. Nếu muốn dùng bản fine-tune AITeamVN thì phải xác minh ngày phát hành < 01/08/2026 và ≤15B trước (chưa kiểm chứng) — không đạt thì dùng bản BAAI gốc.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** 1 slot: so R_doc@120(reranked) với R_doc@200(fused) từ Đề xuất A. Bác bỏ nếu không vượt → cross-encoder không transfer sang y khoa Việt/Trung → đóng băng, private dùng cấu hình A.
- **Kỳ vọng:** +0,03–0,06 (R_doc 0,32 → 0,42–0,50) | Tự tin: vừa | Chi phí: M

**Lịch trình:** A ngày 1–2 (sau khi H về) ∥ B ngày 1 (CPU) → C ngày 3–5 → đóng băng ngày 7. **Private (5 bài):** chỉ các cấu hình đã thắng trên public, giữ G làm neo an toàn, chừa ≥1 slot cho lỗi 413/format.

## 4. Bình chọn
VOTES: M1-A, M3-A, M1-B
