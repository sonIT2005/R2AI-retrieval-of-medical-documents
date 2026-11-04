# M3 = qwen (qwen/qwen3.8-max-0902) — vai: competition_veteran — vòng 2

## 1. Nhận xét từng thành viên
- M1: điểm mạnh: đề xuất `bm25_vi` thuần với k=25/40/60 là thí nghiệm rẻ và đúng chỗ để tách ảnh hưởng của RRF/quota; phát hiện “BM25” hiện tại có thể không phải BM25 thật do HashingVectorizer; chunk dài có kiểm soát cap và benchmark. | lỗ hổng: k=25–60 có thể quá bảo thủ vì với F2 hiện tại ngưỡng thêm tài liệu còn thấp và |G| có thể rất lớn; cap 8.000 ký tự với N≈100 dễ đụng timeout/file size; chưa nêu rõ cách đọc nhiễu LB ngay trong thí nghiệm chính.
- M2: điểm mạnh: nhấn mạnh đo nhiễu LB trước khi kết luận; audit near-duplicate và khoảng trống crawl là chẩn đoán đúng với corpus tin tức/nhà thuốc; chunk dài vừa phải 3.000 ký tự là an toàn hơn. | lỗ hổng: giả định file chấm chi tiết có gold per-question để tính recall@300 là không được brief đảm bảo và có rủi ro “dò đáp án”; dedup có thể không giúp nếu gold không gộp bản sao hoặc doc_id bản sao không nằm trong gold.
- M4: điểm mạnh: chuỗi thí nghiệm rất sạch: whole-doc chunk → BM25 Việt thuần → sửa toàn văn/tokenization; đúng tinh thần quay về baseline BM25 của BTC. | lỗ hổng: whole-doc không có ngân sách timeout/file size; không đo nhiễu LB; không có cơ chế chọn N theo ngưỡng precision biên nên dễ quay lại lỗi “N cố định”.

## 2. Tôi đổi quan điểm thế nào (giữ / bỏ / sửa gì, vì sao)
- Giữ: từ M3-A/M3-B, tôi giữ luận điểm chunk nên là **1 chunk dài duy nhất cho mỗi tài liệu** trong vòng ablation đầu, và phải quay về tín hiệu lexical/BM25 trước khi tiêu GPU cho reranker/LLM.
- Bỏ: tôi bỏ đề xuất nộp “toàn văn bản” không kiểm soát ngay từ vòng đầu; quá rủi ro về thời gian chấm và kích thước file. Tôi cũng bỏ ý tưởng giữ tiếng Trung theo quota cố định; bằng chứng P_vi≈0,38 > P_zh≈0,16 cho thấy quota 40 slot Trung đang làm loãng top tài liệu Việt.
- Sửa: tôi nhận M2-C mạnh hơn ở điểm **phải đo nhiễu LB trước**. Tôi cũng nhận M1-A/M4-B hợp lý hơn đề xuất “global BM25 đa ngôn ngữ ngay” của tôi: trước hết phải nộp `bm25_vi` thuần để tách lỗi fusion, rồi mới nói tới chuẩn hóa điểm số hay thêm Trung. Tôi sửa ngưỡng thêm tài liệu: không dùng cứng 0,11–0,15; với F2_doc hiện tại 0,238 ngưỡng lý thuyết chỉ khoảng 0,048, nhưng khi đã lên vùng 0,5–0,6 thì cần precision biên ≈0,10. Vì vậy, quét N và đọc precision biên trên LB vẫn là cách an toàn nhất.
- Về reranker/LLM: tôi giữ quan điểm **không ưu tiên lúc này**. Reranker chỉ nên xét sau khi chunk F2 ≈ doc F2 và doc F2 đã ≥0,45; trước đó, lỗi lớn nhất là retrieval lexical và độ phủ chunk.

## 3. Đề xuất cuối (tối đa 3)

### Đề xuất A: Đo nhiễu + ablation chunk dài 1 chunk/tài liệu trên retrieval đóng băng (dựa trên: M1-B, M2-C, M3-A, M4-A)
- Giả thuyết: F2_chunk thấp không phải chủ yếu do chọn sai cửa sổ cosine, mà do chunk 1.000 ký tự không phủ ≥40% chunk tham chiếu. Vì LCS(c,g)/|g| đơn điệu tăng khi c dài hơn, một chunk dài hơn cho cùng doc_id sẽ tăng R_chunk mà không tăng N_chunk. Nếu F2_chunk không tăng khi chunk dài hơn, vấn đề nằm ở extraction/doc_id/crawl chứ không phải độ dài.
- Cách làm cụ thể:
  1. Xác nhận lại chính xác bài 0,1606: N thật, tỷ lệ ngôn ngữ, danh sách doc_id. Nếu không khôi phục được, nộp lại đúng file hiện tại để làm baseline.
  2. Kiểm tra offline: tất cả doc_id nộp phải tồn tại trong corpus BTC; đếm số ID lạ/redirect. Nếu có >0, sửa trước khi nộp.
  3. Giữ nguyên danh sách tài liệu của bài tốt nhất. Với mỗi tài liệu, chỉ nộp **1 chunk**. Chunk lấy từ text thô hơn: trafilatura `favor_recall` hoặc html2text, không lọc dòng rác mạnh, không lowercase; nếu doc ngắn hơn L thì nộp toàn bộ, nếu dài hơn thì chọn cửa sổ quanh vị trí BM25/cosine hiện tại rồi mở rộng đến L, cắt ở ranh giới câu/đoạn.
  4. Đặt ngân sách an toàn: nếu bài hiện tại khoảng N=100 và L=1.000, thử L=1.500 và L=2.000 trước. Không nhảy ngay lên 4.000–8.000 khi N=100. Nếu sau này giảm N về 30–60, có thể tăng L để giữ N×L ≈ 100k–150k ký tự/câu.
  5. Benchmark cục bộ trước khi nộp L=2.000: chạy LCS DP trên ~20 cặp giả lập với c≈L token và g≈300–600 token. Nếu ước lượng tổng thời gian quá lớn hoặc file nộp vượt giới hạn đã biết, hạ L hoặc giảm N. Nếu có thể, hỏi BTC bằng văn bản về trần độ dài/thời gian.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ:
  - Dùng 3 slot public trong 1 ngày: (1) nộp lại cấu hình tốt nhất để đo nhiễu σ; (2) L=1.500; (3) L=2.000 nếu benchmark/file size ổn.
  - Chấp nhận hướng chunk dài nếu F2_chunk tăng > max(0,02; 3σ) và R_chunk/R_doc đạt ≥0,6 ở ít nhất một cấu hình.
  - Bác bỏ giả thuyết “chỉ cần dài hơn” nếu F2_chunk không tăng vượt nhiễu hoặc R_chunk/R_doc vẫn ≤0,45 dù chunk dài hơn. Khi đó ưu tiên audit crawl/extraction/doc_id, không tiếp tục tối ưu retrieval trên nền chunk sai.
  - Nếu bị timeout/reject ở L=2.000, hạ L hoặc chuyển sang chiến lược N nhỏ hơn với chunk dài hơn ở Đề xuất B.
- Kỳ vọng: +0,05 đến +0,10 tổng điểm | Tự tin: cao | Chi phí: S

### Đề xuất B: BM25 Việt thuần, bỏ RRF/quota; quét N và cắt theo precision biên (dựa trên: M1-A, M4-B, M3-B)
- Giả thuyết: RRF với dense, câu dịch và quota Trung cố định đang đẩy tài liệu Việt đúng ra khỏi top, làm P_doc chỉ còn 0,177 trong khi baseline BM25 của BTC đạt 0,881. Nộp `bm25_vi` thuần sẽ phục hồi precision. Sau đó, số tài liệu nên chọn theo precision biên, không cố định 100 hay 60/40.
- Cách làm cụ thể:
  1. Dùng cache `bm25_vi` hiện có, chỉ với câu hỏi tiếng Việt gốc. Không dense, không RRF, không dịch Trung/Anh, không quota ngôn ngữ. Tạm thời bỏ hoàn toàn tiếng Anh vì gold có 0 tài liệu Anh.
  2. Dùng chunk tốt nhất từ Đề xuất A. Nếu A chưa có kết quả, vẫn nộp để đọc F2_doc, nhưng không kết luận chunk.
  3. Nộp 3 mốc: top-30, top-60, top-100 tài liệu Việt. Với top-30, có thể tăng L chunk lên khoảng 3.000–4.000 nếu benchmark an toàn; với top-60/100 giữ L nhỏ hơn để giữ ngân sách N×L.
  4. Từ P_doc và R_doc trả về, ước lượng H≈P×N. Tính precision biên giữa các mốc: ΔH/ΔN. Nguyên tắc dừng: nếu đang ở vùng F2_doc thấp, có thể chấp nhận precision biên ≥0,05; nếu đã đạt F2_doc ≥0,40, ưu tiên precision biên ≥0,10. Nếu thêm tài liệu làm tổng điểm giảm, dừng.
  5. Sau khi có N* cố định, thử một biến per-question cutoff: giữ trung bình N≈N*, nhưng cắt theo khe điểm BM25 hoặc ngưỡng score < α×score_max. Không dùng gold per-question; chỉ dùng điểm retrieval và đặc trưng câu hỏi. Nếu chưa được BTC xác nhận, không dùng |G| từng câu từ file chấm để đặt N.
  6. Tiếng Trung chỉ thử sau khi có N* Việt: một bài nộp giữ tổng N=N*, thay phần đuôi bằng ứng viên Trung được chuẩn hóa điểm theo percentile; không dùng quota 40. Nếu H không tăng ≥5% ở cùng N, bỏ Trung ở cấu hình chính.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ:
  - Xác nhận “fusion/quota là lỗi chính” nếu top-30 `bm25_vi` có P_doc ≥0,60 và F2_doc ≥0,40, hoặc vượt bài 0,1606 hơn 3σ.
  - Bác bỏ giả thuyết chỉ do fusion nếu top-30 P_doc <0,40 hoặc F2_doc ≤0,30. Khi đó vấn đề nhiều khả năng là chỉ mục/text crawl khác baseline, chuyển sang Đề xuất C.
  - Bác bỏ per-question cutoff nếu tổng điểm không tăng ≥0,01 so với fixed N*; giữ fixed N* cho private.
- Kỳ vọng: +0,15 đến +0,30 tổng điểm nếu tín hiệu lexical tái tạo được | Tự tin: vừa | Chi phí: S/M

### Đề xuất C: Nếu B chưa đạt: xây BM25 thật full-text + audit crawl/dedup có điều kiện (dựa trên: M1-C, M3-C, M2-B)
- Giả thuyết: Nếu `bm25_vi` thuần từ index hiện tại vẫn có P@30 thấp, nguyên nhân nằm ở index/text: HashingVectorizer không tương đương BM25 Okapi, cắt 10.000 ký tự đầu, tokenizer âm tiết, hoặc extraction thiếu nội dung. Nếu P đã khá nhưng recall chưa đủ, near-duplicate cluster expansion có thể thêm các bản sao cùng bài mà nhãn có thể đã gộp.
- Cách làm cụ thể:
  1. Xây index BM25 thật (BM25Okapi/BM25S, không HashingVectorizer) trên trang Việt. Không cắt 10.000 ký tự đầu; index toàn văn bản đã extract. Tạo 2 biến thể tokenizer: (a) tách âm tiết theo khoảng trắng; (b) tách từ tiếng Việt bằng underthesea/VnCoreNLP (chưa kiểm chứng). Nếu RAM 29GB không đủ, shard index hoặc dùng bản mmap.
  2. Audit extraction/crawl rẻ trước: lấy 50 câu public, grep chính xác hoặc gần chính xác cụm từ dài 5–8 token trong corpus đã crawl. Nếu hit rate <50%, trần recall có thể do crawl/extraction; ưu tiên sửa extract, thử Wayback/proxy cho laodong.vn/youmed.vn trong time-box 1 ngày. Nếu hit rate cao, tập trung vào ranking.
  3. Nộp tối đa 2 bài cho BM25 thật: chọn biến thể tốt hơn theo offline nếu có thể, nếu không nộp 1 bài tokenizer âm tiết và 1 bài tokenizer từ, cùng N* và chunk từ Đề xuất A.
  4. Chỉ làm near-duplicate expansion nếu audit offline cho thấy đáng làm: MinHash/SimHash trên title + 300–500 ký tự đầu của trang Việt; nếu ≥10–15% top-40 BM25 thuộc cụm có ≥2 bản sao, tạo 1 bài nộp expansion: với mỗi cụm trong top-k, thêm các bản sao chưa có, xếp hạng cụm theo max BM25, giữ cùng N*. Không expand nếu precision biên rơi dưới ngưỡng đã xác định ở B.
  5. Reranker/LLM chỉ xét sau nhánh này nếu F2_doc ≥0,45 và F2_chunk đã gần F2_doc. Khi đó, BGE-reranker-v2-m3 chỉ nên dùng để chọn cửa sổ chunk nếu bắt buộc giới hạn L; Qwen3-8B 4-bit chỉ nên lọc top-50/tài liệu ở ngày gần cuối, không thay đổi cấu hình private trừ khi có slot dự phòng.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ:
  - Chấp nhận BM25 thật nếu ít nhất một biến thể đạt P@30 ≥0,60 hoặc F2_doc ≥0,40, hoặc tăng ≥0,03 so với `bm25_vi` cache.
  - Bác bỏ hướng index nếu cả hai biến thể P@30 <0,35 và F2_doc không tăng ≥0,03. Khi đó ngừng đốt thêm submission cho lexical pool; giữ cấu hình tốt nhất làm private baseline và chỉ thử 1 slot semantic/LLM nếu còn dư.
  - Bác bỏ near-duplicate expansion nếu offline cluster <10% top-40, hoặc bài expansion không tăng H ≥10% ở cùng N so với BM25 thuần.
- Kỳ vọng: +0,05 đến +0,20 tổng điểm nếu index/cluster đúng là nguyên nhân | Tự tin: thấp/vừa | Chi phí: M

## 4. Bình chọn
VOTES: M1-B, M1-A, M2-C
