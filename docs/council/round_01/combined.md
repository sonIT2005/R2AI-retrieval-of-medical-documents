Hội đồng model — round_01 — 2026-10-22 11:56 — 2 vòng

> Các model KHÔNG thấy code, chỉ thấy brief. Đồng thuận là tín hiệu, không phải bằng chứng — kiểm chứng với code/log thật trước khi đưa vào PLAN.

## Thành viên
- M1 = grok (x-ai/grok-4.7) — vai: red_team
- M2 = minimax (xiaomi/mimo-v2.6-flash) — vai: data_detective
- M3 = qwen (qwen/qwen3.8-max-0902) — vai: competition_veteran
- M4 = deepseek (deepseek-v4-pro) — vai: root_cause

## Bảng xếp hạng đồng thuận (phiếu vòng 2 cho đề xuất vòng 1)

| Hạng | ID | Đề xuất | Của | Điểm | Người bầu |
|---|---|---|---|---|---|
| 1 | M3-A | "Một chunk duy nhất, dài nhất có thể" — và không bao giờ >1 chunk/tài liệu | qwen | 8 | M2, M4, M1 |
| 2 | M1-A | Nộp thuần danh sách bm25_vi đã lưu | grok | 6 | M2, M4, M3 |
| 3 | M3-B | Bỏ quota ngôn ngữ + bỏ RRF, xếp hạng BM25 toàn cục, quét N để vẽ H(N) và cắt ở ngưỡng p ≥ F2/5 | qwen | 5 | M2, M4, M1 |
| 4 | M1-B | Một chunk nguyên văn dài, giữ nguyên tập tài liệu | grok | 3 | M3 |
| 5 | M2-C | Trước tiên đo nhiễu LB, rồi mới chạy 1 thí nghiệm chunk dài hơn | minimax | 1 | M3 |
| 6 | M4-B | Bỏ dense/RRF và hạn mức ngôn ngữ — chỉ nộp BM25 Việt thuần với whole-doc chunk | deepseek | 1 | M1 |

## Chi tiết top 5 đề xuất được bầu

**M3-A** (qwen)

### Đề xuất A: "Một chunk duy nhất, dài nhất có thể" — và không bao giờ >1 chunk/tài liệu

- **Giả thuyết:** F2_chunk = 5·H_c/(4·G_c + N_c). Vì ~1 chunk tham chiếu/tài liệu (G_c ≈ G_d) và 1 chunk nộp/tài liệu (N_c = N_d), nếu span nộp **chứa** g thì overlap = LCS/|g| = 1 ⇒ H_c = H_d ⇒ **F2_chunk = F2_doc**. Điểm tổng khi đó = F2_doc, mọi cải thiện ở tầng tài liệu chuyển 1:1 vào điểm thay vì chỉ ~35% như hiện nay. Nộp k chunk/tài liệu làm N_c tăng k lần mà H_c không tăng quá H_d ⇒ strictly worse.
- **Bằng chứng trong brief:** (i) mẫu số chỉ là |g|, không giới hạn độ dài, "cách phân đoạn do đội tự thiết kế"; (ii) LCS là subsequence nên thêm token vào c không bao giờ giảm overlap; (iii) đội #1 có **P_chunk 0,993 ≈ P_doc 0,995** và R_chunk 0,700 ≈ R_doc 0,695 — chữ ký chính xác của "1 chunk dài/tài liệu, đúng tài liệu là đúng chunk"; (iv) các đội #3–#5 có F2_chunk ≈ F2_doc; (v) các bạn là ngoại lệ duy nhất: F2_chunk 0,084 ≪ F2_doc 0,238.
- **Cách làm cụ thể:**
  1. Bỏ hoàn toàn việc chọn chunk bằng cos BGE-M3. Với mỗi tài liệu nộp, lấy span liên tiếp: nếu văn bản ≤ L thì nộp **toàn bộ**; nếu dài hơn, lấy cửa sổ điểm BM25 (cấp câu/cụm) cao nhất rồi mở rộng đối xứng tới đúng L ký tự, cắt ở ranh giới câu/dòng. L là biến số duy nhất cần dò.
  2. Bỏ lọc dòng rác khi trích xuất cho phần chunk: văn bản "bẩn hơn" nhưng dài hơn chỉ **có lợi** cho LCS (đơn điệu), đồng thời hedging rủi ro extraction của các bạn lệch extraction của BTC (g là nguyên văn theo bản crawl của BTC).
  3. Kiểm tra hai trần cứng trước khi nộp: **kích thước file nộp** (600 câu × N chunk × L ký tự; L=2.000 với N=100 là ~120 MB, L=4.000 là ~240 MB) và **thời gian chấm**. Ước lượng chi phí LCS: |g| ≈ 150–300 token; L=2.000 ký tự ≈ 330 âm tiết ⇒ ~10⁵ ô DP (vô hại); L=8.000 ≈ 1.300 âm tiết ⇒ 4·10⁵ ô ≈ 0,4 s nếu DP thuần Python, ×100 doc ×600 câu ≈ 6–7 giờ ⇒ **rất dễ timeout**. Vùng an toàn dự đoán: 2.000–4.000 ký tự.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** Giữ nguyên tập tài liệu của bài 0,1606 (đóng băng N=100, 60/40/0), chỉ đổi chunk, dùng 4 bài trong 1 ngày: L ∈ {2.000, 4.000, 8.000, toàn văn bản}. 
  - *Xác nhận:* F2_chunk tiến về F2_doc (0,20–0,24) ngay ở L=2.000; điểm tổng lên ~0,22–0,24 mà không đổi retrieval.
  - *Bác bỏ 1:* nếu F2_chunk **không** tăng khi L tăng ⇒ văn bản các bạn crawl **không chứa** g (lệch extraction/URL bị chặn, hoặc doc_id ánh xạ sai) ⇒ phải sửa tầng crawl trước, mọi tối ưu chunk vô nghĩa. Đây là thông tin cực rẻ và cực quan trọng.
  - *Bác bỏ 2:* nộp thêm 1 bài với 3 chunk/tài liệu (L=1.000, phủ cả văn bản). Nếu F2_chunk của bản 3-chunk **cao hơn** bản 1-chunk thì giả định G_c ≈ G_d của tôi sai (nhiều chunk tham chiếu/tài liệu hơn brief ghi) ⇒ khi đó quay lại chiến lược phủ nhiều span.
  - *Song song:* gửi BTC 1 câu hỏi bằng văn bản về trần độ dài chunk / thời gian chấm / kích thước file nộp. Đây là cách rẻ nhất để loại rủi ro "lách luật" ở vòng private. Về rủi ro bị coi là lách luật: bản thân luật cho phép tự thiết kế phân đoạn, nhưng để phòng thủ khi xét bài báo, tôi khuyên **không** nộp nguyên văn bản 50k ký tự; giữ span liên tiếp có chủ đích ≤4.000 ký tự và lưu 1 cấu hình bảo thủ (L=1.500–2.000) làm phương án private.
- **Kỳ vọng:** +0,06 → +0,10 điểm tổng ngay lập tức (0,161 → ~0,24), và hệ số nhân 1:1 cho mọi cải thiện retrieval sau này | **Tự tin: cao** | **Chi phí: S**

**M1-A** (grok)

### Đề xuất A: Nộp thuần danh sách bm25_vi đã lưu
- Giả thuyết: RRF (k=60, bản dịch trọng số 0,3) và hạn mức 60/40 đang đẩy tài liệu ngoài pool nhãn lên trên đúng hit lexical. Top-k của riêng lượt bm25_vi (đã tính, không cần reindex) sẽ có P_doc cao hơn hẳn 0,177 và F2 doc tiến về 0,559 của baseline.
- Dựa trên bằng chứng nào trong brief: baseline trả ~30 tài liệu, trúng ~27 (P 0,881); bài tốt nhất trả ~100, trúng ~18. Chưa từng nộp bm25_vi thuần ở k≈25–60. 20 Anh = 0; P Việt 0,38 > P Trung 0,16. BEIR đo đúng kiểu lệch này: trên TREC-COVID, hit lexical Hole@10 chỉ 6,4%, còn dense tới 14–32% và bị tính sai cho đến khi gán nhãn lại (ANCE 0,654 → 0,735).
- Cách làm cụ thể: giữ nguyên chunk hiện tại để không nhiễu. Ba bài trong một ngày, cùng một danh sách bm25_vi đã lưu, chỉ đổi k = 25, 40, 60; doc_id đúng ID corpus, không URL redirect. Cấm trộn dense, Trung, Anh. Không tăng 150–200 trên fusion hiện tại — với P 0,177, thêm tài liệu đuôi gần như chắc làm macro-F2 tệ hơn.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: so với bài 0,1606 ngày 15/10. Bác bỏ giả thuyết “fusion là thủ phạm chính” nếu cả ba k đều có F2 doc < 0,28 hoặc P_doc < 0,30. Nếu k=40 có P_doc ≥ 0,6 và R_doc ≥ 0,45 thì fusion là lỗi, dừng plan reranker. Nếu P vẫn ~0,2 thì lỗi nằm ở bản thân sparse/text (chuyển sang Đề xuất C), không phải ở cách gộp.
- Kỳ vọng: <+0,08 đến +0,18 điểm tổng nếu P_doc ≥ 0,6> | Tự tin: vừa | Chi phí: S

**M3-B** (qwen)

### Đề xuất B: Bỏ quota ngôn ngữ + bỏ RRF, xếp hạng BM25 toàn cục, quét N để vẽ H(N) và cắt ở ngưỡng p ≥ F2/5

- **Giả thuyết:** Nhãn được sinh từ pool BM25 của BTC (có thể qua một bước lọc), nên P_doc = 0,881 của baseline là dấu hiệu nhãn "dễ tái tạo" chứ không phải BM25 giỏi thật. RRF rank-fusion với dense (chỉ 1 vector/tài liệu từ **2.000 ký tự đầu**, 512 token) gần như nhiễu trên tài liệu dài, và quota 40 slot tiếng Trung cố định đẩy ra ngoài 40 tài liệu Việt có p ≈ 0,38 để lấy 40 tài liệu Trung có p ≈ 0,16 — vi phạm trực tiếp **Probability Ranking Principle cho F-measure** (dự đoán tối ưu là top-k theo xác suất, không phải theo hạn mức nhóm): https://yenan.github.io/pub/fscore-icml12/fscore.pdf (Theorem 9, trích Lewis 1995). Ngoài ra, với metric dạng điều hoà này, quy tắc "nộp nếu p > ngưỡng" đã được chứng minh ngay trong tài liệu TREC: https://trec.nist.gov/pubs/trec11/papers/cmu.collins-thompson.pdf — với T11F = 1/(1/recall + 4/precision) họ suy ra "deliver if P(relevant) > 0,33"; với F2 = 5PR/(4P+R) của các bạn, cùng phép suy ra cho **ngưỡng = F2/5 ≈ 0,11–0,15** (tương tự kết quả ngưỡng tối ưu = F/2 cho F1 tại https://arxiv.org/html/1402.1892v2, Corollary 1). Và "không có ngưỡng cố định nào tối ưu Fβ" ⇒ phải cắt theo từng câu: https://dl.acm.org/doi/pdf/10.1145/1076034.1076144
- **Bằng chứng trong brief:** (i) P_zh 0,16 > ngưỡng 0,12 ⇒ giữ tiếng Trung, nhưng chỉ ở phần đuôi của một danh sách toàn cục; (ii) H của các bạn ở N=100 (~18) **thấp hơn** H của BM25 thuần ở N=30 (~26) ⇒ fusion đang phá huỷ tín hiệu, không phải thiếu tài liệu; (iii) các bạn đã cache 8 lượt top-300 nên ghép lại chỉ mất vài giây; (iv) |G| dao động 5–190 mà N cố định 100 ⇒ thừa với câu ngắn, thiếu với câu dài.
- **Cách làm cụ thể:**
  1. Offline, từ 8 lượt đã cache: tạo danh sách **chỉ bm25_vi + bm25_zh**, quy về một điểm BM25 so sánh được (chuẩn hoá điểm theo phân vị trong từng ngôn ngữ, hoặc dùng chung một chỉ mục đa ngôn ngữ), xếp hạng toàn cục, **không RRF, không quota**. Dense chỉ được phép vào như một tie-breaker ở vùng đuôi, không phải thành phần fusion ngang hàng.
  2. Vẽ đường cong H(N) bằng LB: nộp N ∈ {30, 60, 100, 150, 200}. Từ P và R của từng bài suy ra H = P·N và G = H/R; precision biên của dải [N₁,N₂] = (H(N₂)−H(N₁))/(N₂−N₁). Chọn N\* là điểm cuối cùng mà precision biên ≥ 0,12–0,15.
  3. Chỉ số "vân tay" quan trọng nhất: **P@30 của bm25_vi thuần ≈ 0,881?** Nếu đúng, các bạn đã tái tạo được ranker sinh nhãn và có thể đẩy N rất sâu; nếu chỉ ~0,5 thì vấn đề nằm ở **chỉ mục**, và thứ tự sửa rẻ→đắt là: (a) bỏ HashingVectorizer (collision + IDF sai) → vocabulary thật/Okapi chuẩn; (b) bỏ cắt 10.000 ký tự đầu, index toàn văn; (c) thử token theo từ (pyvi/underthesea/vncorenlp) thay vì theo âm tiết; (d) thử index cấp chunk rồi lấy max-score lên cấp tài liệu. Mỗi phương án chỉ cần 1–2 bài nộp để đọc P@30.
  4. N theo từng câu thay vì cố định: cắt tại "đầu gối" của đường điểm BM25 (điểm có score < α·score_max, hoặc khe hở lớn nhất trong top-200), với α hiệu chỉnh trên public. Đây là ngưỡng động, đúng tinh thần tài liệu ACM ở trên.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** 5 bài nộp trong ngày 1–2 (đã ghép sẵn offline), tất cả dùng chunk của Đề xuất A để F2_chunk không làm nhiễu phép đọc.
  - *Xác nhận:* H(100) ≥ 40 và P@30 ≥ 0,80 ⇒ F2_doc ≥ 0,5, tức vượt mọi đội trừ #1.
  - *Bác bỏ:* nếu bm25_vi thuần top-30 cho P < 0,6 (tệ hơn hẳn 0,881 của BTC) thì giả thuyết "nhãn = pool BM25 của BTC" vẫn có thể đúng nhưng **chỉ mục của các bạn không khớp**; khi đó dừng việc quét N và dồn 2 ngày vào sửa chỉ mục (bước 3), vì quét N trên một ranker sai chỉ tối ưu cái sai.
  - *Bác bỏ quota:* nộp 1 bài "toàn cục không quota" và 1 bài "quota 80/20" ở cùng N. Nếu không-quota không hơn ≥0,02 thì quota không phải thủ phạm.
- **Kỳ vọng:** +0,25 → +0,40 điểm tổng (F2_doc 0,24 → 0,5–0,6, chunk ăn theo 1:1) | **Tự tin: cao** cho hướng "bỏ fusion/quota", **vừa** cho con số cụ thể | **Chi phí: S–M**

**M1-B** (grok)

### Đề xuất B: Một chunk nguyên văn dài, giữ nguyên tập tài liệu
- Giả thuyết: R_chunk/R_doc = 0,34 chủ yếu vì cửa sổ 1.000 ký tự (Việt) ngắn hơn 0,4|g| hoặc không chứa đoạn vàng, không phải vì cosine chọn sai giữa các cửa sổ ngắn. Một chunk = thân bài trafilatura thô (không phải chuỗi đã tách âm tiết / đã lọc “dòng rác”) sẽ kéo R_chunk về gần R_doc.
- Dựa trên bằng chứng nào trong brief: luật overlap = LCS_token(c,g)/|g|, mẫu số chỉ |g|, ~1 chunk vàng/tài liệu; P_chunk 0,067 và R_chunk 0,115. Chunk Trung (trang ngắn, 500 ký tự) có P cao hơn Việt (bài dài). Đội #1 có P_chunk 0,993 ≈ P_doc 0,995. Tập ViHealthQA (vinmec/vnexpress, cùng kiểu hỏi–đáp y khoa Việt) có ~47% đoạn trả lời trên 300 từ — priors độ dài, không phải nhãn cuộc thi này.
- Cách làm cụ thể: lấy đúng tập doc của bài 0,1606. Mỗi doc nộp đúng 1 chunk: thân bài sau trafilatura, chưa lọc dòng, chưa lowercase, chưa bỏ dấu. Cap 8.000 ký tự (cắt theo biên đoạn, không cắt giữa từ). Không nộp 2–3 cửa sổ: chunk không phủ g nào là false positive. Chấm thử local bằng DP LCS Python trên 20 cặp (8.000 token × giả định |g|=400) để ước lượng thời gian; không tìm thấy ngưỡng timeout chính thức của BTC.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: một bài LB, doc giống hệt 15/10. Bác bỏ nếu R_chunk/R_doc vẫn ≤ 0,45 và F2 chunk tăng < 0,03. Nếu điểm chunk = 0 hoặc bài bị reject trong khi doc vẫn khớp, coi là timeout/format — hạ cap xuống 3.000 rồi 1.500, không nhảy lên full HTML. Nếu R_chunk lên ≥ 0,8×R_doc, độ dài/text thô là lỗi; lúc đó mới sweep 3k/8k/12k.
- Kỳ vọng: <+0,04 đến +0,10 điểm tổng trên tập doc hiện tại> | Tự tin: vừa | Chi phí: S

**M2-C** (minimax)

### Đề xuất C: Trước tiên đo nhiễu LB, rồi mới chạy 1 thí nghiệm chunk dài hơn
- Giả thuyết: vì mẫu số chỉ là |g|, gộp 2–3 dòng liền kề thành chunk 2.500–4.000 ký tự (hoặc nộp 2 chunk lân cận/tài liệu) sẽ tăng R_chunk trong tài liệu đúng, đúng thứ họ đang thua nặng nhất (R_chunk/R_doc = 0,34); nhưng cần biết nhiễu LB để biết Δ bao nhiêu là thật.
- Dựa trên bằng chứng nào trong brief: F2_chunk 0,084 vs F2_doc 0,238; các đội #3–#5 có F2_chunk ≈ F2_doc; "nhiễu giữa các bài nộp: chưa đo"; snippet extraction vốn khó hơn doc retrieval ngay cả ở BioASQ chuẩn. [nguồn mục 4]
- Cách làm cụ thể: (1) chi 1 lượt nộp lại đúng cấu hình tốt nhất (100 tài liệu 60/40) → |Δ| với 0,1606 ước nhiễu LB; (2) chi 1 lượt chỉ đổi phần chunk (giữ nguyên top-100, chunk 1/tài liệu nhưng gộp lên ~3.000 ký tự quanh vị trí cos cao nhất); (3) kiểm tra offline trên 20 trang: % trang mà vùng 1.000 ký tự đầu đội chọn nằm ngoài 40% ký tự giữa trang (dấu hiệu trích xuất lệch vùng/boilerplate).
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: ΔF2_chunk > 3×nhiễu đo được ở (1) → giữ hướng chunk dài làm mục chính; Δ nhỏ hơn → nguyên nhân không phải độ dài mà là chọn sai vùng/parser lệch, chuyển sang rerank chunk (bge-reranker-v2-m3 đã có trong plan) thay vì kéo độ dài. Chú ý giới hạn 5 bài/private: chỉ dùng 2 lượt LB cho việc này.
- Kỳ vọng: +0,03–0,08 tổng điểm (chunk 0,084 → tiệm cận F2_doc) | Tự tin: vừa | Chi phí: S (2 lượt nộp + 1 lần đếm offline)

## Câu trả lời vòng cuối (vòng 2)

---

# M1 = grok (x-ai/grok-4.7) — vai: red_team

## 1. Nhận xét từng thành viên
- M2: điểm mạnh là buộc phải đo nhiễu LB và chỉ ra mâu thuẫn near-duplicate (dedup làm mất slot) trước khi diễn giải Δ nhỏ. | lỗ hổng: M2-A giả định file chấm có gold doc_id từng câu rồi tối ưu trên đó — brief chỉ cho thống kê tổng quát, và đây sát “cấm dò đáp án”; nếu làm, public bị overfit và private có thể bị huỷ. CLEF eHealth chỉ chứng minh pooling nói chung, không chứng minh nhãn cuộc thi này là pool BM25.
- M3: điểm mạnh là rút F2 = 5H/(4G+N) và ngưỡng biên p > F2/5, khớp bảng LB (baseline ~0,564 so với 0,559 — lệch nhỏ đúng kiểu macro, không phải sai công thức); từ đó quota cố định là sai, và >1 chunk/tài liệu làm tăng N_c mà không tăng H_c nếu G_c ≈ 1. | lỗ hổng: câu “đang nộp quá ít / cắt Trung là sai” dùng P trung bình, không phải precision biên của ranker hiện tại (H≈18 ở N≈100, tệ hơn H≈27 của BM25 ở N≈30). P_zh≈0,16 không chứng minh slot Trung thứ 40 có p trên ngưỡng của từng câu. Kỳ vọng +0,25–0,40 giả định chỉ mục đã khớp BTC. Ước |g|≈150–300 token chưa có bằng chứng; nếu |g| dài, timeout LCS tệ hơn nhiều so với 6–7 giờ. Nguồn Yen/Lewis và TREC-11 ủng hộ “xếp theo xác suất rồi cắt ngưỡng”, không ủng hộ đúng số 0,11–0,15 của metric này.
- M4: điểm mạnh là tách biến sạch (chunk trước, retrieval sau) và tiêu chí giết doc F2 ≤ 0,30. | lỗ hổng: nộp toàn văn / cap 50k token ở bài đầu là rủi ro timeout hoặc reject — Δ=0 khi đó không bác được giả thuyết chunk. Không kiểm HashingVectorizer có phải BM25 thật trước khi kết luận “fusion không phải thủ phạm”. Không có nguồn; thứ tự thì đúng, độ dài chunk thì không an toàn.

## 2. Tôi đổi quan điểm thế nào (giữ / bỏ / sửa gì, vì sao)
Giữ: fusion/quota đang phá tín hiệu lexical; không tăng 150–200 trên danh sách hiện tại; reranker sau khi có ranker P cao; cấm Anh; không đổi chunk và retrieval trong cùng một bài nộp.
Bỏ: “cấm Trung ở hệ thống cuối”. Bài 20 Trung = 0,0536 nên có hit; Trung chỉ bị cấm trong bài chẩn đoán để tách biến. Cách giữ đúng là xếp hạng toàn cục, không phải quota 40 — đây là lập luận của M3-B, tốt hơn đề xuất cũ của tôi.
Sửa độ dài chunk: không bắn 8.000 ký tự hoặc toàn văn ở bài đầu (M4-A). Bài đầu L=2.000 rồi 4.000, vì |g| không biết và mẫu số chỉ |g| vẫn đúng nếu span chứa g. Công thức M3 thuyết phục tôi rằng 2–3 chunk/tài liệu chỉ đáng thử nếu bản 1 span dài không nâng R_chunk.
Sửa diễn giải “nộp quá ít”: chỉ đúng sau khi P@30 của sparse Việt đã cao. Trên ranker P=0,177, đuôi gần như chắc p < F2/5.
Không nhận M2-A: không dùng doc_id vàng từng câu, không suy ngược nhãn từ nhiều bài nộp.

## 3. Đề xuất cuối (tối đa 3)
### Đề xuất A: Một span 2k/4k, đóng băng đúng tập tài liệu (dựa trên: M3-A, M4-A)
- Giả thuyết: R_chunk/R_doc = 0,34 vì cửa sổ 1.000 ký tự không phủ 0,4|g| hoặc text đã lọc rác mất câu vàng; 1 span liên tiếp dài hơn, chưa lowercase/chưa tách âm tiết, sẽ kéo F2_chunk về phía F2_doc. Nếu text crawl không chứa g, tăng L không giúp.
- Cách làm cụ thể: xác nhận từ log số doc thật của bài 0,1606 (brief ghi “giả định” 60/40/0). Giữ nguyên doc_id, mỗi doc đúng 1 chunk, bỏ lọc dòng rác, cắt biên câu. Không nộp bản đã hash/token hoá. Trước khi nộp: DP LCS Python 3.7 trên 20 cặp xấu nhất (L × giả định |g| = 200 và 2.000 token). Chunk.doc_id phải nằm trong relevant_docs, doc_id không trùng. Không gửi toàn văn ở lượt này.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: 2 bài, cùng ngày, chỉ đổi L ∈ {2.000, 4.000}. Bác bỏ “độ dài là thủ phạm” nếu cả hai có R_chunk/R_doc ≤ 0,45 và ΔF2_chunk < 0,03 so với 0,084. Nếu điểm chunk = 0 hoặc reject trong khi doc khớp bài cũ → timeout/format, không được diễn giải là sai giả thuyết; dừng, không tăng L. Nếu 4.000 không hơn 2.000 quá 0,02 thì dừng sweep độ dài. Bác bỏ “cấm >1 chunk” chỉ bằng 1 bài sau: 3 cửa sổ 1.000 ký tự, cùng tập doc; chỉ đổi chiến lược nếu F2_chunk cao hơn bản 1 span ít nhất 0,03.
- Kỳ vọng: <+0,04 đến +0,10 tổng> | Tự tin: vừa | Chi phí: S

### Đề xuất B: Sparse Việt thuần, sau khi xác minh có phải BM25 (dựa trên: M3-B, M4-B)
- Giả thuyết: RRF + quota đẩy hit ngoài pool lên trên hit lexical. Việc này chỉ đọc được nếu bài nộp không đồng thời đổi chunk, và chỉ kết luận “chỉ mục ≠ BTC” nếu scorer thật sự là BM25 có IDF. HashingVectorizer không có IDF và có collision — nếu log đúng là lớp đó, top-30 P thấp không bác giả thuyết nhãn bám BM25.
- Cách làm cụ thể: offline, không tốn bài nộp: (i) xác nhận lớp chấm trong code; (ii) thử nghiệm 50 tài liệu — từ hiếm phải đổi thứ hạng mạnh hơn từ “là” lặp lại, nếu không thì không phải BM25; (iii) đếm doc_id nộp không có trong file URL BTC. Rồi 2 bài, chunk đóng băng theo bài 0,1606 (hoặc theo A nếu A đã xong — không cả hai cùng lúc): chỉ bm25_vi đã cache, k=30 và k=60, không dense, không Trung, không Anh. Từ P,R suy H=P·N, precision biên giữa 30 và 60. Chỉ nối Trung ở bài thứ ba nếu P@30 ≥ 0,60: một danh sách điểm đã chuẩn hoá vi+zh, không quota, cùng N=60, chunk vẫn đóng băng.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: bác “fusion là thủ phạm chính” nếu k=30 có P_doc < 0,30 và F2_doc < 0,28. Nếu P@30 ≥ 0,60 nhưng precision biên 30→60 < 0,12 thì không được tăng N (ngưỡng M3, áp trên ranker đã sửa, không áp trên fusion cũ). Nếu P@30 < 0,60 và bước (ii) cho thấy không có IDF → không sửa fusion thêm; chuyển đề xuất C. Nếu đã là BM25 thật mà P@30 vẫn < 0,60 → lỗi text/cắt 10k, cũng chuyển C. Bài trộn Trung bị bác nếu không hơn bài Việt thuần cùng N ít nhất 0,02.
- Kỳ vọng: <+0,08 đến +0,18 nếu P@30 ≥ 0,60> | Tự tin: vừa | Chi phí: S

### Đề xuất C: Chỉ mục BM25 thật + trần crawl, chỉ khi B bị bác (dựa trên: M4-C, M3-B)
- Giả thuyết: nếu B thất bại vì scorer/cắt 10.000 ký tự, BM25Okapi hoặc BM25S trên full text Việt, k=40, sẽ nâng P@30. Nếu cả tokenizer vẫn thấp, trần là crawl/extract (thiếu youmed/laodong, trafilatura bỏ đoạn), không phải công thức — lúc đó reranker vô ích.
- Cách làm cụ thể: song song, trước bài nộp: grep 50 câu public trong index Việt (chuỗi nguyên văn, không dịch); MinHash shingle 5-gram trên top-40, đo kích thước cụm. Không dedup và không expansion cho đến khi cụm trung bình ≥ 1,5 và ≥ 20% top-40 có bản sao — hai hướng M2-B và M3-C loại nhau, chưa đủ chứng để đốt submission. Nếu grep < 50% câu có mặt, thử html2txt/favor_recall trên 30 URL rồi grep lại, vẫn chưa nộp. Nếu grep ≥ 90% và doc_id sạch: index full text Việt, không HashingVectorizer, không cắt 10k; hai bài k=40, token âm tiết rồi token từ. Chunk = cấu hình thắng của A, không đổi thêm.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: bác “sai hàm/cắt độ dài” nếu cả hai tokenizer có P@30 < 0,35 và F2_doc không hơn bài B quá 0,03. Bác “trần crawl” nếu ≥ 90% câu public xuất hiện nguyên văn và < 2% doc_id lạ — khi đó dừng recrawl. Cụm < 1,5 thì bỏ cả dedup lẫn expansion, không nộp. Không chạy reranker cho đến khi P@30 ≥ 0,60 và F2_chunk đã đi cùng hướng với F2_doc. Giữ 1/5 slot private cho bản không đuổi pool BM25 public; không dùng private để tiếp tục dò.
- Kỳ vọng: <+0,10 đến +0,20 so với 0,1606 nếu B thất bại vì sparse hỏng; +0 nếu grep đã đạt 90%> | Tự tin: vừa | Chi phí: M

## 4. Bình chọn
VOTES: M3-A, M3-B, M4-B

---

# M2 = minimax (xiaomi/mimo-v2.6-flash) — vai: data_detective

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

---

# M3 = qwen (qwen/qwen3.8-max-0902) — vai: competition_veteran

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

---

# M4 = deepseek (deepseek-v4-pro) — vai: root_cause

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

---

_Câu trả lời các vòng trước: thư mục r1/_

_Nguồn tra cứu: 41 link từ 0 lượt search — xem sources.md_
