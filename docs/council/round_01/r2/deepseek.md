# M4 = deepseek (deepseek-v4-pro) — vai: root_cause — vòng 2

## 1. Nhận xét từng thành viên

- **M1**: điểm mạnh là phát hiện đúng chỗ cần cô lập nhất — HashingVectorizer có thể không phải BM25 thật, và đề xuất nộp **thuần `bm25_vi` đã cache ở 3 mức k** rất rẻ, tách được biến fusion/quota ra khỏi biến chỉ mục. | Lỗ hổng: giả định HashingVectorizer không có IDF chưa chắc đúng nếu pipeline thực tế đã tính IDF riêng; đồng thời A/B/C có thể đổi quá nhiều biến cùng lúc nếu không giữ nguyên chunk. Cũng chưa xử lý nhiễu LB trước khi diễn giải chênh lệch.

- **M2**: điểm mạnh là nêu rõ phải **đo nhiễu LB** trước khi tin các Δ nhỏ, và audit khoảng trống crawl/near-duplicate là đúng hướng để phát hiện trần recall ngoài retrieval. | Lỗ hổng: đề xuất A phụ thuộc vào “file chấm chi tiết có per-question gold” — brief không khẳng định điều này; nếu file chỉ có thống kê tổng thì kế hoạch sụp đổ. Ngưỡng near-duplicate 0,8 cũng chưa hiệu chỉnh theo dữ liệu.

- **M3**: điểm mạnh là lập luận toán học rõ nhất: LCS/|g| đơn điệu không giảm khi chunk dài ra, và F2 = 5H/(4G+N) đủ để bác bỏ quota cố định theo ngôn ngữ; quét L=2k/4k/8k là thí nghiệm phân biệt rất tốt. | Lỗ hổng: tự tin cao nhưng chưa loại trừ H4 — nếu văn bản crawl/trafilatura không chứa gold chunk, hoặc doc_id sai, thì chunk dài vô ích. Dự kiến +0,25–0,40 có thể overfit public; cũng nên thận trọng việc dùng file chấm chi tiết per-question vì có thể chạm luật cấm dò đáp án.

## 2. Tôi đổi quan điểm thế nào (giữ / bỏ / sửa gì, vì sao)

- **Giữ**: chunk dài là hướng có cơ sở nhất để kéo F2_chunk; nhưng tôi **sửa** đề xuất cũ của mình: không nộp ngay toàn văn mà quét L=2k/4k/8k như M3-A để vừa chọn mức an toàn timeout, vừa xác minh độ dài thực sự là nguyên nhân.
- **Bỏ**: không vội nộp “toàn văn + BM25 Việt thuần” cùng lúc như tôi từng định — vì nếu trộn thay đổi retrieval lẫn chunk, LB không cho biết cái nào cải thiện. Trước hết phải tách riêng tín hiệu doc.
- **Sửa**: tiếp thu M1-A để làm phép thử `bm25_vi` thuần trước, và tiếp thu M2-C để dành 1 slot đo nhiễu. Tôi cũng hạ mức kỳ vọng so với M3: chỉ coi là xác nhận hướng đi, không cam kết +0,4 ngay.

## 3. Đề xuất cuối (tối đa 3)

### Đề xuất A: X-quang tín hiệu BM25 thuần Việt ở 3 mức K (dựa trên: M1-A, M3-B)
- Giả thuyết: Điểm doc tụt vì (H1) RRF + dense + hạn mức Trung/Anh làm loãng các tài liệu Việt đúng mà BM25 đã xếp cao, hoặc (H2) chính chỉ mục BM25 của đội (HashingVectorizer, cắt 10k ký tự, token âm tiết) không khớp BM25 của BTC. Hai giả thuyết cần cách xử lý khác hẳn nhau.
- Cách làm cụ thể: Dùng 3 danh sách `bm25_vi` đã cache sẵn, tạo 3 bài nộp **thuần Việt**: k = 30, 60, 100. Không dense, không zh/en, không RRF, không quota. Giữ nguyên chunk như bài 0,1606 (1 chunk ≈1.000 ký tự/tài liệu) để doc metric không bị nhiễu. Nếu còn slot, nộp lại đúng file 0,1606 để ước nhiễu LB; nếu giới hạn slot thì ưu tiên 3 mức k.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ:
  - Nếu **k=30 có P_doc ≥ 0,6 và R_doc ≥ 0,35**, H1 được xác nhận: fusion/quota là thủ phạm chính; chuyển sang tinh chỉnh k thuần BM25 và bỏ reranker trước mắt.
  - Nếu **cả 3 đều P_doc < 0,35**, H1 không giải thích được; H2 (chỉ mục/text) gần như đúng → đi thẳng Đề xuất C, không tiếp tục tăng k trên ranker hỏng.
  - Nếu k=30 P cao nhưng k=100 P giảm mạnh và hit tăng ít, thêm tài liệu từ ranker hiện tại không đáng; cần sửa BM25 trước khi quét N lớn.
- Kỳ vọng: nếu H1 đúng, F2_doc có thể 0,24 → 0,45–0,55 | Tự tin: vừa | Chi phí: S (3–4 lượt nộp)

### Đề xuất B: Quét độ dài chunk trên retrieval đóng băng (dựa trên: M3-A, M1-B)
- Giả thuyết: F2_chunk tụt thảm do **cửa sổ 1.000 ký tự** không phủ được ≥40% chunk tham chiếu (H3), chứ không phải do văn bản crawl không chứa gold (H4). Vì mẫu số là |g|, chunk nộp dài hơn gần như không bị phạt, nên nếu đoạn crawl có chứa gold, R_chunk/R_doc phải tăng theo L.
- Cách làm cụ thể: Chọn retrieval tốt nhất từ Đề xuất A (nếu chưa có, giữ đúng retrieval bài 0,1606). Nộp 3 file chỉ đổi phần chunk, giữ nguyên N và thứ tự tài liệu:
  - L = 2.000 ký tự
  - L = 4.000 ký tự
  - L = 8.000 ký tự
  Mỗi tài liệu nộp **đúng 1 chunk**, span liên tục, vị trí trung tâm là nơi cosine BGE-M3 cao nhất, hoặc nếu tài liệu ngắn thì toàn văn. Dùng text thô chưa lọc dòng rác để hedging parser BTC.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ:
  - Nếu R_chunk/R_doc tăng đơn điệu và **≥ 0,8 ở L = 8k**, H3 đúng; tối ưu L trong 2k–8k.
  - Nếu vẫn **≤ 0,45** dù L đã tăng, bác bỏ H3: lỗi nằm ở văn bản crawl/parser hoặc doc_id, chuyển sang Đề xuất C thay vì kéo dài hơn.
  - Nếu timeout/reject ở L=8k, hạ về 4k/2k; nhưng vẫn đọc được xu hướng.
- Kỳ vọng: nếu H3 đúng, F2_chunk 0,084 → 0,20–0,24 | Tự tin: vừa | Chi phí: S (3 lượt nộp)

### Đề xuất C: Audit offline chỉ mục + văn bản trước khi viết lại BM25 (dựa trên: M1-C, M2-B)
- Giả thuyết: Nếu A không đạt P_doc cao, nguyên nhân là (H2/H4) một trong ba: BM25 hiện tại không tương đương BM25 thật; trafilatura/cắt 10k làm mất nội dung; doc_id/crawl lệch hoặc trùng lặp làm tắc top-k. Đây là giả thuyết cạnh tranh cần tách trước khi tốn submission vào viết lại chỉ mục.
- Cách làm cụ thể:
  1. Trên 100k doc Việt, dựng BM25Okapi/BM25S full-text (token âm tiết) và so top-100 với `bm25_vi` hiện tại: tính rank correlation và overlap top-30.
  2. Lấy 30–50 URL trong top-100 của bài best hiện tại, so raw HTML với output trafilatura: % nội dung bị bỏ, % trang mà 1.000 ký tự quan trọng nằm ngoài text đã trích.
  3. Đếm % doc_id nộp thuộc đúng file URL BTC; kiểm tra redirect/http/www; đếm near-duplicate bằng SimHash trong top-100.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ:
  - Nếu BM25Okapi full-text **trùng ≥80% top-30** với `bm25_vi` hiện tại và rank corr ≥0,9 → H2 (chỉ mục) gần như sai; lỗi nghiêng về H4 (crawl/text).
  - Nếu trafilatura bỏ ≥15% nội dung trên nhiều trang top, hoặc ≥2% doc_id sai/redirect → H4 xác nhận; sửa crawl trước khi thử BM25 mới.
  - Nếu top-30 khác hẳn (<50% trùng) và văn bản đã đầy đủ → đổ slot vào viết lại BM25 theo hướng full-text/tách từ là đúng.
- Kỳ vọng: không trực tiếp tăng điểm; giúp không đốt 3–5 lượt nộp vào hướng sai | Tự tin: thấp-vừa | Chi phí: M (offline, vài giờ CPU/RAM)

## 4. Bình chọn
VOTES: M1-A, M3-A, M3-B
