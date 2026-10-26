# M2 = minimax (xiaomi/mimo-v2.6-flash) — vai: data_detective — vòng 1

## 1. Chẩn đoán nhanh

- P_doc của BM25 baseline = 0,881 là con số bất thường đối với truy hồi web thật, nên tôi giả định (chưa xác minh được) nhãn sinh ra từ một pool BM25 của BTC kiểu pooling TREC — mọi lượt dense/dịch/Trung kéo tài liệu ngoài pool vào và bị phạt precision theo cách BM25 của BTC không bị. [nguồn pooling: CLEF eHealth task overview ở mục 4]
- Hạn mức 60/40 áp đồng nhất cho mọi câu bơm tài liệu Trung (P≈0,16) vào mọi câu, trong khi 0/12.000 mẫu gold là tiếng Anh — đây là mất điểm có hệ thống do dữ liệu phân bổ theo câu, không phải do mô hình.
- Chunk thua vì hai thứ thuần data: chỉ 1 chunk ~1.000 ký tự/tài liệu (trong khi mẫu số chỉ là |g| nên chunk dài không bị phạt), và vùng text đội trích xuất (trafilatura + gom dòng) nhiều khả năng lệch với chunk tham chiếu mà BTC trích bằng parser riêng.
- Crawl thiếu domain (laodong.vn, youmed.vn) + khả năng mirror/gần-trùng lặp giữa báo–nhà thuốc–bệnh viện tạo trần recall mà ranking không sửa được.
- Chưa có ước lượng nhiễu LB và chưa dùng file chấm chi tiết ở mức per-question → mọi chỉnh hạn mức hiện tại đều là phỏng đoán.

## 2. Đề xuất (xếp theo kỳ vọng/chi phí)

### Đề xuất A: Khai thác file chấm chi tiết ở mức per-question trước khi chỉnh gì cả
- Giả thuyết: file chấm chi tiết chứa đủ (ít nhất |G| mỗi câu, nếu may mắn là cả doc_id gold) để ước ngoại lệ tối ưu cho K và hạn mức ngôn ngữ ngoài cuộc; và recall@300 của từng lượt truy hồi đã có so với gold sẽ cho biết RRF đang làm loãng hay khuếch đại tín hiệu BM25.
- Dựa trên bằng chứng nào trong brief: |G| dao động 5–190 nhưng K cố định ~100; P theo ngôn ngữ lệch mạnh (Vi 0,38 vs Zh 0,16); ước tính 18/60 hit của mình vs ~27/30 của baseline.
- Cách làm cụ thể: (1) liệt kê chính xác cột nào file chấm chi tiết có per-question; (2) nếu có gold doc_id, tính offline: recall@300 của bm25_vi, dense_vi, bm25_zh, quota 60/40 hiện tại, và oracle "chọn K theo |G|"; (3) vẽ histogram |G|, histogram domain của gold so với corpus đã crawl.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nếu recall@300 của bm25_vi ≥ ~0,52 (mức baseline) trong khi config 100 tài liệu chỉ đạt R=0,334 →证实 hạn mức/dịch đang loễ hoá tín hiệu BM25, plan phải đổi sang "quota theo câu hỏi, gần thuần BM25 Việt"; bác bỏ nếu recall@300 của bm25_vi ≈ config hiện tại (tức pool BM25 không phải chìa khoá). Nếu file không có gì per-question → đề xuất này tự bác bỏ và chỉ còn LB làm nhãn.
- Kỳ vọng: +0,02–0,05 (thông qua quyết định quota/K đúng) | Tự tin: vừa | Chi phí: S

### Đề xuất B: Audit near-duplicate + khoảng trống crawl của top-k đã truy hồi
- Giả thuyết: một tỷ lệ đáng kể trong top-100 họ đang nộp là bản mirror/gần-trùng của nhau (syndicated news, nhà thuốc copy bài), mỗi slot duplicate là một slot mất cơ hội trúng đúng doc_id gold; thêm vào đó gold đến từ domain bị chặn thì trần recall đã cố định.
- Dựa trên bằng chứng nào trong brief: corpus 714k trang VN trộn báo/bệnh viện/nhà thuốc; thiếu ~20k URL (laodong.vn, bạnmed.vn); P_doc=0,177 với ~100 tài liệu.
- Cách làm cụ thể: MinHash/LSH (shingle 5-gram, ngưỡng ~0,8) trên corpus Việt và trên top-100 của mỗi câu; đếm (i) % duplicate trong top-100, (ii) số câu bị duplicate lấp ≥20% hạn mức, (iii) nếu file chấm có domain gold: % gold rơi vào domain không crawl được.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nếu % duplicate trong top-100 < 5% → bác bỏ (không cần dedup); nếu > 20% → nộp 1 bản dedup cùng K, giữ 1 trang/nhóm, cùng quota: kỳ vọng F2_doc tăng vì thay slot trùng bằng slot mới. Δ ≤ 0 (so với 0,1606, sau khi đã ước nhiễu ở đề xuất C) → bác bỏ.
- Kỳ vọng: +0,01–0,04 F2_doc | Tự tin: thấp/vừa | Chi phí: S–M

### Đề xuất C: Trước tiên đo nhiễu LB, rồi mới chạy 1 thí nghiệm chunk dài hơn
- Giả thuyết: vì mẫu số chỉ là |g|, gộp 2–3 dòng liền kề thành chunk 2.500–4.000 ký tự (hoặc nộp 2 chunk lân cận/tài liệu) sẽ tăng R_chunk trong tài liệu đúng, đúng thứ họ đang thua nặng nhất (R_chunk/R_doc = 0,34); nhưng cần biết nhiễu LB để biết Δ bao nhiêu là thật.
- Dựa trên bằng chứng nào trong brief: F2_chunk 0,084 vs F2_doc 0,238; các đội #3–#5 có F2_chunk ≈ F2_doc; "nhiễu giữa các bài nộp: chưa đo"; snippet extraction vốn khó hơn doc retrieval ngay cả ở BioASQ chuẩn. [nguồn mục 4]
- Cách làm cụ thể: (1) chi 1 lượt nộp lại đúng cấu hình tốt nhất (100 tài liệu 60/40) → |Δ| với 0,1606 ước nhiễu LB; (2) chi 1 lượt chỉ đổi phần chunk (giữ nguyên top-100, chunk 1/tài liệu nhưng gộp lên ~3.000 ký tự quanh vị trí cos cao nhất); (3) kiểm tra offline trên 20 trang: % trang mà vùng 1.000 ký tự đầu đội chọn nằm ngoài 40% ký tự giữa trang (dấu hiệu trích xuất lệch vùng/boilerplate).
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: ΔF2_chunk > 3×nhiễu đo được ở (1) → giữ hướng chunk dài làm mục chính; Δ nhỏ hơn → nguyên nhân không phải độ dài mà là chọn sai vùng/parser lệch, chuyển sang rerank chunk (bge-reranker-v2-m3 đã có trong plan) thay vì kéo độ dài. Chú ý giới hạn 5 bài/private: chỉ dùng 2 lượt LB cho việc này.
- Kỳ vọng: +0,03–0,08 tổng điểm (chunk 0,084 → tiệm cận F2_doc) | Tự tin: vừa | Chi phí: S (2 lượt nộp + 1 lần đếm offline)

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief

- **File chấm chi tiết rốt cuộc chứa gì?** Chỉ thống kê tổng quát hay per-question gold doc_id/chunk? Đây là quyết định sống còn cho mọi đề xuất ở trên — tôi đang giả định nó có per-question (giả định, không chắc).
- Bài 0,1606 có thực sự nộp ~100 tài liệu không? Brief nói 60/40/0 chỉ là "giả định" — không rõ cấu hình thật đã nộp.
- Gold có tài liệu Trung không? "20 Trung" được 0,0536 > 0 nghĩa là có hit — hit này đến từ doc Trung thật trong gold, hay từ trùng text đa ngôn ngữ? Chưa giải thích.
- Gold chunk do BTC trích bằng parser gì? Text trích của đội (trafilatura + gom dòng) đã khớp từng token sau NFKC với text gốc chưa? Không có cách nào kiểm nếu không có vài gold chunk mẫu.
- P_doc 0,177 × ~100 ≈ 18 hit vs gold ~60 → R=0,33 nhất quán; nhưng ước tính "baseline 27/30" giả định |G|≈55 cho cả hai — có thể baseline và mình so được câu khác nhau.

## 4. Nguồn đã tra cứu

- CLEF 2017 Task overview (eHealth IR, pooling-based relevance assessment) — https://eprints.qut.edu.au/128813/1/invited_paper_17.pdf — chứng minh cách dựng nhãn chuẩn trong IR cạnh tranh là gộp (pool) kết quả các baseline rồi chấm; giải thích hợp lý vì sao P_doc của một BM25 baseline thuần có thể lên tới 0,88.
- Sparse Retrieval with Cross-Encoder Reranking … for Biomedical QA (BioASQ Phase A) — https://ceur-ws.org/Vol-4283/paper23.pdf — doc retrieval và snippet/chunk retrieval là hai việc riêng, snippet khó hơn; BM25 + cross-encoder rerank là cách chuẩn xử lý cặp này.
- Enhancing Regulatory Compliance … (bge-m3 + bge-reranker-v2-m3) — https://aclanthology.org/2025.regnlp-1.14.pdf — dùng đúng cặp model mà plan đang định chạy, cho thấy rerank chunk giúp tăng Recall@10 0,74→0,79.
- Microsoft Azure Architecture — RAG evaluation (định nghĩa LCS không liên tiếp) — https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-llm-evaluation-phase — xác nhận scoringrule của BTC là LCS-token kiểu ROUGE-L; lưu ý mẫu số |g| (chunk dài không bị phạt) là luật riêng của cuộc thi lấy từ brief, không tìm thấy nguồn web độc lập.
- An evaluation of RAG Retrieval Chunking Methods (VectorHub) — https://github.com/superlinked/VectorHub/blob/main/docs/articles/evaluation_of_RAG_retrieval_chunking_methods.md — reranker sau retrieval cải thiện độ chính xác chọn đoạn.
- Không tra cứu được (vượt giới hạn 3 lượt tìm kiếm của vòng này): ảnh hưởng tách từ tiếng Việt (âm tiết vs từ) tới BM25, và write-up đội thắng cuộc của chính bài toán này.
