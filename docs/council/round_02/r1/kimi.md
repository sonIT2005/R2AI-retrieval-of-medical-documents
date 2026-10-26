# M3 = kimi (moonshotai/kimi-k3) — vai: alternative — vòng 1

## 1. Chẩn đoán nhanh

R doc dừng ở 0,32 chủ yếu vì pipeline chấm điểm tài liệu bằng **1 vector/2.000 ký tự đầu** trong khi tài liệu Việt trung bình 3.553 ký tự — tức là ~40–60% nội dung tài liệu vô hình với nhánh dense, và BM25 chỉ cứu được phần khớp từ khoá đúng chính tả. Hệ quả: nhánh dense đang mù một nửa corpus về mặt ngữ nghĩa, còn RRF chỉ xáo trộn thứ hạng chứ không thêm tài liệu mới vào phủ. Reranker trong plan cũng chỉ sắp xếp lại top-200 — nếu tài liệu đúng chưa từng lọt vào ứng viên thì không cứu được. Với ~60 tài liệu đúng/câu, đây là bài toán recall-heavy, nên mọi cải tiến không làm tăng *candidate recall* đều có trần thấp.

## 2. Đề xuất (tối đa 3, xếp theo kỳ vọng/chi phí)

### Đề xuất A: Chấm điểm tài liệu bằng max-sim cấp chunk trên pool ứng viên (không cần re-index toàn corpus)
- Giả thuyết: phần lớn tài liệu đúng bị rơi vì đoạn liên quan nằm sau ký tự 2.000; nếu chấm điểm tài liệu = max cos(query, chunk) trên các chunk 512 token, recall ứng viên tăng mạnh mà không phải encode lại 1,17M tài liệu ở cấp chunk.
- Dựa trên bằng chứng nào trong brief: tài liệu Việt TB 3.553 ký tự nhưng vector chỉ nhìn 2.000 ký tự đầu; F2_chunk/F2_doc đã 0,91 → chọn chunk trong tài liệu đã tốt, nghĩa là embedding cấp chunk của BGE-M3 đủ nhạy, vấn đề nằm ở tầng tài liệu. Bên ngoài: bài báo BGE-M3 cho thấy multi-vector (late interaction kiểu ColBERT) +5,1 điểm so với dense 1-vector trên retrieval tài liệu dài đa ngôn ngữ (MLDR) (https://arxiv.org/html/2402.03216v3); thực nghiệm độc lập cho thấy embed cả tài liệu dài thành 1 vector kém hơn rõ so với embed theo chunk (MRR@1 0,739 vs 0,842) (https://saeedesmaili.com/notes/to-chunk-or-not-to-chunk-with-the-long-context-single-embedding-models/).
- Cách làm cụ thể: lấy hợp top-500 của tất cả lượt hiện có (candidate recall hiện tại), cắt mỗi tài liệu thành chunk 512 token stride 128, encode bằng BGE-M3 (chỉ vài trăm nghìn chunk cho 1.200 câu — vài giờ GPU, không phải 4h×3), điểm tài liệu = max (hoặc trung bình top-2) sim chunk. Thêm lượt "chunkmax_vi" và "chunkmax_zh" vào RRF thay vì chỉ 1 vector/tài liệu. Bonus: chunk argmax cho luôn vị trí mở rộng nguyên văn ở bước chunk → L ngắn hơn vẫn trúng, tiết kiệm byte để tăng N.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nộp 1 bài = pipeline G nhưng thay dense_vi_vi/dense_zh_zh bằng chunkmax, giữ nguyên N và L=4.000. Bác bỏ nếu F2 doc không tăng ≥ +0,02 so với 0,2309. Ước lượng offline trước: đo tỉ lệ tài liệu trong top-500 có argmax-chunk nằm sau ký tự 2.000 — nếu <15% thì giả thuyết yếu, huỷ không tốn lượt nộp.
- Kỳ vọng: +0,03–0,06 tổng | Tự tin: vừa | Chi phí: M

### Đề xuất B: HyDE — embed "câu trả lời giả" thay vì câu hỏi
- Giả thuyết: câu hỏi y khoa trung vị 18 từ quá ngắn và lệch phân phối với văn bản bài viết; sinh 1–2 đoạn "bài viết giả" bằng Qwen3-8B (tiếng Việt và tiếng Trung, có sẵn trong pipeline dịch) rồi embed đoạn đó sẽ kéo đúng vùng ngữ nghĩa của tài liệu đúng — đặc biệt nhánh Trung nơi dịch thuật có thể làm nhiễu thuật ngữ.
- Dựa trên bằng chứng nào trong brief: dense vượt BM25 rõ ở tiếng Việt (0,38 vs 0,156 P@30) → nhánh ngữ nghĩa là chỗ đầu tư đúng; độ trùng dense_vi_zh∩dense_zh_zh chỉ 28% → các biểu diễn câu hỏi đang rất phân tán, có dư địa cho một biểu diễn mới khác biệt. Bên ngoài: HyDE cải thiện mạnh zero-shot retrieval không nhãn, gồm cả y khoa (TREC-Covid) và đa ngôn ngữ low-resource (https://arxiv.org/abs/2212.10496).
- Cách làm cụ thể: Qwen3-8B sinh cho mỗi câu: 1 đoạn trả lời/bài viết giả ~150 từ tiếng Việt + 1 đoạn tiếng Trung (~300 ký tự). Encode bằng BGE-M3, tạo 2 lượt mới (hyde_vi, hyde_zh) đưa vào RRF cùng 8 lượt cũ, giữ nguyên mọi thứ khác. Chi phí sinh: 1.200 câu × 2 đoạn, vài giờ trên 16GB (batch).
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: 1 bài nộp = G + 2 lượt HyDE. Bác bỏ nếu F2 doc không tăng ≥ +0,015. Kiểm tra rẻ trước khi nộp: đo độ trùng top-40 giữa hyde_vi và dense_vi_vi — nếu >60% thì HyDE không thêm thông tin, huỷ.
- Kỳ vọng: +0,01–0,03 tổng | Tự tin: thấp-vừa | Chi phí: S

### Đề xuất C: Khử trùng lặp gần-đúng (near-dup) trước khi xếp hạng
- Giả thuyết: corpus crawl 1,17M trang y khoa gần chắc chứa bài đăng lại/near-duplicate (cùng bài viết trên nhiều site). Nếu nhãn chỉ gắn cho 1 bản, nộp nhiều bản trùng = mất precision và tốn byte vô ích; loại chúng giải phóng cả slot tài liệu lẫn ngân sách 95 MB để tăng N.
- Dựa trên bằng chứng nào trong brief: 698k trang Việt crawl tự do; P doc 0,174 thấp hơn đáng kể so với #4/#5 (0,24/0,27) ở cùng độ dài danh sách — một phần có thể là trùng lặp nội dung; ràng buộc byte đang là nút thắt chính của việc tăng N.
- Cách làm cụ thể: MinHash/simhash trên văn bản sạch toàn corpus (CPU, <1 giờ), nhóm các tài liệu có Jaccard ≥ 0,8; khi nộp, chỉ giữ bản có điểm truy hồi cao nhất trong mỗi cụm, bản bị loại nhường slot cho tài liệu kế tiếp trong RRF.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: bước 1 (miễn phí, không tốn lượt): đo tỉ lệ cặp near-dup trong top-100 của 50 câu ngẫu nhiên. Nếu <5% → bác bỏ, không làm tiếp. Nếu ≥10% → nộp 1 bài G+dedup; bác bỏ nếu F2 doc không tăng.
- Kỳ vọng: +0,005–0,02 tổng (và tiết kiệm byte) | Tự tin: thấp | Chi phí: S

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief

- Chưa có số liệu tỉ lệ tài liệu đúng theo ngôn ngữ (Việt/Trung) — hạn mức 40/50/10 đang là phỏng đoán; một bài nộp rẻ kiểu "phân bổ theo tỉ lệ điểm ứng viên" có thể trả lời dứt điểm câu (f).
- Không rõ chunk tham chiếu dài bao nhiêu (|g|); nếu |g| nhỏ, L=4.000 đang lãng phí byte khổng lồ cho P chunk — cần đo trước khi quyết định L theo thứ hạng.
- Bài G "dựng lại A" tăng từ 0,16 → 0,22 chủ yếu nhờ L — chưa có thí nghiệm nào tách riêng đóng góp của từng lượt retrieval (ablation 8 lượt), nên trọng số RRF trong plan đang tune trên nền chưa đo.
- Độ dài tài liệu Trung và vị trí argmax-chunk (đề xuất A) chưa được đo — đây là phép đo rẻ nhất quyết định ưu tiên.

## 4. Nguồn đã tra cứu
- BGE M3-Embedding paper (MLDR long-doc, multi-vector +5,1 điểm so với dense; MCLS) — https://arxiv.org/html/2402.03216v3 — chứng minh chấm điểm đa-vector/chunk-level thắng 1-vector trên tài liệu dài đa ngôn ngữ (nền cho Đề xuất A).
- To Chunk or Not to Chunk (trích thực nghiệm Aapo Tanskanen: BGE-M3 chunked MRR@1 0,842 vs no-chunk 0,739) — https://saeedesmaili.com/notes/to-chunk-or-not-to-chunk-with-the-long-context-single-embedding-models/ — chứng minh 1 vector/tài liệu dài làm mất thông tin (nền cho Đề xuất A).
- Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE) — https://arxiv.org/abs/2212.10496 — HyDE cải thiện mạnh retrieval zero-shot không nhãn, kể cả y khoa và đa ngôn ngữ (nền cho Đề xuất B).
- BAAI/bge-reranker-v2-m3 model card — https://huggingface.co/BAAI/bge-reranker-v2-m3 — xác nhận reranker đa ngôn ngữ chỉ rerank top-K ứng viên (củng cố chẩn đoán: reranker không cứu được candidate recall).
- AITeamVN/Vietnamese_Reranker — https://huggingface.co/AITeamVN/Vietnamese_Reranker — tồn tại bản fine-tune tiếng Việt của bge-reranker-v2-m3 (tham khảo nếu plan 3 đi tiếp).
