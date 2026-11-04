# M1 = gemini (google/gemini-4-argon) — vai: pragmatist — vòng 1

## 1. Chẩn đoán nhanh
Kết quả đang dừng ở `0,2207` (`R_doc = 0,322`) trước hết vì đội đang **đánh đồng số tài liệu nộp `N_doc` với số đoạn trích `N_chunk`**: nhìn vào thông số của đội #3 (`P_doc = 0,18, R_doc = 0,61` nhưng `P_chunk = 0,25, R_chunk = 0,47`) và #4 (`P_chunk = 0,28 > P_doc = 0,24`), về mặt toán học `P_chunk > P_doc` chứng minh họ nộp `N_doc ≈ 180–210` ID trong `relevant_docs` (chỉ tốn `< 1 MB` nén) nhưng chỉ nộp chunk cho `N_chunk ≈ 90–115` tài liệu đầu trong `relevant_chunks`. Thứ hai, hạn mức cứng `40 Việt + 50/60 Trung` đang tự bóp nghẹt `R_doc`: nhóm Việt sau RRF đạt `P@40 ≈ 0,38` (~15,2 tài liệu đúng), nghĩa là 50 tài liệu Trung + 10 Anh trong bài G chỉ đóng góp vỏn vẹn ~2,2 tài liệu đúng (`P ≈ 0,037`), trong khi tài liệu Việt hạng 41–150 có precision biên vẫn vượt xa ngưỡng có lời của F2 (`F2/5 ≈ 0,046` theo lý thuyết cắt ngưỡng F-measure tại https://arxiv.org/abs/1402.1892). Thứ ba, chất lượng xếp hạng nhóm Việt đang bị kéo tụt do RRF cào bằng trọng số giữa `bm25_vi` rất yếu (`P@30 = 0,156`) với `dense_vi_vi` mạnh (nhược điểm đã được chứng minh của RRF tại https://arxiv.org/abs/2210.11934), cộng thêm việc vector dense chỉ nhìn `2.000` ký tự đầu (`FirstP`) làm lọt các bài y khoa Việt dài (trung bình `3.553` ký tự). **Thứ tự ưu tiên (a–f) & việc cần DỪNG NGAY**: Làm ngay **(a) Tách `N_doc > N_chunk` + (b) Hạ trọng số BM25/chuẩn hóa điểm + (f) Tăng mạnh tỷ lệ Việt** (Ngày 1–2, 0 giờ GPU) → **(c) Reranker `bge-reranker-v2-m3` kết hợp (f) phân bổ Việt/Trung động & định tâm cửa sổ trượt** (Ngày 3–4, ~1 giờ GPU) → **(d) Dense `Tail-MaxP` chỉ cho phần đuôi `> 2.000` ký tự của bài Việt** (Ngày 5–6, ~2,5 giờ GPU); **DỪNG NGAY** toàn bộ nhánh tiếng Anh (0 nhãn đúng), **DỪNG** tăng quota tiếng Trung kiểu bài H, và **BỎ QUA (e)** mở rộng câu hỏi bằng Qwen3-8B (HyDE dễ sinh nhiễu thuật ngữ y khoa và tốn GPU nhưng không giải quyết nút thắt cắt ngưỡng).

---

## 2. Đề xuất (tối đa 3, xếp theo kỳ vọng/chi phí)

### Đề xuất A: Tách rời `N_doc` khỏi `N_chunk` + Phá hạn mức 40 Việt + Gộp điểm có trọng số & Phân bổ `L` bậc thang
- **Giả thuyết:**
  1. *(Giả định định dạng bài nộp tính điểm `relevant_docs` và `relevant_chunks` độc lập theo công thức `(F2_doc + F2_chunk)/2`)*: Danh sách `relevant_docs` chỉ chứa chuỗi `doc_id` (~20 byte/ID), nên tăng `N_doc` từ 100 lên `180–200` chỉ tốn `< 1 MB` bzip2 nhưng đẩy `R_doc` từ `0,32` lên `0,48–0,55` vì đạo hàm của `F2 = 5TP / (4|G| + N)` dương chừng nào precision biên `p_m > F2 / 5 ≈ 0,046` (https://arxiv.org/abs/1402.1892).
  2. Nâng hạn mức tài liệu Việt từ `40` lên `135–150` tài liệu/câu và hạ trọng số `bm25_vi` xuống `0,25` so với `dense_vi_vi` (`1,0`) — hoặc dùng tổ hợp lồi điểm chuẩn hóa (Convex Combination) thay cho RRF không trọng số theo Bruch et al. (2023) (https://arxiv.org/abs/2210.11934) — sẽ lấy lại hàng chục tài liệu Việt đúng ở hạng 41–150 đang bị 50–60 tài liệu Trung chất lượng thấp chiếm chỗ.
  3. Với ngân sách `~350 KB JSON/câu`, chỉ xuất `relevant_chunks` cho top `N_chunk = 110` tài liệu đầu theo độ dài bậc thang (hạng 1–50: `L = 4.500`, hạng 51–110: `L = 2.500`, hạng 111–180: không xuất chunk) giúp tối đa hóa đồng thời cả `F2_doc` và `F2_chunk` dưới ngưỡng 95 MB bzip2.
- **Dựa trên bằng chứng nào trong brief:**
  - Đội #3 đạt `P_doc = 0,18, R_doc = 0,61` (`R/P = 3,39 → N_doc ≈ 203`) nhưng `P_chunk = 0,25, R_chunk = 0,47` (`R/P = 1,88 → N_chunk ≈ 113`); đội #4 cũng có `P_chunk (0,28) > P_doc (0,24)`.
  - Bài G (`40 Việt + 50 Trung + 10 Anh`) có `P_doc = 0,174` (~17,4 tài liệu đúng/câu), nhưng riêng nhóm Việt sau RRF đạt `P ≈ 0,38` (`40 × 0,38 = 15,2` tài liệu đúng) → 50 bài Trung + 10 Anh chỉ trúng ~2,2 bài.
  - `bm25_vi` thuần rất yếu (`P@30 = 0,156`), độ trùng `bm25_vi ∩ dense_vi_vi = 15%`.
- **Cách làm cụ thể:**
  1. Xóa toàn bộ nhánh tiếng Anh. Trong nhóm Việt, gộp điểm bằng chuẩn hóa z-score trên top-300 mỗi lượt: `score_vi(d) = 0,78 * z(dense_vi_vi) + 0,22 * z(bm25_vi)` (hoặc RRF có trọng số `0,78 : 0,22` với `k=60`). Trong nhóm Trung: `score_zh(d) = 0,50 * z(dense_zh_zh) + 0,35 * z(dense_vi_zh) + 0,15 * z(bm25_zh)`.
  2. Lấy `relevant_docs` gồm **`N_doc = 180` tài liệu/câu** theo tỷ lệ **140 Việt + 40 Trung** (khớp tỷ lệ corpus 698k/237k).
  3. Lấy `relevant_chunks` chỉ cho **`N_chunk = 110` tài liệu đầu** (ưu tiên sắp xếp xen kẽ theo phân vị điểm giữa Việt và Trung, ví dụ 85 Việt + 25 Trung):
     - Hạng 1–50: mở rộng `L = 4.500` ký tự (Trung `2.250`).
     - Hạng 51–110: mở rộng `L = 2.500` ký tự (Trung `1.250`).
     - Hạng 111–180: **không xuất vào `relevant_chunks`**.
  4. Khi ghi file JSON, bật `json.dump(..., ensure_ascii=False, separators=(',', ':'))` để loại bỏ khoảng trắng thừa, tiết kiệm ~12–18% dung lượng trước khi nén bzip2.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:**
  - *Bước 1 (1 bài nộp)*: Giữ `N_doc = N_chunk = 100, L = 4.000` như bài G/H, nhưng đổi hạn mức thành `80 Việt + 20 Trung` + trọng số `dense_vi_vi` gấp 3,5 lần `bm25_vi`. **Tiêu chí bác bỏ**: Nếu `F2_doc` không vượt `0,260` (`+0,03` so với bài G), bác bỏ giả thuyết nhóm Trung đang làm loãng.
  - *Bước 2 (2 bài nộp)*: Giữ thứ tự xếp hạng của Bước 1, nộp `N_doc = 180` (và thử `N_doc = 210`) kết hợp `N_chunk = 110` bậc thang `L = 4.500 / 2.500`. **Tiêu chí bác bỏ**: Nếu tăng `N_doc` từ 100 lên 180 làm giảm `F2_doc` hoặc tăng `< +0,02`, nghĩa là precision biên hạng 101–180 `< 0,046` → lùi `N_doc` về 140.
- **Kỳ vọng:** `+0,06 đến +0,09` điểm (`0,2207 → 0,28–0,31`) | **Tự tin:** Cao | **Chi phí:** S (~2 giờ code CPU, 0 giờ GPU, thực hiện Ngày 1–2)

---

### Đề xuất B: Rerank đa ngữ `BAAI/bge-reranker-v2-m3` trên Top-250 + Định tâm Chunk bằng cửa sổ trượt lai + Cắt ngưỡng động
- **Giả thuyết:**
  1. Cắt tài liệu thành các đoạn 1.000 ký tự rời rạc (không chồng lấn) làm chunk tham chiếu `g` dễ bị cắt đôi ở ranh giới, khiến khi hạ `L` xuống `2.000` thì `F2_chunk / F2_doc` rơi từ `0,91` xuống `0,63`. Dùng cửa sổ trượt `500` ký tự (bước nhảy `250`) kết hợp điểm `BGE-M3 cosine + mật độ token trùng câu hỏi` sẽ đặt tâm mở rộng đúng vùng giàu LCS token nhất.
  2. Chấm điểm cặp `(câu hỏi tiếng Việt, đoạn 1.000 ký tự quanh tâm tốt nhất)` cho top-250 ứng viên/câu bằng cross-encoder `BAAI/bge-reranker-v2-m3` (https://huggingface.co/BAAI/bge-reranker-v2-m3) đưa cả tài liệu Việt và Trung về **cùng một thang xác suất hiệu chuẩn `p_i = sigmoid(logit_i)`**. Nhờ đó, hệ thống tự động phân bổ tỷ lệ Việt/Trung và số lượng tài liệu `N_doc(q)` theo từng câu hỏi (vốn có nhãn dao động mạnh từ 5 đến 190 tài liệu/câu).
- **Dựa trên bằng chứng nào trong brief:**
  - Số tài liệu đúng/câu biến thiên rất rộng (`5–190`, trung vị `60`) và điểm tính **macro-F2** từng câu.
  - Ở `L = 2.000` (Bài E), `F2_chunk / F2_doc` chỉ đạt `0,0775 / 0,1240 = 0,625`, chứng tỏ định tâm hiện tại bị lệch khi thu hẹp cửa sổ mở rộng.
  - Tổng số câu hỏi chỉ là `1.200`: với top-250 ứng viên/câu (`300.000` cặp câu hỏi - đoạn ngắn), model 568M tham số `bge-reranker-v2-m3` chạy `fp16` trên RTX 5060 Ti 16GB chỉ mất **~12–15 phút** (cộng ~25 phút mã hóa BGE-M3 cho các đoạn của ~120k tài liệu ứng viên duy nhất).
- **Cách làm cụ thể:**
  1. **Định tâm cửa sổ trượt lai (Sliding-Window Hybrid Centering)**: Với mỗi tài liệu trong top-250 ứng viên/câu (190 Việt + 60 Trung từ Đề xuất A), chia văn bản thành các cửa sổ `w_k` dài `500` ký tự (Trung `250`), bước nhảy `250` ký tự (Trung `125`). Tính điểm từng cửa sổ: `s(w_k) = 0,8 * cos_BGE(q, w_k) + 0,2 * (số âm tiết/từ khóa của q xuất hiện trong w_k / |q|)`. Chọn cửa sổ `k*` cực đại hóa tổng trượt 3 cửa sổ liên tiếp `s(w_{k-1}) + 2*s(w_k) + s(w_{k+1})` làm **tâm mở rộng**.
  2. **Chạy Cross-Encoder Reranker**: Trích đoạn `1.000` ký tự (Trung `500`) quanh tâm `k*` của mỗi ứng viên, đưa cặp `(query_vi, đoạn_1000)` vào `BAAI/bge-reranker-v2-m3` (`use_fp16=True`, `max_length=512`, `batch_size=128`). Kết hợp điểm xếp hạng cuối: `S_final(q, d) = 0,65 * sigmoid(logit_rerank) + 0,35 * norm_score_Stage1(q, d)`.
  3. **Phân bổ Việt/Trung động & Cắt ngưỡng `N_doc(q)` động**:
     - Xếp chung ứng viên Việt và Trung theo `S_final(q, d)` giảm dần (tự động giải quyết bài toán phân bổ Việt/Trung theo câu hỏi).
     - Chọn vào `relevant_docs` mọi tài liệu có `S_final(q, d) ≥ \tau_doc`, kẹp trong khoảng `N_doc(q) ∈ [70, 230]`, với `\tau_doc` được chọn sao cho trung bình trên 1.200 câu đạt `mean(N_doc) = 185`.
     - Chọn vào `relevant_chunks` tối đa `N_chunk(q) = min(115, N_doc(q))` tài liệu đầu, với độ dài mở rộng `L_i` nội suy tuyến tính theo `S_final` từ `4.500` (hạng 1) xuống `2.200` (hạng 115) để dùng vừa khít `340 KB JSON/câu`.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:**
  - *Bước 1 (Kiểm chứng định tâm cửa sổ trượt - 0 giờ GPU mới)*: Áp dụng ngay cách chọn tâm cửa sổ trượt có cộng điểm từ khóa lên bài nộp tốt nhất của Đề xuất A. **Tiêu chí bác bỏ**: Nếu `F2_chunk / F2_doc` không tăng thêm `≥ +0,03`, giữ nguyên cách chọn chunk cũ.
  - *Bước 2 (Kiểm chứng Reranker + Động hóa)*: Nộp 1 bài dùng `S_final` với `N` cố định (`N_doc = 185, N_chunk = 115`), và 1 bài bật ngưỡng động `N_doc(q) ∈ [70, 230]`. **Tiêu chí bác bỏ**: Nếu `S_final` không tăng điểm tổng `≥ +0,015` so với Đề xuất A, hạ trọng số reranker xuống `0,4`. Nếu cắt ngưỡng động thua `N` cố định trên LB, quay về `N` cố định cho tập Private.
- **Kỳ vọng:** `+0,03 đến +0,05` điểm cộng thêm (`→ 0,32–0,35`) | **Tự tin:** Cao | **Chi phí:** M (~40 phút GPU + 4 giờ code, thực hiện Ngày 3–4)

---

### Đề xuất C: Bổ sung Dense Vector phần đuôi (`Tail-MaxP`) CHỈ cho các tài liệu Việt dài `> 2.000` ký tự
- **Giả thuyết:**
  - Tài liệu Việt dài trung bình `3.553` ký tự, nhưng `dense_vi_vi` hiện chỉ mã hóa `2.000` ký tự đầu (`FirstP`). Trong bài viết y khoa, phần điều trị, liều thuốc và chống chỉ định thường nằm ở nửa cuối (`> 2.000` ký tự). Khi câu hỏi nhắm vào phần cuối và dùng từ đồng nghĩa, tài liệu bị trượt khỏi top-300 ngay ở Stage 1 nên Reranker ở Đề xuất B không bao giờ nhìn thấy.
  - Thay vì mã hóa lại toàn bộ corpus cấp chunk (tốn ~12 giờ GPU), ta **tái sử dụng 100% vector 2.000 ký tự đầu đã có** và chỉ mã hóa thêm tối đa 2 đoạn đuôi (`[1.600 : 3.600]` và `[3.200 : 5.200]`) cho các bài Việt dài `> 2.000` ký tự, rồi gộp điểm cấp tài liệu bằng phép lấy cực đại `MaxP` (https://arxiv.org/abs/2402.03216). Cách này cắt giảm 65% thời gian GPU (chỉ mất **~2,2 giờ GPU** chạy ngầm ban đêm).
- **Dựa trên bằng chứng nào trong brief:**
  - Mục 1, 2 & 4: Corpus Việt gồm `698k` bài (TB `3.553` ký tự), hiện chỉ lấy `1 vector/tài liệu, 2.000 ký tự đầu`. Mã hóa toàn bộ `1,175M` bài mất `~4 giờ` → mã hóa thêm ~650k đoạn đuôi chỉ mất ~2,2 giờ.
- **Cách làm cụ thể:**
  1. Quét `698k` tài liệu Việt, chỉ lọc các bài có `len(text) > 2.000`. Cắt thêm tối đa 2 đoạn: `seg_2 = text[1600:3600]` và (nếu `len(text) > 3.600`) `seg_3 = text[3200:5200]`.
  2. Sắp xếp các đoạn theo độ dài token giảm dần rồi mã hóa bằng BGE-M3 (`fp16`, `max_length=512`), đẩy thêm vào FAISS index của `dense_vi_vi`.
  3. Khi truy vấn `dense_vi_vi`, lấy top-600 vector gần nhất rồi rút gọn theo `doc_id` bằng `score(d) = max(cos(q, vec_head), cos(q, vec_seg2), cos(q, vec_seg3))` để lấy đủ 300 tài liệu độc nhất đưa vào pipeline Đề xuất A + B.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:**
  - *Kiểm chứng nội bộ trước khi nộp*: Đo tỷ lệ tài liệu mới lọt vào top-180 của 1.200 câu hỏi nhờ `seg_2, seg_3`. Nếu `< 5%` danh sách thay đổi, dừng ngay không tốn lượt nộp. Nếu `≥ 8%`, nộp 1 bài kết hợp A + B + C lên LB.
  - *Tiêu chí bác bỏ*: Nếu `R_doc` trên LB tăng `< +0,015` so với bài A + B, dừng việc mở rộng `Tail-MaxP` sang tiếng Trung.
- **Kỳ vọng:** `+0,02 đến +0,035` điểm cộng thêm (`→ 0,34–0,37`) | **Tự tin:** Vừa–Cao | **Chi phí:** M (~2,5 giờ GPU ban đêm + 2 giờ code, thực hiện Ngày 5–6)

---

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief
1. **Điểm đáng ngờ nghiêm trọng giữa Bài A và Bài G (`F2_doc` bị tụt ngầm):**
   - Trong bảng kết quả, khi tăng `L` từ `1.000 → 2.000 → 4.000` ở chuỗi Bài C → E → F, điểm `F2_doc` giữ nguyên tuyệt đối (`0,1240`), vì độ dài chunk `L` không ảnh hưởng tới `relevant_docs`. Thế nhưng ở **Bài G ("= A dựng lại, chunk L=4.000")**, `F2_doc` lại **tụt từ `0,2375` (Bài A) xuống `0,2309` (`R_doc` tụt từ `0,334` xuống `0,322`)**! Điều này chứng tỏ bước "dựng lại" ở Bài G đã làm thay đổi tập tài liệu truy xuất (do thay đổi bản dịch của Qwen3-8B khi `temperature > 0`, thay đổi bước làm sạch trafilatura làm mất văn bản, hoặc lỗi thứ tự tie-break trong RRF). Đội cần kiểm tra diff trực tiếp tập `relevant_docs` giữa file nộp Bài A và Bài G ngay trong Ngày 1.
2. **Thiếu thí nghiệm cô lập đóng góp thực tế của nhóm tiếng Trung:**
   - Đội đã thử `bm25_vi` thuần (Bài B, C, D) nhưng chưa từng nộp 1 bài **`100 Việt (dense + bm25) + 0 Trung`** để biết 50–60 tài liệu Trung đang cộng thêm điểm hay đang lấy mất slot của các tài liệu Việt đúng.
3. **Chưa rõ ràng buộc hợp lệ giữa `relevant_docs` và `relevant_chunks` của hàm chấm điểm:**
   - Khi tách `N_doc = 180` và `N_chunk = 110`, cần đảm bảo 110 `doc_id` trong `relevant_chunks` là tập con của 180 `doc_id` trong `relevant_docs`. Ngoài ra, brief chưa nêu rõ nếu nộp **2 chunk rời nhau có cùng `doc_id`** (cho top-10 bài Việt cực dài `> 7.000` ký tự) thì hàm chấm tính `TP_chunk` theo từng phần tử dự đoán hay gộp theo `doc_id` — có thể kiểm tra rẻ bằng 1 lượt nộp dư trong Ngày 6.
4. **Ngân sách thời gian 8 ngày & Chiến lược 5 bài Private LB (Trả lời Câu hỏi 3):**
   - **Lịch trình 8 ngày**: Ngày 1–2: Debug chênh lệch A vs G + Chạy Đề xuất A (~4 lượt nộp). Ngày 3–4: Chạy Đề xuất B (`bge-reranker-v2-m3` + định tâm cửa sổ trượt + quét ngưỡng, ~6 lượt nộp). Ngày 5–6: Chạy Đề xuất C (`Tail-MaxP` cho bài Việt dài, ~4 lượt nộp). Ngày 7–8: Tinh chỉnh trọng số gộp & đóng băng 5 bài Private.
   - **Danh mục 5 bài Private LB (phòng hộ rủi ro lệch phân phối trên 600 câu ẩn)**:
     - *Bài 1 (Neo an toàn tuyệt đối - Không phụ thuộc Reranker hay ngưỡng động)*: Đề xuất A + C (`Tail-MaxP` + Weighted Z-score/RRF), cố định `N_doc = 180 (140 Việt + 40 Trung)`, `N_chunk = 110` bậc thang `L = 4.500 / 2.500`.
     - *Bài 2 (Chủ lực ổn định - Reranker với `N` cố định)*: Đề xuất A + B + C đầy đủ (`S_final` kết hợp `bge-reranker-v2-m3` và Stage 1), nhưng **khóa cố định** `N_doc = 185, N_chunk = 115` cho mọi câu hỏi (chống rủi ro lệch thang điểm `sigmoid` trên tập Private).
     - *Bài 3 (Tối ưu Macro-F2 - Cắt ngưỡng động)*: Cấu hình A + B + C có điểm Public LB cao nhất với `N_doc(q) ∈ [70, 230]` biến thiên theo điểm `S_final`.
     - *Bài 4 (Phòng hộ Recall cao)*: Giống Bài 2 nhưng đẩy `N_doc = 225` (175 Việt + 50 Trung) để ăn trọn điểm nếu tập Private có trung vị tài liệu đúng/câu cao hơn 60.
     - *Bài 5 (Ensemble xếp hạng)*: Gộp RRF giữa thứ hạng tài liệu của Bài 1 (Bi-encoder `Tail-MaxP` + BM25) và Bài 3 (Cross-encoder `bge-reranker-v2-m3`), xuất `N_doc = 190, N_chunk = 115`.

---

## 4. Nguồn đã tra cứu
- *BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation* — https://arxiv.org/abs/2402.03216 — Chứng minh kiến trúc nhúng đa ngữ/đa độ hạt của BGE-M3 và cơ sở gộp điểm nhiều đoạn (`MaxP`) trên tài liệu dài.
- *An Analysis of Fusion Functions for Hybrid Retrieval* (Bruch, Gai, & Ingber, ACM TOIS / arXiv) — https://arxiv.org/abs/2210.11934 — Chứng minh RRF nhạy cảm với tham số và bị suy giảm chất lượng khi gộp cào bằng một bộ truy xuất từ vựng yếu (BM25) với bộ truy xuất ngữ nghĩa mạnh (Dense), trong khi tổ hợp lồi có trọng số (Convex Combination) vượt trội ổn định.
- *Thresholding Classifiers to Maximize F1 Score* (Lipton, Elkan, & Narayanaswamy, ECML PKDD / arXiv) — https://arxiv.org/abs/1402.1892 — Chứng minh điều kiện ngưỡng xác suất biên tối ưu cho họ độ đo $F_\beta$ (với $F_2$, thêm tài liệu còn có lợi chừng nào xác suất đúng biên $> F_2 / (5 - 4F_2) \approx F_2/5$) và sự cần thiết của cắt ngưỡng theo từng truy vấn khi tối ưu macro-$F_\beta$.
- *BAAI/bge-reranker-v2-m3 Official Model Card & Documentation* — https://huggingface.co/BAAI/bge-reranker-v2-m3 — Xác thực thông số mô hình cross-encoder đa ngữ 568M tham số (hỗ trợ tốt tiếng Việt - Trung, chạy nhẹ với `fp16` và ánh xạ điểm chuẩn hóa qua hàm `sigmoid`).
