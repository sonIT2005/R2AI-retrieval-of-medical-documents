# M3 = kimi (moonshotai/kimi-k3) — vai: alternative — vòng 2

## 1. Nhận xét từng thành viên
- M1: điểm mạnh — suy luận N_doc≈203/N_chunk≈113 của đội #3 từ tỉ số R/P là sắc và khớp với đại số F2; phát hiện F2_doc tụt giữa bài A và G ("dựng lại" làm đổi tập truy xuất) là cờ đỏ thật, cần debug ngay. | lỗ hổng — toàn bộ Đề xuất A dựa trên giả định format cho phép `relevant_chunks ⊂ relevant_docs` mà brief chưa xác nhận (chính M4 cũng phải ghi "cần hỏi BTC"); trọng số 0,78/0,22 và các mốc L=4.500/2.500 là số học tự đặt, chưa có phép đo nào ủng hộ; đề xuất 5 bài private quá sớm khi chưa có 1 thí nghiệm nào chạy.
- M2: điểm mạnh — kỷ luật ablation (đổi 1 biến/lần, kiểm byte thật trên file ZIP sau nén), nhắc đúng rằng precision biên của bm25_vi không suy ra được cho danh sách fused. | lỗ hổng — quá thận trọng: kỳ vọng +0,00–0,01 ở mức dưới nhiễu LB (±0,01 theo M4) nghĩa là các thí nghiệm của M2 không phân biệt được thắng/thua; xếp reranker cuối cùng mâu thuẫn với bằng chứng P/R của #3 (họ thắng bằng chất lượng xếp hạng, không phải độ sâu).
- M4: điểm mạnh — đại số F2 = 5T/(4G+N) + ngưỡng precision biên hiệu chỉnh ~0,06–0,07 (tính cả pha loãng chunk) là đóng góp lý thuyết quan trọng nhất vòng này: nó cho thấy plan "quét N lớn hơn" của đội có thể vô ích nếu không sửa xếp hạng trước; bài "dò độ sâu N=200 với L theo thứ hạng" là cách đo precision biên fused duy nhất khả thi không cần nhãn. | lỗ hổng — con số acc@1 0,79 vs 0,57 của Vietnamese_Reranker đo trên benchmark retrieval tiếng Việt tổng quát, chưa chứng minh chuyển dịch sang y khoa Việt/Trung; đốt 3 slot nộp chỉ để chẩn đoán (VI-only, ZH-only, N=200) là xa xỉ khi 2 trong 3 có thể suy gần đúng offline.

## 2. Tôi đổi quan điểm thế nào
- **Bỏ HyDE (M3-B cũ):** M1 và M2 cùng phản biện độc lập — HyDE không giải quyết nút thắt (candidate recall do cắt 2.000 ký tự + pha loãng quota), và bài gốc HyDE (Gao et al., 2022) ghi nhận rủi ro hallucination. Tôi chấp nhận: nộp HyDE bây giờ là đốt slot cho biến không nằm trên đường tới nút thắt.
- **Sửa M3-A:** hội tụ với M4-B — không cần encode lại pool 500 ứng viên mới; bước 5 của pipeline đã tính cos(chunk, query), chỉ cần dùng max-sim làm điểm tài liệu. Nhưng giữ phép đo offline của tôi (tỉ lệ argmax-chunk nằm sau ký tự 2.000) làm cổng quyết định trước khi tốn lượt nộp — đây là thứ M4-B thiếu.
- **Giữ M3-C (near-dup)** vì không ai phản biện và phép đo bước 1 miễn phí; nhưng hạ ưu tiên sau hai đề xuất kia.
- **Tiếp thu M4:** ngưỡng precision biên ~0,06–0,07 làm tôi đổi thứ tự ưu tiên — sửa xếp hạng (max-sim, reranker) trước, độ sâu N sau, thay vì ngược lại như plan hiện tại của đội.

## 3. Đề xuất cuối (tối đa 3)
### Đề xuất A: Max-sim cấp chunk làm điểm tài liệu, có cổng offline (dựa trên: M4-B, M3-A)
- Giả thuyết: vector 2.000 ký tự đầu làm mù ~44% nội dung tài liệu Việt (TB 3.553 ký tự); score(doc) = max cos(chunk, query) trên các chunk bước 5 đã encode sẽ kéo tài liệu đúng ở nửa sau vào top — tăng T ở N cố định, đúng khoảng cách với #3. BGE-M3 hỗ trợ multi-vector gốc (+5,1 điểm trên MLDR long-doc, arXiv 2402.03216 — chưa kiểm chứng trên y khoa Việt).
- Cách làm cụ thể: (1) Cổng offline 0 chi phí: với top-300 fused hiện có của 1.200 câu, đo tỉ lệ tài liệu có argmax-chunk nằm sau ký tự 2.000. Nếu <15% → huỷ, không tốn lượt. (2) Nếu ≥20%: thêm lượt "chunkmax_vi/zh" vào RRF (hoặc thay dense 1-vector), giữ nguyên N, L=4.000 của bài G. Bonus: vị trí argmax-chunk dùng luôn làm tâm mở rộng chunk → L ngắn hơn vẫn trúng, tiết kiệm byte (trả lời câu hỏi 2 của brief).
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: 1 bài nộp = G + chunkmax. Bác bỏ nếu F2_doc không tăng ≥ +0,02 so với 0,2309 (nhiễu LB ±0,01, cần vượt 2σ). Nếu thắng, mới tính chuyện reranker xếp sau.
- Kỳ vọng: +0,02–0,05 tổng | Tự tin: vừa | Chi phí: S–M (0 GPU mới nếu chunk embedding bước 5 đã cache)

### Đề xuất B: Ba phép đo chẩn đoán gộp vào 1–2 bài nộp (dựa trên: M4-A, M1-A)
- Giả thuyết: đội thiếu 3 số quyết định — precision biên của xếp hạng fused, đóng góp thật của nhánh Trung, và format có cho `relevant_chunks ⊂ relevant_docs` không; đo xong mới xếp ưu tiên 8 ngày được. Tôi đồng ý với M4 nhưng siết chi phí: không nộp ZH-only riêng (suy gần đúng offline từ precision từng lượt đã có), gộp "dò độ sâu" và "tách N_doc/N_chunk" thành một bài.
- Cách làm cụ thể: (1) Hỏi BTC/FAQ hoặc 1 bài nộp thử với `relevant_docs`=180 ID nhưng `relevant_chunks` chỉ 110 tài liệu đầu (L bậc thang 4.000/2.000) — một bài này đồng thời kiểm chứng format VÀ đo precision biên fused dải 111→180 = (T@180 − T@100)/80. (2) Nếu biên ≥0,08 → độ sâu đáng giá, làm lưới N∈{150, 200}; nếu ≤0,05 → khoá độ sâu, dồn toàn lực cho Đề xuất A + reranker. (3) Debug diff relevant_docs giữa bài A và G (cờ đỏ của M1) trước mọi bài nộp mới.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nếu bài tách N_doc/N_chunk bị chấm lỗi hoặc F2_chunk tụt bất thường → format không cho phép, quay về N_doc=N_chunk và mọi tính toán ngưỡng biên theo M4 (~0,06–0,07). Nếu F2_doc tăng ≥+0,02 thuần nhờ đuôi 111–180 → chấp nhận chiến lược tách.
- Kỳ vọng: +0,02–0,06 trực tiếp; giá trị thông tin định hướng toàn bộ 8 ngày | Tự tin: cao (về giá trị thông tin), vừa (về điểm trực tiếp) | Chi phí: S (1–2 slot, 0 GPU)

### Đề xuất C: Khử near-duplicate trước xếp hạng (dựa trên: M3-C)
- Giả thuyết: corpus crawl 1,17M trang y khoa gần chắc có bài đăng lại; nếu nhãn gắn 1 bản, nộp cụm trùng = mất P doc và tốn byte — giải phóng cả slot lẫn ngân sách 95 MB. P doc 0,174 thấp hơn #4/#5 (0,24/0,27) ở độ dài tương đương là dấu hiệu gián tiếp.
- Cách làm cụ thể: MinHash trên văn bản sạch (CPU <1 giờ), cụm Jaccard ≥0,8, giữ bản điểm cao nhất mỗi cụm, nhường slot cho tài liệu kế tiếp. Cổng offline: đo tỉ lệ cặp near-dup trong top-100 của 50 câu ngẫu nhiên — <5% thì huỷ.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nếu ≥10%, nộp 1 bài G+dedup; bác bỏ nếu F2_doc không tăng ≥+0,01.
- Kỳ vọng: +0,005–0,02 | Tự tin: thấp | Chi phí: S

## 4. Bình chọn
VOTES: M1-A, M4-A, M4-C
