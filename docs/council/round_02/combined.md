Hội đồng model — round_02 — 2026-10-23 00:36 — 2 vòng

> Các model KHÔNG thấy code, chỉ thấy brief. Đồng thuận là tín hiệu, không phải bằng chứng — kiểm chứng với code/log thật trước khi đưa vào PLAN.

## Thành viên
- M1 = gemini (google/gemini-4-argon) — vai: pragmatist
- M2 = openai (openai/gpt-6-luna) — vai: plan_critic
- M3 = kimi (moonshotai/kimi-k3) — vai: alternative
- M4 = glm (z-ai/glm-5.3) — vai: simplifier

## Bảng xếp hạng đồng thuận (phiếu vòng 2 cho đề xuất vòng 1)

| Hạng | ID | Đề xuất | Của | Điểm | Người bầu |
|---|---|---|---|---|---|
| 1 | M4-A | Xoá tiếng Anh + 3 bài nộp chẩn đoán (VI-only, ZH-only, dò độ sâu N=200) | glm | 8 | M2, M3, M1 |
| 2 | M1-A | Tách rời `N_doc` khỏi `N_chunk` + Phá hạn mức 40 Việt + Gộp điểm có trọng số & Phân bổ `L` bậc thang | gemini | 7 | M4, M2, M3 |
| 3 | M2-C | Thêm vector phần sau cho tài liệu dài | openai | 2 | M1 |
| 4 | M3-A | Chấm điểm tài liệu bằng max-sim cấp chunk trên pool ứng viên (không cần re-index toàn corpus) | kimi | 2 | M4 |
| 5 | M4-B | Dùng lại embedding chunk của bước 5 làm tín hiệu xếp hạng tài liệu (max-sim vào RRF) — không build index mới | glm | 2 | M2 |
| 6 | M1-B | Rerank đa ngữ `BAAI/bge-reranker-v2-m3` trên Top-250 + Định tâm Chunk bằng cửa sổ trượt lai + Cắt ngưỡng động | gemini | 1 | M4 |

## Chi tiết top 5 đề xuất được bầu

**M4-A** (glm)

### Đề xuất A: Xoá tiếng Anh + 3 bài nộp chẩn đoán (VI-only, ZH-only, dò độ sâu N=200)
- **Giả thuyết:** hệ đang đốt quota/lượt truy vấn vào phần vô dụng, và đang thiếu 2 số đo quyết định (đóng góp VI vs ZH, precision biên fused) — inexpensive và quyết định toàn bộ thứ tự ưu tiên còn lại.
- **Bằng chứng trong brief:** nhãn 0 tài liệu Anh; bảng chỉ có precision biên của bm25_vi thuần (0,068 dải 60→100), không có của fused; quota cố định 40/50/10 chưa từng được đo từng phần.
- **Cách làm:** khoá 3 lượt Anh (giữ index trên đĩa làm bảo hiểm). Trên bảng xếp hạng đã cache: (i) nộp VI-only 100 và ZH-only 100 → đọc R doc từng ngôn ngữ → quota ∝ đóng góp biên; (ii) nộp đúng xếp hạng fused như G nhưng N=200 với **L theo thứ hạng** (top-50 nguyên văn ≤4.000, 51–150 → 2.000, 151–200 → 1.000 ký tự; 50×4000+50×2000+100×1000 = 400k ký tự/câu ≈ same byte như G) → precision biên fused dải 111→200 = (T@200−T@111)/89.
- **Thí nghiệm + tiêu chí bác bỏ:** nếu dải biên fused ≥0,10 → độ sâu đáng giá, làm lưới N∈{150,200,250}; nếu ≤0,06 → **khoá độ sâu**, dồn toàn bộ cho Đề xuất C. Nếu R doc(ZH-only) <0,05 → cắt luôn các lượt Trung (bỏ plan dịch Qwen).
- **Kỳ vọng:** +0,01–0,03 trực tiếp (tái phân bổ quota), nhưng thông tin định hướng ≥0,05 | **Tự tin: cao** | **Chi phí: S** (≈0 GPU, chỉ tốn 3 slot nộp trong ~80 slot còn lại).

**M1-A** (gemini)

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

**M2-C** (openai)

### Đề xuất C: Thêm vector phần sau cho tài liệu dài
- Giả thuyết: Vector chỉ từ 2.000 ký tự đầu làm rơi tài liệu đúng có thông tin liên quan ở phần sau; thêm một vector phần sau rồi lấy điểm cao nhất có thể tăng recall trước bước fusion.
- Dựa trên bằng chứng nào trong brief: Tài liệu Việt trung bình 3.553 ký tự nhưng chỉ biểu diễn 2.000 ký tự đầu; BGE-M3 được thiết kế cho nhiều độ hạt và hỗ trợ dense, multi-vector, sparse retrieval: https://arxiv.org/abs/2402.03216
- Cách làm cụ thể: Với tài liệu dài hơn 2.000 ký tự, mã hóa thêm một đoạn ở phần sau; dùng max(head, tail) làm điểm dense cho lượt tiếng Việt, giữ mọi bước còn lại cố định. Đây là thử nghiệm hai vector/tài liệu, chưa cần thay cả hệ bằng index chunk đầy đủ.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Nộp một bản so với nền tốt nhất. Bác bỏ nếu không tăng F2_doc ít nhất 0,01, P doc xuống dưới 0,15, hoặc thời gian mã hóa gây rủi ro cho lịch nộp.
- Kỳ vọng: <+0,005–0,02 điểm tổng | Tự tin: thấp | Chi phí: M

**M3-A** (kimi)

### Đề xuất A: Chấm điểm tài liệu bằng max-sim cấp chunk trên pool ứng viên (không cần re-index toàn corpus)
- Giả thuyết: phần lớn tài liệu đúng bị rơi vì đoạn liên quan nằm sau ký tự 2.000; nếu chấm điểm tài liệu = max cos(query, chunk) trên các chunk 512 token, recall ứng viên tăng mạnh mà không phải encode lại 1,17M tài liệu ở cấp chunk.
- Dựa trên bằng chứng nào trong brief: tài liệu Việt TB 3.553 ký tự nhưng vector chỉ nhìn 2.000 ký tự đầu; F2_chunk/F2_doc đã 0,91 → chọn chunk trong tài liệu đã tốt, nghĩa là embedding cấp chunk của BGE-M3 đủ nhạy, vấn đề nằm ở tầng tài liệu. Bên ngoài: bài báo BGE-M3 cho thấy multi-vector (late interaction kiểu ColBERT) +5,1 điểm so với dense 1-vector trên retrieval tài liệu dài đa ngôn ngữ (MLDR) (https://arxiv.org/html/2402.03216v3); thực nghiệm độc lập cho thấy embed cả tài liệu dài thành 1 vector kém hơn rõ so với embed theo chunk (MRR@1 0,739 vs 0,842) (https://saeedesmaili.com/notes/to-chunk-or-not-to-chunk-with-the-long-context-single-embedding-models/).
- Cách làm cụ thể: lấy hợp top-500 của tất cả lượt hiện có (candidate recall hiện tại), cắt mỗi tài liệu thành chunk 512 token stride 128, encode bằng BGE-M3 (chỉ vài trăm nghìn chunk cho 1.200 câu — vài giờ GPU, không phải 4h×3), điểm tài liệu = max (hoặc trung bình top-2) sim chunk. Thêm lượt "chunkmax_vi" và "chunkmax_zh" vào RRF thay vì chỉ 1 vector/tài liệu. Bonus: chunk argmax cho luôn vị trí mở rộng nguyên văn ở bước chunk → L ngắn hơn vẫn trúng, tiết kiệm byte để tăng N.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nộp 1 bài = pipeline G nhưng thay dense_vi_vi/dense_zh_zh bằng chunkmax, giữ nguyên N và L=4.000. Bác bỏ nếu F2 doc không tăng ≥ +0,02 so với 0,2309. Ước lượng offline trước: đo tỉ lệ tài liệu trong top-500 có argmax-chunk nằm sau ký tự 2.000 — nếu <15% thì giả thuyết yếu, huỷ không tốn lượt nộp.
- Kỳ vọng: +0,03–0,06 tổng | Tự tin: vừa | Chi phí: M

**M4-B** (glm)

### Đề xuất B: Dùng lại embedding chunk của bước 5 làm tín hiệu xếp hạng tài liệu (max-sim vào RRF) — không build index mới
- **Giả thuyết:** vector dense cấp tài liệu chỉ thấy 2.000/3.553 ký tự đầu (≈56% tài liệu) → tài liệu có đoạn đúng ở nửa sau bị tụt hạng; max-sim theo chunk kéo chúng vào tập nộp.
- **Bằng chứng:** BGE-M3 hỗ trợ gốc multi-vector/ColBERT (late interaction) và input tới 8.192 token (không cần model mới); bước 5 đã tính cos chunk—theo—query cho ứng viên → tín hiệu gần như có sẵn, chỉ chưa được dùng để **xếp hạng tài liệu**.
- **Cách làm:** với top-300 fused mỗi câu, score(doc)=max cos(chunk, query) (dùng query cùng ngôn ngữ với doc), gộp RRF vào nhóm Việt/Trung. Cache embedding theo (doc, chunk) một lần (~2–5h GPU cho ~300 ứng viên × 1.200 câu), dùng lại cho mọi bài sau.
- **Thí nghiệm + tiêu chí bác bỏ:** 1 bài nộp giống G, chỉ đổi xếp hạng. Nếu |ΔR doc| < 0,015 (nhiễu LB trên 600 câu ≈ ±0,01) → đóng băng, không thêm lớp nào nữa.
- **Kỳ vọng:** +0,02–0,04 | **Tự tin: vừa** | **Chi phí: S–M**.

### Đ xuất C: Cross-encoder rerank top-200 (bge-reranker-v2-m3 / bản fine-tune tiếng Việt) — rồi mới tới lưới (N, L)
- **Giả thuyết:** T ở N cho trước là toàn bộ trận đấu; cross-encoder dồn tài liệu đúng lên top → cùng ngân sách byte nộp được N≈200 với P≈0,18 như #3.
- **Bằng chứng:** #3 có P doc 0,18 ≈ P của bạn nhưng T≈37 vs T≈19; trên retrieval tiếng Việt, reranker fine-tune từ bge-reranker-v2-m3 đạt acc@1 0,79 vs bi-encoder BGE-M3 0,57 (acc@10: 0,97 vs 0,89) — khoảng cách lớn; BAAI chính thức khuyến nghị cross-encoder để rerank top-k của embedding.
- **Cách làm:** rerank top-200 fused (~240k cặp, max_length 512, chạy đêm trên 5060 Ti ~3–6h, **cache điểm theo (câu, doc)** — chỉ tính lại khi xếp hạng đổi). Nộp top-120 (top-60 nguyên văn, đuôi 1.500) và bản N=200 (đuôi 1.000). **Dùng luôn điểm reranker để chọn vị trí chunk** (rerank top-3 chunk mỗi doc thay cos) — trả lời câu hỏi 2: L ngắn mà vẫn trúng nhờ localise tốt hơn.
- **Thí nghiệm + tiêu chí bác bỏ:** so T@120(reranked) với T@200(fused, từ bài dò ở A). Nếu R doc@120(reranked) ≤ R doc@200(fused) → cross-encoder không chuyển dịch sang y khoa Việt/Trung → khoá, trả lại thời gian cho quota + độ sâu.
- **Kỳ vọng:** +0,03–0,08 (R doc 0,32 → 0,42–0,50) | **Tự tin: vừa–cao** | **Chi phí: M**.

**Thứ tự cho câu hỏi 1:** C > B > (a) độ sâu sau-reranker > (b) trọng số RRF > (f) quota theo câu (A đo hộ) > (e) HyDE (để cùng). **Câu hỏi 2:** có, L theo thứ hạng; vị trí chunk tốt hơn = reranker (Đề xuất C). **Câu hỏi 3 (private):** bài private #1 = cấu hình tốt nhất **đã thắng trên public**, không đưa cấu kiện mới nào vào private; giữ ≥1 slot cho lỗi 413/định dạng (Cloudflare 100MB là ngưỡng cứng, không tăng được từ phía client); giữ G làm phương án an toàn.

## Câu trả lời vòng cuối (vòng 2)

---

# M1 = gemini (google/gemini-4-argon) — vai: pragmatist

## 1. Nhận xét từng thành viên
- **M2**: điểm mạnh là kỷ luật thực nghiệm rất cao (chờ bài H, cô lập từng biến, đo trực tiếp file ZIP nén bzip2 với biên an toàn 10% dưới 95 MB), bác bỏ HyDE có căn cứ (`arXiv:2212.10496` cảnh báo sinh chi tiết sai), và đề xuất **M2-C** thêm đúng 1 vector phần đuôi `max(head, tail)` cho bài Việt dài với chi phí thấp | lỗ hổng là xếp Cross-Encoder Reranker xuống cuối cùng vì cho rằng "reranker không mở rộng pool", bỏ qua thực tế là hợp 8 lượt top-300 tạo ra ~600–1.000 ứng viên/câu nhưng chỉ nộp được 100–200 tài liệu, nên bước lọc từ pool xuống tập nộp chính là nút thắt lớn nhất; đồng thời M2 vẫn mặc định $N_{\text{doc}} = N_{\text{chunk}}$.
- **M3**: điểm mạnh là tư duy kiểm chứng offline miễn phí trước khi tốn lượt nộp (đo tỷ lệ `argmax-chunk` nằm sau ký tự 2.000 ở **M3-A**; đo tỷ lệ bài trùng lặp gần đúng bằng MinHash trên CPU ở **M3-C** — rất sát thực tế corpus 698k trang web y tế Việt tự crawl hay copy bài của nhau) và dẫn nguồn thực nghiệm đa độ hạt của BGE-M3 (`arXiv:2402.03216`) | lỗ hổng là mâu thuẫn nội tại ở **M3-A**: chẩn đoán tài liệu đúng bị rớt khỏi pool ứng viên do vector đầu chỉ nhìn 2.000 ký tự, nhưng giải pháp lại chỉ tính `max-sim chunk` trên *top-500 ứng viên đã truy hồi được* (tài liệu đã rớt khỏi Stage 1 thì không có trong top-500 để cứu); ngoài ra **M3-B** (HyDE) dùng Qwen3-8B sinh 2.400 đoạn y khoa Việt/Trung tốn nhiều giờ GPU nhưng rủi ro ảo giác thuật ngữ cao.
- **M4**: điểm mạnh là phân tích đại số sắc bén về "pha loãng kép" (nếu mỗi tài liệu đều nộp kèm 1 chunk thì tăng $N$ làm loãng cả $F2_{\text{doc}}$ lẫn $F2_{\text{chunk}}$, đẩy ngưỡng precision biên cần thiết lên $0,06–0,07$), thiết kế bài nộp chẩn đoán đo trực tiếp precision biên của danh sách fused (**M4-A**), nhận ra Bước 5 đã tính sẵn `cos(chunk, query)` nên có thể dùng ngay làm tín hiệu xếp hạng tài liệu mà không cần index lại (**M4-B**), và dùng Cross-Encoder (`bge-reranker-v2-m3` / `AITeamVN/Vietnamese_Reranker`) cho cả xếp hạng tài liệu lẫn định tâm chunk (**M4-C**) | lỗ hổng là tốn 1 lượt nộp riêng chỉ cho `ZH-only 100` (không cần thiết khi đã có bài G, H và 1 bài `VI-only 100`), ước lượng thời gian chạy reranker 240k cặp quá bi quan (3–6 giờ, trong khi model 568M chạy `fp16` thực tế chỉ mất ~20–30 phút), và mới chỉ đặt câu hỏi về việc nộp `relevant_chunks` $\subset$ `relevant_docs` ở phần thắc mắc chứ chưa khai thác bằng chứng từ thông số của đội #3 và #4 ($P_{\text{chunk}} > P_{\text{doc}}$).

---

## 2. Tôi đổi quan điểm thế nào (giữ / bỏ / sửa gì, vì sao)
- **Giữ (và được củng cố bởi M4):**
  1. **Tách rời $N_{\text{doc}} > N_{\text{chunk}}$** (`relevant_docs` nộp $180–210$ ID tốn $<1\text{ MB}$, nhưng `relevant_chunks` chỉ nộp cho top $110–120$ tài liệu theo $L$ bậc thang): Phân tích "pha loãng kép" của M4 chứng minh tại sao đây là đòn bẩy số 1. Khi tài liệu hạng 115–200 không nộp kèm chunk, chúng không làm giảm $P_{\text{chunk}}$, giữ ngưỡng có lời của $F2_{\text{doc}}$ ở đúng $F2/5 \approx 0,046$ và giải thích hoàn hảo vì sao đội #3, #4 đều có $P_{\text{chunk}} > P_{\text{doc}}$.
  2. **Danh sách DỪNG NGAY để bảo toàn 8 ngày & 1 GPU 16GB:** (i) Dừng toàn bộ nhánh tiếng Anh (0 nhãn đúng); (ii) Dừng **HyDE / mở rộng câu hỏi bằng Qwen3-8B** (đồng thuận với M2 và M4: tốn GPU, dễ nhiễu thuật ngữ y khoa); (iii) Dừng tăng quota tiếng Trung cố định kiểu bài H; (iv) Kiểm tra ngay diff `relevant_docs` giữa Bài A và Bài G để tìm nguyên nhân $F2_{\text{doc}}$ tụt từ $0,2375$ xuống $0,2309$.
- **Sửa & Tiếp thu từ hội đồng:**
  1. **Tách bước chẩn đoán cô lập trước khi gộp thay đổi (tiếp thu M4-A, M2-A, M3-C):** Ở vòng trước, Đề xuất A của tôi gộp chung đổi quota Việt/Trung + trọng số RRF + tách $N_{\text{doc}}$. Với 80 lượt nộp còn lại, tôi sửa lại theo hướng của M4-A và M2-A: chạy các bài nộp chẩn đoán cô lập (`VI-only 100` và dò độ sâu $N=200$) ngay Ngày 1, đồng thời tích hợp bước lọc trùng lặp gần đúng bằng MinHash trên CPU (**M3-C**) để không đốt slot và byte vào các trang web copy lại bài của nhau.
  2. **Bỏ công thức cửa sổ trượt heuristic, thay bằng tận dụng `max-sim chunk` của Bước 5 + Cross-Encoder định tâm (tiếp thu M4-B, M4-C, M3-A):** Nhận xét của M4-B rất chí lý: Bước 5 của đội đằng nào cũng tính embedding các chunk của ứng viên bằng BGE-M3. Thay vì viết thêm heuristic đếm từ khóa, ta đẩy bước cắt chunk của top-300 ứng viên lên trước để lấy điểm `max-sim chunk` đưa vào RRF (**M4-B / M3-A**), sau đó dùng chính `bge-reranker-v2-m3` (hoặc `AITeamVN/Vietnamese_Reranker` sau khi xác minh phát hành trước 01/08/2026) chấm điểm top-2 chunk tốt nhất của mỗi tài liệu (**M4-C**). Cách này vừa rerank tài liệu, vừa tự động chọn tâm chunk chuẩn xác để thu ngắn $L$ ở phần đuôi.
  3. **Rút gọn `Tail-MaxP` xuống đúng 1 vector đuôi cho bài Việt dài (tiếp thu M2-C):** Thay vì mã hóa thêm 2 đoạn đuôi như đề xuất cũ của tôi, chỉ mã hóa thêm **1 đoạn đuôi duy nhất** (`[1.800 : 3.800]`) cho các bài Việt $>2.000$ ký tự theo **M2-C**. Thời gian GPU giảm một nửa (xuống **~1,2 giờ**), nhưng khắc phục triệt để điểm mù của M3-A/M4-B là cứu được các tài liệu dài bị trượt hoàn toàn khỏi top-300 ban đầu.

---

## 3. Đề xuất cuối (tối đa 3)

### Đề xuất A: Chẩn đoán cô lập Quota Việt/Trung + Khử trùng lặp (Near-Dup) + Tách $N_{\text{doc}} > N_{\text{chunk}}$ với $L$ bậc thang (dựa trên: M4-A, M2-A, M2-B, M3-C)
- **Giả thuyết:**
  1. Nhánh tiếng Anh (0 nhãn đúng) và hạn mức cứng 50–60 tài liệu Trung đang chiếm chỗ của tài liệu Việt hạng 41–150 có precision biên cao hơn nhiều, đồng thời `bm25_vi` yếu ($P@30 = 0,156$) đang kéo tụt `dense_vi_vi` khi gộp RRF đồng trọng số.
  2. Corpus tự crawl 698k trang Việt chứa các bài đăng lại (near-duplicate) giữa các trang tin y tế; lọc bỏ chúng giải phóng cả slot tài liệu lẫn dung lượng JSON.
  3. Tách số lượng `relevant_docs` ($N_{\text{doc}} = 180–200$) lớn hơn `relevant_chunks` ($N_{\text{chunk}} = 110–120$ với $L$ giảm dần theo hạng: $4.000 \rightarrow 2.000$) giúp ăn trọn recall tài liệu ở đuôi mà không gây "pha loãng kép" lên $P_{\text{chunk}}$ và giữ file ZIP bzip2 an toàn ở mức $\le 85\text{ MB}$ (dưới ngưỡng 95 MB 10%).
- **Cách làm cụ thể:**
  1. **Vệ sinh & Khử trùng lặp (CPU, ~30 phút):** Xóa 3 lượt tiếng Anh. Kiểm tra diff giữa Bài A và Bài G để vá lỗi tụt $F2_{\text{doc}}$. Chạy MinHash (shingle 5 từ, ngưỡng Jaccard $\ge 0,80$) trên văn bản sạch của top-300 ứng viên mỗi câu: nếu 2 tài liệu trùng nhau, chỉ giữ bản có điểm cao hơn.
  2. **Tối ưu gộp nhóm Việt & Trung (0 GPU):** Trong nhóm Việt, nâng trọng số `dense_vi_vi` gấp 3 lần `bm25_vi` trong RRF (hoặc z-score combination `0,75 * dense + 0,25 * bm25`).
  3. **Chạy 3 bài nộp chẩn đoán & khai thác trên bảng xếp hạng đã cache (Ngày 1–2):**
     - *Bài A1 (Cô lập tiếng Việt):* Nộp `100 Việt + 0 Trung`, $L = 4.000$ (so sánh trực tiếp với Bài G và Bài H đang chấm để tính chính xác precision biên của Việt từ 40→100 và đóng góp thực của Trung).
     - *Bài A2 (Tái phân bổ Quota + Trọng số Dense):* Đặt hạn mức $N = 100$ theo tỷ lệ đóng góp biên vừa đo được ở A1 vs G/H (dự kiến khoảng `80 Việt + 20 Trung`) + trọng số `dense_vi_vi` $\times 3$ + lọc near-dup, $L = 4.000$.
     - *Bài A3 (Mở độ sâu $N_{\text{doc}} = 190 > N_{\text{chunk}} = 115$ + $L$ bậc thang):* Giữ thứ tự xếp hạng của A2, xuất `relevant_docs` cho top $N_{\text{doc}} = 190$ tài liệu (~150 Việt + 40 Trung), nhưng chỉ xuất `relevant_chunks` cho top $N_{\text{chunk}} = 115$ (hạng 1–50: $L = 4.200$, hạng 51–115: $L = 2.200$, hạng 116–190: không xuất chunk; Trung dùng $L/2$). Bật `separators=(',', ':')` khi ghi JSON và đo kích thước ZIP bzip2 thực tế $< 85\text{ MB}$.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:**
  - *Kiểm tra nội bộ (M3-C):* Nếu tỷ lệ cặp near-dup trong top-100 của 100 câu mẫu $< 3\%$, bỏ bước MinHash.
  - *Trên LB:* Nếu Bài A1 có $F2_{\text{doc}} > 0,245$ (vượt Bài G chỉ bằng tiếng Việt), chứng tỏ quota 50–60 Trung ở G/H đang làm hại $\rightarrow$ khóa tỷ lệ Trung $\le 20\%$. Nếu Bài A3 (tách $N_{\text{doc}} = 190, N_{\text{chunk}} = 115$) làm giảm $F2_{\text{chunk}}$ của A2 (tức hệ thống chấm bắt buộc `relevant_docs` và `relevant_chunks` phải cùng độ dài), chuyển hạng 116–190 sang xuất chunk siêu ngắn $L = 1.000$ ký tự. Ngược lại, nếu $F2_{\text{doc}}$ của A3 tăng $< +0,015$ so với A2 (precision biên dải 101–190 $< 0,05$), lùi $N_{\text{doc}}$ về 140.
- **Kỳ vọng:** `+0,05 đến +0,08` điểm tổng (`0,2207 → 0,27–0,30`) | **Tự tin:** Cao | **Chi phí:** S (~3 giờ code CPU, 0 giờ GPU, 3 lượt nộp trong Ngày 1–2)

---

### Đề xuất B: Tái sử dụng `Max-Sim Chunk` Bước 5 + Cross-Encoder Rerank & Định tâm Chunk trên Top-250 (dựa trên: M4-B, M4-C, M3-A)
- **Giả thuyết:**
  1. Bước 5 hiện tại đã cắt tài liệu ứng viên thành các chunk 1.000 ký tự (Trung 500) và tính `cos(chunk, query)` bằng BGE-M3, nhưng tín hiệu này bị bỏ phí không dùng để xếp hạng tài liệu. Đưa điểm `max_chunk_cos` vào xếp hạng (M4-B, M3-A) sẽ kéo các tài liệu dài có nội dung đúng ở nửa sau (đã lọt vào top-300 nhờ BM25 hoặc câu mở đầu) lên đầu bảng.
  2. Chấm điểm top-2 chunk tốt nhất của mỗi tài liệu trong top-250 ứng viên bằng Cross-Encoder (`BAAI/bge-reranker-v2-m3`, hoặc `AITeamVN/Vietnamese_Reranker` cho nhánh Việt nếu hợp lệ) giúp: (i) tăng mạnh độ chính xác xếp hạng ($T@N$), (ii) quy đổi điểm Việt và Trung về cùng thang logit/sigmoid để **phân bổ Việt/Trung động theo từng câu hỏi** (trả lời câu 1f), và (iii) định tâm mở rộng văn bản chuẩn xác hơn bi-encoder để $L = 2.000$ ở phần đuôi vẫn đạt tỷ lệ trúng LCS cao (trả lời câu 2).
- **Cách làm cụ thể:**
  1. **Đẩy Bước 5 lên trước & Cache `Max-Sim Chunk` (~35 phút GPU):** Với hợp top-250 ứng viên/câu từ Đề xuất A, cắt chunk 800 ký tự (bước trượt 400 ký tự để tránh cắt đôi đoạn tham chiếu $g$; tiếng Trung 400 / bước trượt 200). Mã hóa bằng BGE-M3 (`fp16`), lưu lại điểm `max_cos(d)` và vị trí 2 chunk không chồng lấn có cosine cao nhất của mỗi tài liệu.
  2. **Chạy Cross-Encoder Reranker (~35 phút GPU trên RTX 5060 Ti):**
     - Kiểm tra model card của `AITeamVN/Vietnamese_Reranker` (dựa trên `bge-reranker-v2-m3`, ~568M tham số): nếu xác nhận phát hành trước 01/08/2026 và giấy phép mở thì dùng cho ứng viên Việt, còn `BAAI/bge-reranker-v2-m3` dùng cho toàn bộ (hoặc dùng chung `bge-reranker-v2-m3` cho cả Việt và Trung để đồng nhất thang điểm).
     - Chấm điểm cặp `(query_vi, chunk_top1)` và `(query_vi, chunk_top2)` cho 250 ứng viên $\times$ 1.200 câu (`batch_size=128, fp16, max_length=512`), lấy `rerank_score(d) = max(score_chunk1, score_chunk2)` và lấy chunk thắng làm **tâm mở rộng nguyên văn**. Cache toàn bộ điểm ra đĩa.
  3. **Xếp hạng lai & Phân bổ động:**
     - Điểm cuối: `S_final(q, d) = 0,65 * sigmoid(rerank_score) + 0,20 * norm(max_cos_BGE) + 0,15 * norm(RRF_Stage1)`.
     - Xếp chung cả tài liệu Việt và Trung theo `S_final(q, d)` giảm dần (tự động phân bổ tỷ lệ Việt/Trung theo từng câu hỏi). Xuất $N_{\text{doc}}$ và $N_{\text{chunk}}$ bậc thang tốt nhất từ Đề xuất A.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:**
  - *Kiểm tra offline trước khi nộp (M3-A):* Đo tỷ lệ ứng viên trong top-250 có chunk đạt `max_cos` nằm sau ký tự 2.000.
  - *Bước 1 (1 bài nộp - kiểm chứng M4-B):* Chỉ cộng thêm điểm `max_cos_BGE` vào RRF của Đề xuất A (chưa bật Cross-Encoder) + dùng cửa sổ trượt bước 400. **Tiêu chí bác bỏ:** Nếu điểm tổng không tăng $\ge +0,01$, bỏ thành phần `max_cos_BGE` khỏi công thức gộp.
  - *Bước 2 (2 bài nộp - kiểm chứng M4-C):* Nộp bản đầy đủ có Cross-Encoder Reranker: 1 bài giữ quota Việt/Trung cố định từ A2, và 1 bài gộp chung Việt/Trung theo `S_final` (quota động + cắt ngưỡng động $N_{\text{doc}}(q) \in [90, 230]$ sao cho trung bình bằng 190). **Tiêu chí bác bỏ:** Nếu Reranker không tăng $F2_{\text{doc}}$ thêm $\ge +0,02$ so với Đề xuất A, hoặc làm $P_{\text{doc}} < 0,15$, khóa Reranker và không tinh chỉnh thêm.
- **Kỳ vọng:** `+0,04 đến +0,07` điểm cộng thêm (`→ 0,31–0,36`) | **Tự tin:** Cao | **Chi phí:** M (~1,2 giờ GPU tổng cộng + 3 giờ code, thực hiện Ngày 3–4)

---

### Đề xuất C: Bổ sung đúng 1 Vector phần sau (`Tail-MaxP`) cho tài liệu Việt dài $> 2.000$ ký tự ở tầng truy hồi (dựa trên: M2-C, M3-A)
- **Giả thuyết:**
  - Đề xuất B chỉ cứu được các tài liệu đã lọt vào top-250 ứng viên. Với các bài y khoa Việt dài (trung bình 3.553 ký tự) mà phần trả lời nằm ở nửa cuối (phác đồ điều trị, liều lượng, biến chứng) và không khớp từ khóa chính xác với BM25, việc `dense_vi_vi` chỉ nhìn 2.000 ký tự đầu khiến chúng bị loại ngay từ vòng gửi xe.
  - Mã hóa thêm **đúng 1 đoạn phần sau** (`ký tự 1.800 đến 3.800`) chỉ cho các tài liệu Việt dài $> 2.000$ ký tự rồi lấy `max(cos_head, cos_tail)` (theo **M2-C**) sẽ mở rộng *candidate recall* thực sự với chi phí GPU chỉ bằng ~30% so với index lại toàn bộ corpus.
- **Cách làm cụ thể:**
  1. Lọc trong 698k tài liệu Việt các bài có `len(text) > 2.000` (ước tính ~380k bài). Trích đoạn `tail = text[1800:3800]`.
  2. Mã hóa ~380k đoạn `tail` bằng BGE-M3 (`fp16, max_length=512`, sắp xếp theo độ dài để tối ưu padding) trong **~1,2 giờ GPU** (chạy ban đêm Ngày 4).
  3. Khi truy vấn lượt `dense_vi_vi`, điểm của mỗi tài liệu Việt là `max(cos(q, vec_head), cos(q, vec_tail))`, lấy top-300 tài liệu cao nhất đưa vào pipeline của Đề xuất A + B.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:**
  - *Kiểm tra nội bộ trước khi nộp:* So sánh tập top-250 ứng viên trước và sau khi có `vec_tail` trên 1.200 câu hỏi. **Tiêu chí bác bỏ sớm:** Nếu $< 5\%$ ứng viên trong top-250 thay đổi, hủy ngay không tốn lượt nộp.
  - *Trên LB (1 bài nộp):* Chạy lại pipeline tốt nhất của (A + B) trên tập ứng viên mới có `Tail-MaxP`. **Tiêu chí bác bỏ:** Nếu $R_{\text{doc}}$ tăng $< +0,015$ hoặc điểm tổng tăng $< +0,01$, đóng băng tầng truy hồi, dành toàn bộ thời gian còn lại (Ngày 6–8) để tinh chỉnh lưới $(N_{\text{doc}}, N_{\text{chunk}}, L)$ và chuẩn bị 5 bài Private.
- **Kỳ vọng:** `+0,015 đến +0,03` điểm cộng thêm (`→ 0,33–0,38`) | **Tự tin:** Vừa–Cao | **Chi phí:** M (~1,2 giờ GPU ban đêm + 1,5 giờ code, thực hiện Ngày 5–6)

---

### Tóm tắt Ngân sách Thời gian 8 ngày & Chiến lược 5 bài Private LB (Vai trò Pragmatist)
- **Phân bổ 8 ngày (~15–18 lượt nộp có kiểm soát, chỉ tiêu ~2,5 giờ GPU tổng cộng):**
  - *Ngày 1–2 (0h GPU, 3–4 bài nộp):* Vá lỗi diff A vs G, chạy **Đề xuất A** (bỏ tiếng Anh, lọc near-dup CPU, đo `VI-only 100`, chốt trọng số RRF và tách $N_{\text{doc}} = 190 > N_{\text{chunk}} = 115$ với $L$ bậc thang dưới 85 MB bzip2).
  - *Ngày 3–4 (~1,2h GPU, 3–4 bài nộp):* Chạy **Đề xuất B** (cache `max-sim chunk` + Cross-Encoder `bge-reranker-v2-m3` định tâm chunk & phân bổ động Việt/Trung).
  - *Ngày 5–6 (~1,2h GPU ban đêm, 2–3 bài nộp):* Chạy **Đề xuất C** (`Tail-MaxP` 1 vector đuôi cho bài Việt dài) + quét tinh chỉnh bước nhảy $(N_{\text{doc}}, L)$ sau reranker.
  - *Ngày 7–8 (0h GPU, 2–3 bài nộp):* Kiểm tra an toàn dung lượng bzip2 $< 88\text{ MB}$ cho mọi kịch bản và chốt 5 bài Private (chỉ chọn các cấu hình **đã chứng minh thắng trên Public LB** như M2 và M4 khuyến nghị):
    1. **Bài Private 1 (An toàn tuyệt đối - Bi-encoder + BM25):** Cấu hình tốt nhất của Đề xuất A + C (không dùng Cross-Encoder, dùng quota cố định và $N_{\text{doc}}, N_{\text{chunk}}$ cố định).
    2. **Bài Private 2 (Chủ lực ổn định - Reranker + Quota cố định):** Đề xuất A + B + C với $N_{\text{doc}} = 190, N_{\text{chunk}} = 115$ và tỷ lệ Việt/Trung khóa cố định (phòng rủi ro lệch phân phối điểm sigmoid trên tập Private).
    3. **Bài Private 3 (Điểm Public cao nhất - Reranker + Phân bổ động):** Đề xuất A + B + C gộp chung Việt/Trung theo điểm `S_final` và định tâm chunk bằng reranker.
    4. **Bài Private 4 (Phòng hộ Recall cao):** Giống Bài 2 hoặc 3 nhưng đẩy $N_{\text{doc}} = 230$ (chỉ tăng danh sách `doc_id`, giữ nguyên `relevant_chunks` để không tốn thêm byte) phòng trường hợp 600 câu Private có số nhãn đúng trung bình $> 60$.
    5. **Bài Private 5 (Ensemble thứ hạng):** Gộp RRF giữa bảng xếp hạng của Bài 1 (Stage-1 `Tail-MaxP` + `max-sim chunk`) và Bài 3 (Cross-Encoder Reranker).

## 4. Bình chọn
VOTES: M4-C, M4-A, M2-C

---

# M2 = openai (openai/gpt-6-luna) — vai: plan_critic

## 1. Nhận xét từng thành viên
- M1: Điểm mạnh là phát hiện sai khác A–G và nêu khả năng tách số tài liệu khỏi số chunk. | Lỗ hổng là suy ra số tài liệu đúng của từng ngôn ngữ từ precision tổng hợp, rồi đề xuất quota, trọng số và lịch chunk cụ thể chưa có kiểm chứng; nhiều thay đổi bị gộp trong cùng một bài. Trích dẫn về RRF không chứng minh cấu hình trọng số được đề xuất sẽ tốt hơn ở bài này.
- M2: Điểm mạnh là cảnh báo precision biên BM25 không đại diện cho precision biên của xếp hạng đã fusion, và yêu cầu đo kích thước file nén thật. | Lỗ hổng là đặt trọng số RRF trước các bước kiểm tra tính tái lập và độc lập giữa `relevant_docs`/`relevant_chunks`; đề xuất trước đây cũng chưa đưa ra phép thử trực tiếp cho chênh lệch A–G.
- M3: Điểm mạnh là chỉ ra reranker không thể cứu tài liệu ngoài candidate pool và chú ý điểm mù do chỉ mã hóa phần đầu tài liệu. | Lỗ hổng là phép thử trên top-500 chỉ cải thiện thứ tự trong pool, không chứng minh recall toàn corpus tăng; chi phí mã hóa và lợi ích dự kiến chưa được đo. BGE-M3 paper liên quan tới multi-vector, nhưng không đảm bảo mức tăng tương tự trên corpus này.
- M4: Điểm mạnh là đòi đo precision biên của danh sách fused trước khi quyết định tăng N, và tận dụng điểm chunk có thể đã tính sẵn. | Lỗ hổng là suy ra N từ P/R tổng hợp và giả định số nhãn trung bình trong công thức macro có thể gây sai; bài dò N=200 đồng thời đổi L cũng làm khó kết luận. Kết quả reranker tiếng Việt được trích dẫn là benchmark khác, chưa chứng minh lợi ích trên tác vụ này và cần xác minh điều kiện dùng.

## 2. Tôi đổi quan điểm thế nào (giữ / bỏ / sửa gì, vì sao)
Tôi giữ ý “đợi H và kiểm dung lượng thật” từ câu trả lời trước, nhưng đổi thứ tự: trước cả thử nghiệm mới, phải xác minh A–G có cùng danh sách tài liệu hay không. Nếu baseline không tái lập, so sánh LB sau đó không đáng tin. Tôi cũng sửa đề xuất tăng N: chỉ thử trên thứ hạng cố định và tách rõ danh sách tài liệu khỏi danh sách chunk nếu định dạng cho phép. Chưa ưu tiên reranker hay HyDE; reranker bị giới hạn bởi candidate pool, còn HyDE thêm nhiễu mà hiện chưa có kiểm chứng.

**Thứ tự ưu tiên sửa đổi (5 hướng; kiểm tra tính hợp lệ là bước chặn trước):**
1. **(f) Phân bổ Việt/Trung:** chờ H trước; dùng kết quả để tránh tốn bài thử quota đã gần được trả lời.
2. **(a) Tăng N:** thử với thứ hạng giữ nguyên, đồng thời giới hạn riêng số chunk để kiểm ngân sách byte.
3. **(b) Trọng số RRF:** thử một thay đổi trọng số đơn lẻ; rẻ hơn reranker nhưng chưa có bằng chứng về precision biên sau fusion.
4. **(d) Dense cấp chunk/max-sim:** ưu tiên sau các phép thử rẻ; có thể xử lý tài liệu bị điểm mù ở phần sau.
5. **(c) Reranker:** chỉ sau khi candidate pool và cách xếp hạng đã ổn định; reranker không khôi phục tài liệu không lọt vào pool. **(e) HyDE** tạm hoãn vì lợi ích chưa được chứng minh trong khi đã có các lượt truy vấn dịch.

## 3. Đề xuất cuối (tối đa 3)
### Đề xuất A: Khóa baseline trước khi tiêu lượt nộp
- **Giả thuyết:** Chênh lệch A–G có thể do đầu vào hoặc danh sách tài liệu thay đổi, khiến kết luận về L và các cải tiến sau bị nhiễu.
- **Cách làm cụ thể:** So sánh trực tiếp `relevant_docs` của A và G theo từng câu; ghi lại bản dịch, seed/cấu hình, thứ tự tie-break và hash đầu vào. Chạy lại cùng cấu hình hai lần. Kiểm tra H và đo kích thước chính xác của ZIP bzip2 trước khi nộp.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** Nếu hai lần dựng cùng cấu hình cho danh sách giống hệt nhau, A–G khác nhau chỉ ở chunk như dự kiến, và file nén nằm dưới ngưỡng an toàn, bác bỏ giả thuyết lỗi tái lập; nếu không, chưa dùng các so sánh LB để chọn pipeline.
- **Kỳ vọng:** +0 trực tiếp; tránh tối ưu nhầm baseline | Tự tin: cao | Chi phí: S

### Đề xuất B: Tách số tài liệu và số chunk trong phép thử tăng N
- **Giả thuyết:** Có thể tăng F2_doc bằng cách lấy thêm tài liệu trong khi giữ số chunk và dung lượng chunk gần như cố định. **Giả định:** định dạng/chấm điểm cho phép `relevant_chunks` là tập con của `relevant_docs`.
- **Cách làm cụ thể:** Xác minh giả định từ schema/hướng dẫn chấm; giữ nguyên xếp hạng tốt nhất, so sánh N_doc=100 với N_doc=150, còn N_chunk và quy tắc L giữ cố định. Nén file hoàn chỉnh và để dư biên dưới giới hạn 95 MB.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** Nộp một biến thể chỉ đổi N_doc. Bác bỏ nếu F2_doc không tăng ít nhất 0,01, P_doc xuống dưới 0,15, điểm tổng không tăng, hoặc file vượt ngưỡng. Nếu schema không cho tách hai danh sách, dừng hướng này thay vì suy đoán.
- **Kỳ vọng:** +0,01–0,03 điểm tổng, chưa chắc | Tự tin: vừa | Chi phí: S

### Đề xuất C: Dùng điểm chunk sẵn có để xếp hạng tài liệu trước cross-encoder
- **Giả thuyết:** Nếu bước chọn chunk hiện đã tính similarity cho các chunk của tài liệu ứng viên, lấy điểm tốt nhất theo tài liệu có thể cải thiện thứ tự trong pool với chi phí thấp hơn xây index chunk toàn corpus.
- **Cách làm cụ thể:** **Giả định:** điểm similarity theo chunk có thể lấy lại mà không mã hóa lại. Trên cùng candidate pool, N, quota ngôn ngữ và L, thay riêng điểm xếp hạng tài liệu bằng max-sim chunk; chỉ xem xét cross-encoder sau khi phép thử này cho thấy lợi ích.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** So với cùng baseline trên LB. Bác bỏ nếu điểm tổng tăng dưới 0,01 hoặc P_doc dưới 0,15; khi đó không đầu tư mã hóa/index chunk toàn corpus chỉ dựa trên lập luận tài liệu dài.
- **Kỳ vọng:** +0–0,02 điểm tổng | Tự tin: thấp–vừa | Chi phí: S nếu điểm đã cache; nếu phải mã hóa lại thì M

## 4. Bình chọn
VOTES: M4-A, M4-B, M1-A

---

# M3 = kimi (moonshotai/kimi-k3) — vai: alternative

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

---

# M4 = glm (z-ai/glm-5.3) — vai: simplifier

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

---

_Câu trả lời các vòng trước: thư mục r1/_

_Nguồn tra cứu: 46 link từ 0 lượt search — xem sources.md_
