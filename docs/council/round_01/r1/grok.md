# M1 = grok (x-ai/grok-4.7) — vai: red_team — vòng 1

Tôi sẽ tra cứu đặc tả chấm điểm, các pitfall BM25/chunk overlap và giải pháp retrieval y khoa tương tự trước khi chỉ ra lỗi nghiêm trọng.## 1. Chẩn đoán nhanh
Điểm thấp hơn baseline BM25 của BTC (0,1606 so với 0,3764) vì pipeline đang phá đúng tín hiệu lexical mà nhãn gần như bám theo, không phải vì thiếu dense hay reranker. P_doc baseline 0,881 ở R 0,515 là bất thường với truy hồi web mở: pool chấm kiểu BEIR coi hit ngoài pool lexical là sai, nên RRF + hạn mức Trung (P≈0,16) và Anh (0/12.000 mẫu vàng) làm loãng top-k. Sparse hiện tại ghi là BM25 nhưng đi qua HashingVectorizer — lớp này không có IDF và va chạm hash — nên thứ hạng có thể không phải BM25. Chunk 1.000 ký tự có thể bất khả thi: LCS ≤ |c|, nên nếu |g| lớn hơn khoảng 2,5 lần |c| thì overlap/|g| không bao giờ ≥ 0,4; các đội #1–#5 có F2 chunk ≈ F2 doc, đội này chỉ 0,34.

## 2. Đề xuất (tối đa 3, xếp theo kỳ vọng/chi phí)
### Đề xuất A: Nộp thuần danh sách bm25_vi đã lưu
- Giả thuyết: RRF (k=60, bản dịch trọng số 0,3) và hạn mức 60/40 đang đẩy tài liệu ngoài pool nhãn lên trên đúng hit lexical. Top-k của riêng lượt bm25_vi (đã tính, không cần reindex) sẽ có P_doc cao hơn hẳn 0,177 và F2 doc tiến về 0,559 của baseline.
- Dựa trên bằng chứng nào trong brief: baseline trả ~30 tài liệu, trúng ~27 (P 0,881); bài tốt nhất trả ~100, trúng ~18. Chưa từng nộp bm25_vi thuần ở k≈25–60. 20 Anh = 0; P Việt 0,38 > P Trung 0,16. BEIR đo đúng kiểu lệch này: trên TREC-COVID, hit lexical Hole@10 chỉ 6,4%, còn dense tới 14–32% và bị tính sai cho đến khi gán nhãn lại (ANCE 0,654 → 0,735).
- Cách làm cụ thể: giữ nguyên chunk hiện tại để không nhiễu. Ba bài trong một ngày, cùng một danh sách bm25_vi đã lưu, chỉ đổi k = 25, 40, 60; doc_id đúng ID corpus, không URL redirect. Cấm trộn dense, Trung, Anh. Không tăng 150–200 trên fusion hiện tại — với P 0,177, thêm tài liệu đuôi gần như chắc làm macro-F2 tệ hơn.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: so với bài 0,1606 ngày 15/10. Bác bỏ giả thuyết “fusion là thủ phạm chính” nếu cả ba k đều có F2 doc < 0,28 hoặc P_doc < 0,30. Nếu k=40 có P_doc ≥ 0,6 và R_doc ≥ 0,45 thì fusion là lỗi, dừng plan reranker. Nếu P vẫn ~0,2 thì lỗi nằm ở bản thân sparse/text (chuyển sang Đề xuất C), không phải ở cách gộp.
- Kỳ vọng: <+0,08 đến +0,18 điểm tổng nếu P_doc ≥ 0,6> | Tự tin: vừa | Chi phí: S

### Đề xuất B: Một chunk nguyên văn dài, giữ nguyên tập tài liệu
- Giả thuyết: R_chunk/R_doc = 0,34 chủ yếu vì cửa sổ 1.000 ký tự (Việt) ngắn hơn 0,4|g| hoặc không chứa đoạn vàng, không phải vì cosine chọn sai giữa các cửa sổ ngắn. Một chunk = thân bài trafilatura thô (không phải chuỗi đã tách âm tiết / đã lọc “dòng rác”) sẽ kéo R_chunk về gần R_doc.
- Dựa trên bằng chứng nào trong brief: luật overlap = LCS_token(c,g)/|g|, mẫu số chỉ |g|, ~1 chunk vàng/tài liệu; P_chunk 0,067 và R_chunk 0,115. Chunk Trung (trang ngắn, 500 ký tự) có P cao hơn Việt (bài dài). Đội #1 có P_chunk 0,993 ≈ P_doc 0,995. Tập ViHealthQA (vinmec/vnexpress, cùng kiểu hỏi–đáp y khoa Việt) có ~47% đoạn trả lời trên 300 từ — priors độ dài, không phải nhãn cuộc thi này.
- Cách làm cụ thể: lấy đúng tập doc của bài 0,1606. Mỗi doc nộp đúng 1 chunk: thân bài sau trafilatura, chưa lọc dòng, chưa lowercase, chưa bỏ dấu. Cap 8.000 ký tự (cắt theo biên đoạn, không cắt giữa từ). Không nộp 2–3 cửa sổ: chunk không phủ g nào là false positive. Chấm thử local bằng DP LCS Python trên 20 cặp (8.000 token × giả định |g|=400) để ước lượng thời gian; không tìm thấy ngưỡng timeout chính thức của BTC.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: một bài LB, doc giống hệt 15/10. Bác bỏ nếu R_chunk/R_doc vẫn ≤ 0,45 và F2 chunk tăng < 0,03. Nếu điểm chunk = 0 hoặc bài bị reject trong khi doc vẫn khớp, coi là timeout/format — hạ cap xuống 3.000 rồi 1.500, không nhảy lên full HTML. Nếu R_chunk lên ≥ 0,8×R_doc, độ dài/text thô là lỗi; lúc đó mới sweep 3k/8k/12k.
- Kỳ vọng: <+0,04 đến +0,10 điểm tổng trên tập doc hiện tại> | Tự tin: vừa | Chi phí: S

### Đề xuất C: BM25 thật trên full text Việt — chỉ nếu A bị bác
- Giả thuyết: “BM25” hiện tại không phải BM25 (HashingVectorizer không có IDF, có collision, norm L2 mặc định là cosine TF đã băm) và/hoặc cắt 10.000 ký tự đầu làm lệch pool của BTC. BM25Okapi/BM25S trên toàn văn Việt, token âm tiết, k=40, sẽ tiến tới P và R của baseline.
- Dựa trên bằng chứng nào trong brief: F2 doc 0,238 so với baseline 0,559 dù cùng bài toán lexical. Dense chỉ encode 2.000 ký tự / 512 token trong khi BGE-M3 chịu 8.192 token; embedding mất recall khi câu trả lời nằm cuối, BM25 thì không — nên cắt đầu phạt dense và có thể phạt cả sparse nếu BTC index full text. Plan reranker đi trước bước này là đảo ưu tiên: bge-reranker-v2-m3 được fine-tune ở max_length 1024, và nếu nhãn là pool BM25 thì cross-encoder đẩy hit semantic không có trong pool lên, LB public giảm.
- Cách làm cụ thể: chỉ index trang Việt đã crawl. Một chỉ mục BM25S hoặc Lucene, không HashingVectorizer; không cắt 10k. Hai biến thể token, cùng k=40: (1) âm tiết như hiện tại, (2) từ pyvi/underthesea. Chunk giữ phương án thắng của B. Không đụng GPU reranker cho đến khi bài này xong.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: tối đa 2 bài. Bác bỏ “sai hàm chấm/cắt độ dài” nếu cả hai tokenizer đều có P_doc < 0,35 và F2 doc không hơn bài A quá 0,03. Khi đó lỗi là text crawl ≠ text BTC (trafilatura bỏ đoạn; bật favor_recall hoặc html2txt trên 30 URL, đo tỉ lệ câu hỏi public xuất hiện nguyên văn trong index). Nếu P_doc ≥ 0,7 ở k=40, khóa pipeline lexical này; reranker chỉ được thử sau, và chỉ giữ nếu không làm P_doc giảm quá 0,05.
- Kỳ vọng: <+0,12 đến +0,22 so với 0,1606 nếu A thất bại vì sparse hỏng> | Tự tin: vừa | Chi phí: M

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief
Xếp theo likelihood × damage:
1. Sparse không phải BM25 (HashingVectorizer) × lệch hẳn baseline — kiểm bằng A rồi C. Giả định từ chữ “BM25 (HashingVectorizer)” trong brief; nếu IDF được tính riêng trước khi băm, A vẫn phân biệt được.
2. Nhãn = pool BM25 của BTC, không phải relevance mở — P 0,881 và 0 tài liệu Anh sau khi PubMed thêm ngày 12/10. Reranker/dense có thể đúng về mặt y khoa nhưng sai trên LB. Không có bằng chứng private dùng cùng pool; giữ 1 slot private cho bản semantic, đừng đốt 5 slot private để đuổi public.
3. |c| < 0,4|g| hoặc chunk nộp là bản đã chuẩn hoá/lọc rác, không phải nguyên văn — kiểm bằng B. So một chunk đã nộp với HTML thô: mất dấu hoặc mất câu là train/inference mismatch.
4. ~20k URL thiếu, trong đó youmed.vn — site hỏi–đáp y khoa. Offline, không tốn submission: grep 50 câu public trong corpus; nếu <50% có chuỗi câu hỏi, trần recall bị crawl/extract khoá, BM25 đúng công thức cũng không tới baseline.
5. doc_id: redirect/http/www khác ID corpus sẽ làm rơi hit im lặng. Đếm bao nhiêu ID nộp không thuộc file URL BTC trước mỗi bài.
6. Nhiễu LB chưa đo. Một slot: nộp lại đúng file 0,1606. Nếu lệch > 0,01 thì mọi ablation trong ngày đó không diễn giải được.
7. Plan mục 6.1 (100→150–200, tỷ lệ cố định) và 6.2 (reranker trước) đi ngược bằng chứng hiện có. Hạn mức ngôn ngữ cố định mọi câu là sai khi |G| từ 5–190 và F2 là macro; việc đó chỉ đáng làm sau khi có thứ hạng lexical có P cao, bằng ngưỡng điểm chứ không bằng k lớn hơn.

## 4. Nguồn đã tra cứu
- HashingVectorizer không có IDF, collision khi n_features nhỏ — https://scikit-learn.org/stable/modules/feature_extraction.html?highlight=tfidf — chứng minh sparse hiện tại không tương đương BM25 nếu dùng đúng lớp này. [[1]](https://scikit-learn.org/stable/modules/feature_extraction.html?highlight=tfidf)
- HashingVectorizer API: không IDF, hash collision, không inverse_transform — https://scikit-learn.org/1.6/modules/generated/sklearn.feature_extraction.text.HashingVectorizer.html — cùng kết luận, bản API. [[2]](https://scikit-learn.org/1.6/modules/generated/sklearn.feature_extraction.text.HashingVectorizer.html)
- BEIR: lexical bias / Hole@10, ANCE 0,654→0,735 sau khi gán hit ngoài pool — https://arxiv.org/html/2104.08663 — mô hình vì sao dense+RRF có thể thua BM25 trên nhãn sinh từ pool lexical. [[3]](https://arxiv.org/html/2104.08663)
- Bảng Hole@10 TREC-COVID (BM25 6,4% vs TAS-B 31,8%) — https://ar5iv.labs.arxiv.org/html/2104.08663 — số liệu pooling bias. [[4]](https://ar5iv.labs.arxiv.org/html/2104.08663)
- Pooling bias khi nhãn chỉ phủ pool retriever yếu — https://arxiv.org/pdf/2209.05072 — cùng cơ chế, phía training. [[5]](https://arxiv.org/pdf/2209.05072)
- BGE-M3 tối đa 8192 token, không phải 512 — https://huggingface.co/BAAI/bge-m3 — đội đang cắt 512 token / 2.000 ký tự, bỏ phần thân bài. [[6]](https://huggingface.co/BAAI/bge-m3?ref=yuniko.software)
- Position bias: bge-m3-dense giảm khi câu trả lời lùi về cuối; BM25 không — https://arxiv.org/abs/2505.13950 — cắt prefix phạt dense, không phải lý do BM25 chuẩn thất bại. [[7]](https://arxiv.org/abs/2505.13950)
- bge-reranker-v2-m3 fine-tune max_length 1024, khuyến nghị 1024 dù kiến trúc 8192 — https://huggingface.co/BAAI/bge-reranker-v2-m3/discussions/9 — reranker không phải việc rẻ/đáng làm trước trên 16GB. [[8]](https://huggingface.co/BAAI/bge-reranker-v2-m3/discussions/9)
- trafilatura thiên về bài báo, thiếu nội dung thì bật favor_recall / html2txt — https://trafilatura.readthedocs.io/troubleshooting.html — cơ chế extract có thể làm text đội ≠ text BTC. [[9]](https://trafilatura.readthedocs.io/troubleshooting.html)
- ViHealthQA: đoạn trả lời y khoa Việt, 34,1% dài 101–300 từ, 31,13% dài 301–500 từ — https://arxiv.org/html/2206.09600 — priors độ dài, không phải phân phối |g| của cuộc thi. [[10]](https://arxiv.org/html/2206.09600)
- Không tìm thấy trang luật chấm, code baseline, hay write-up đúng cuộc thi này (relevant_docs + LCS_token ≥ 0,4); mọi số về timeout grader và cách BTC sinh nhãn là suy từ brief, không có URL.
