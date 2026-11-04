# M2 = minimax (xiaomi/mimo-v2.6-flash) — vai: data_detective — vòng 2

## 1. Nhận xét từng thành viên

- **M1**: điểm mạnh — chỉ ra được giả định then chốt và có kiểm chứng được ngay: HashingVectorizer không có IDF/collision (dẫn nguồn sklearn đúng chỗ), và phép thử "nộp thuần bm25_vi với k sweep" là thí nghiệm rẻ nhất phân tách "fusion phá" vs "chỉ mục sai". Cũng là người duy nhất chỉ ra check offline grep câu hỏi public trong corpus (kiểm trần crawl) — rất data-centric. | lỗ hổng — Đề xuất A dùng 3 slot LB chỉ để sweep k=25/40/60 trên chính ranker chưa biết đúng-sai, trong khi chỉ cần **một** bài top-30 bm25_vi là đã đọc được P@30 (con số quyết định); k sweep trước khi biết P@30 là tối ưu cái sai. Ngoài ra M1 chưa nêu cách ước nhiễu LB — mọi Δ nhỏ hơn nhiễu đều không diễn giải được.

- **M3**: điểm mạnh — móc F2 về dạng 5H/(4G+N) và suy ra ngưỡng p > F2/5 ≈ 0,12–0,15; đây là framework đúng và có nguồn (Yen ICML12, Collins-Thompson TREC-11). Kế hoạch quét N để vẽ H(N) và cắt theo precision biên là cách đúng để đặt N theo câu. | lỗ hổng — khẳng định "P_zh = 0,16 vẫn trên ngưỡng nên cắt Trung là sai hướng" dùng ngưỡng tính trên *trung bình macro của cả bài*, áp đồng nhất; precision 0,16 của nhóm Trung *đã* bị tính trong hạn mức 40 hiện tại và kết quả bài là 0,1606 — không có bằng chứng rằng giữ 40 slot Trung ở N mới là tối ưu. Đây là giả định chưa kiểm chứng. Ngoài ra ước lượng chi phí LCS 4·10⁵ ô ≈ 0,4s rồi nhân lên "6–7 giờ" là suy diễn, M3 tự đánh dấu không kiểm chứng được — nên coi là cần benchmark local, không phải kết luận.

- **M4**: điểm mạnh — thứ tự "chunk trước, rồi BM25, rồi sửa index" là thứ tự chi phí đúng và gần nhất với vai trò của tôi; xác nhận whole-doc chunk là S-cost. | lỗ hổng — không có nguồn, không có tiêu chí bác bỏ định lượng (chỉ "≥0,20 hay <0,15" không so với nhiễu LB), và Đề xuất A của M4 nộp *nguyên toàn văn* (50k token) mà không nêu trần kích thước file (600 câu × 100 doc × toàn văn ≈ hàng GB — tôi đang **giả định** giới hạn tồn tại, cần đọc lại trang Submission) — rủi ro reject lớn hơn hẳn span 2.000–4.000 ký tự mà M3 đề xuất.

- **M1+M3+M4 chung**: cả ba đều chưa đề nghị **ước nhiễu LB trước** — đây là lỗ hổng xuyên suốt; M3 có nêu ở mục "điểm đáng ngờ" nhưng không đưa vào đề xuất. Tôi giữ nguyên quan điểm này của mình.

## 2. Tôi đổi quan điểm thế nào

- **Giữ**: 3 đề xuất của tôi (A: file chi tiết per-question; B: dedup audit; C: ước nhiễu LB + chunk dài). Đề xuất C nay được M3/M4/M1 củng cố mạnh: cả ba độc lập kết luận "1 span dài/tài liệu, F2_chunk → F2_doc", và M3 đưa được argument toán học (LCS đơn điệu, N_c = N_d) + chữ ký bằng chứng từ đội #1 (P_chunk 0,993 ≈ P_doc 0,995). Tôi nâng niềm tin chunk dài từ "vừa" lên "vừa-cao", đồng thời **hạ cap 3.000 ký tự → 2.000–4.000** (theo M3) thay vì "nguyên văn bản" (M1/M4) vì rủi ro file size/timeout.
- **Bỏ/sửa**: đề xuất B (dedup) của tôi — tôi giờ xếp nó **dưới** các thí nghiệm khác vì M3 đã nêu kiểm chứng miễn phí trước (đếm % top-40 có bản sao trong corpus, bác bỏ ngay nếu <10%). Tôi không bỏ hẳn nhưng hạ kỳ vọng và chỉ làm bước đếm offline, không tốn submission.
- **Sửa theo M1**: tôi sẽ hợp nhất "grep 50 câu public trong corpus" (M1) vào đề xuất A — nó cho cùng thứ mà file chi tiết cho: trần recall. Nếu <50% câu xuất hiện nguyên văn trong index thì mọi thí nghiệm fusion/chunk đều vô nghĩa; đây là data-check rẻ nhất, tôi đã thiếu.
- **Đổi quan điểm với M3**: ngưỡng p > F2/5 tôi chấp nhận làm khung cắt N, nhưng tôi **không** chấp nhận kết luận "giữ nguyên 40 Trung" — đề xuất A của tôi (recall@300 theo từng lượt, theo câu) sẽ quyết định điều đó bằng dữ liệu thay vì bằng ngưỡng trung bình.
- **Phản bác M4**: "BM25 Việt thuần top-100" là đúng hướng nhưng M4 chưa tính nhiễu — nếu Δ với bài 0,1606 nằm trong nhiễu thì không đọc được. Phải gộp với ước nhiễu.

## 3. Đề xuất cuối (tối đa 3)

### Đề xuất A: Audit dữ liệu offline trước mọi submission — file chi tiết per-question + grep câu hỏi trong corpus + đếm duplicate (dựa trên: M2-A cũ + M1.D, M3.C, M4.A/B)
- Giả thuyết: (i) file chấm chi tiết có ít nhất |G|/câu (hoặc gold doc_id) → tính được recall@300 từng lượt truy hồi offline, chẩn đoán chính xác fusion có phá tín hiệu BM25 hay không mà không tốn submission; (ii) một tỷ lệ câu public không xuất hiện nguyên văn trong index do crawl thiếu/trafilatura lược đoạn → trần recall cố định; (iii) top-100 có ≥10% near-duplicate → mất slot.
- Cách làm cụ thể: (1) liệt kê cột file chi tiết ở mức per-question; nếu có gold doc_id → tính recall@300 của bm25_vi, bm25_zh, dense_vi, quota 60/40 hiện tại, và oracle theo |G|; (2) grep 50 câu public (chuỗi NFKC) trong index BM25 của mình, đếm % câu có ≥1 đoạn trùng ≥60% token; (3) MinHash 5-gram trên top-40 bm25_vi của 100 câu, đếm % tài liệu nằm trong cụm ≥2 thành viên.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nếu recall@300(bm25_vi) ≥ 0,52 mà config 100 chỉ đạt R=0,334 → xác nhận fusion/quota loãng, đổi plan sang danh sách BM25 toàn cục (ủng hộ M3-B). Bác bỏ (i) nếu recall@300(bm25_vi) ≈ config hiện tại. Bác bỏ (iii) nếu % duplicate <10% → bỏ dedup hoàn toàn. Bác bỏ (ii) nếu ≥80% câu xuất hiện trong index → trần crawl không phải vấn đề. Nếu file không có gì per-question → (i) tự bác bỏ, chỉ còn LB.
- Kỳ vọng: ra quyết định đúng cho N/quota, gián tiếp +0,05–0,15 | Tự tin: vừa | Chi phí: S (0 submission)

### Đề xuất B: 1 submission ước nhiễu LB + 1 submission chunk span 2.000–4.000 ký tự, cùng tập doc (dựa trên: M2-C cũ, sharpen theo M3-A, M1-B)
- Giả thuyết: F2_chunk 0,084 do |c| < 0,4|g| và chọn vùng sai; nộp 1 span liên tiếp 2.000–4.000 ký tự (chọn quanh cửa sổ BM25 tốt nhất, cắt ở ranh giới câu, **không** lọc dòng rác, **không** nộp >1 chunk/tài liệu) sẽ kéo F2_chunk về gần F2_doc của cùng tập tài liệu.
- Cách làm cụ thể: ngày 1: nộp lại y hệt cấu hình 0,1606 → |Δ| = nhiễu. Ngày 2: cùng top-100 doc, chỉ đổi chunk (L=3.000, giữ nguyên text đã crawl, bỏ bước gom dòng/lọc rác); song song benchmark LCS local trên 20 cặp (ước độ dài |g| lấy từ file chi tiết) để ước thời gian grader.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: ΔF2_chunk > 3×nhiễu đo được → giữ hướng chunk dài làm nền (F2_chunk ≈ F2_doc, mọi cải thiện retrieval sau ăn hệ số 1:1). Nếu ΔF2_chunk ≤ 3×nhiễu → nguyên nhân **không** phải độ dài: kiểm tiếp offline % trang mà vùng 1.000 ký tự đầu nằm ngoài gold-region (dấu hiệu parser lệch) — nếu lệch thì sửa trafilatura trước, không kéo L. Nếu điểm = 0/reject → coi là file size/timeout, hạ L=1.500.
- Kỳ vọng: +0,03 đến +0,08 | Tự tin: vừa-cao | Chi phí: S (2 submission)

### Đề xuất C: Thí nghiệm phân tách duy nhất "tín hiệu BM25 có bị fusion phá không" — top-30 bm25_vi thuần, 1 submission (dựa trên: M1-A, M3-B bước 3, M4-B; sửa theo critique ở mục 1)
- Giả thuyết: nhãn = pool BM25 của BTC; top-30 của riêng lượt bm25_vi đã cache cho P@30 ≥ 0,6, và nếu vậy lỗi là fusion/quota chứ không phải chỉ mục.
- Cách làm cụ thể: một bài LB với N=30, chỉ bm25_vi, chunk của Đề xuất B, không dense/zh/en; đọc P@30 và F2_doc. **Không sweep k** — chỉ một bài, con số P@30 là chẩn đoán.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: P@30 ≥ 0,60 → chuyển ngay sang M3-B (danh sách BM25 toàn cục, quét N), bỏ kế hoạch reranker ra sau. P@30 < 0,35 → "nhãn = pool BM25" vẫn có thể đúng nhưng chỉ mục mình sai → dồn ngày còn lại vào sửa index (bỏ HashingVectorizer, bỏ cắt 10k, thử tách từ — M1-C/M4-C), không tốn thêm submission cho fusion. Nếu F2_doc ≈ 0,24 (không khác 0,1606/30 đáng kể trong nhiễu) → cả hai giả định trên đều chưa được xác nhận, cần kiểm text crawl (grep của Đề xuất A).
- Kỳ vọng: +0,05 đến +0,20 (nếu fusion là thủ phạm, kết hợp với M3-B) | Tự tin: vừa | Chi phí: S (1 submission)

## 4. Bình chọn

VOTES: M3-A, M3-B, M1-A
