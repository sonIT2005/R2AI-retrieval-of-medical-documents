# M1 = gemini (google/gemini-4-argon) — vai: pragmatist — vòng 2

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
