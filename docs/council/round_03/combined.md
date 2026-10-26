Hội đồng model — round_03 — 2026-10-24 12:51 — 2 vòng

> Các model KHÔNG thấy code, chỉ thấy brief. Đồng thuận là tín hiệu, không phải bằng chứng — kiểm chứng với code/log thật trước khi đưa vào PLAN.

## Thành viên
- M1 = deepseek (deepseek-v4-pro) — vai: root_cause
- M2 = openai (openai/gpt-6-luna) — vai: plan_critic
- M3 = qwen (qwen/qwen3.8-max-0902) — vai: competition_veteran
- M4 = kimi (moonshotai/kimi-k3) — vai: alternative
- M5 = gemini (google/gemini-4-argon) — vai: pragmatist
- M6 = glm (z-ai/glm-5.3) — vai: simplifier
- M7 = grok (x-ai/grok-4.7) — vai: red_team
- M8 = minimax (xiaomi/mimo-v2.6-flash) — vai: data_detective

## Bảng xếp hạng đồng thuận (phiếu vòng 2 cho đề xuất vòng 1)

| Hạng | ID | Đề xuất | Của | Điểm | Người bầu |
|---|---|---|---|---|---|
| 1 | M7-A | Prepend title — đừng re-embed 1,16M trang đầy đủ | grok | 3 | M1 |
| 2 | M8-A | Đọc trần F2 theo slice |G|, quét k toàn cục, rồi k theo từng câu | minimax | 2 | M1 |
| 3 | M7-B | doc_id anh em bị loại khỏi top-400 | grok | 1 | M1 |

## Chi tiết top 3 đề xuất được bầu

**M7-A** (grok)

### Đề xuất A: Prepend title — đừng re-embed 1,16M trang đầy đủ
- Giả thuyết: Title/<h1> không nằm trong chuỗi đã index (mặc định Trafilatura là TXT không metadata; heading có link còn bị bỏ). BM25 âm tiết và vector 2.000 ký tự đầu đều thiếu tín hiệu mạnh nhất. Cùng kiểu lỗi này, ở task F2 tiếng Việt tương tự, thêm title đã kéo private F2 từ 0,4982 lên 0,5822.
- Dựa trên bằng chứng nào trong brief: Bước 1 chỉ ghi “trafilatura → văn bản”; vector cửa sổ 1.800–5.400 (không có title) −0,04; BTC 0,376 với pipeline chắc chắn đơn giản hơn Qwen3-8B; recall không tăng khi nới k lên 400.
- Cách làm cụ thể: Trên 200 URL, so `extract()` mặc định với `bare_extraction().title` và với `<title>`/`<h1>` thô. Đo tỉ lệ title dài ≥10 ký tự bị vắng trong 500 ký tự đầu. Nếu >20%, một bài nộp duy nhất: giữ nguyên BM25, RRF, k=250, chunk; chỉ đổi văn bản dense thành `title + "\n" + 500 ký tự đầu` (BGE-M3, cùng chuẩn hóa). Không chỉnh trọng số. Không encode full-text Qwen3-4B/8B trước khi bài này về.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Bác bỏ nếu F2_doc giảm ≥0,015 so với 0,3328, hoặc audit local cho <10% trang mất title. Khi đó head-bias là giả và được phép nghĩ tới chunk-level index. Nếu F2_doc ≥0,3328, giả thuyết đúng: bước kế chỉ embed title+lead bằng Qwen3-Embedding-0.6B (query có instruction tiếng Anh, document không có instruction), không embed cả 1,16M trang.
- Kỳ vọng: +0,03…+0,08 overall nếu title đang mất; nếu không thì ≤0 | Tự tin: vừa | Chi phí: S

**M8-A** (minimax)

### Đề xuất A: Đọc trần F2 theo slice |G|, quét k toàn cục, rồi k theo từng câu
- Giả thuyết: mất điểm tập trung ở hai slice ngược nhau — g nhỏ bị trần precision vì k=250, g lớn bị mất recall vì k不够 lớn; k theo câu (cắt tại "knee" điểm RRF/cos) đánh bại mọi k cố định.
- Dựa trên bằng chứng nào trong brief: |G| 5…190 (trung vị ~60); F2doc tăng đều khi k giảm 400→250 (0,302→0,333) trong khi R giảm (0,630→0,599); P doc chỉ 0,157 → chế độ precision-limited.
- Cách làm cụ thể: (1) vẽ bảng trần F2(k)=5g/(4g+k) cho g∈{5,10,20,60,190}, k∈{50,100,150,200,250,300} để biết mỗi slice "được phép" mất bao nhiêu; (2) nộp **k=200 và k=150** (chỉ cắt ranking đã có, 0 giờ encode); (3) nếu cả hai xác nhận precision-limited, làm adaptive k: cắt danh sách tại điểm mà số RRF tích lũy của câu đạt ~80–90% tổng (hoặc cos so với top-1 rơi dưới ngưỡng), hiệu chỉnh 2 ngưỡng để ra k trung bình ~200 và ~300.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: ΔF2doc(k=150 hoặc 200) ≥ +0,01 so với 250 → giả thuyết slice nhỏ là bottleneck đúng → làm tiếp adaptive; nếu cả 150 và 200 đều ≤ 250 (Δ < +0,003) → **bác bỏ**, slice nhỏ không phải nơi mất điểm (hoặc ranker không xếp gold vào top nhỏ), chuyển resources sang hướng khác; nếu adaptive không beats best global k quá +0,004 → tín hiệu không chứa thông tin |G|, dừng (b).
- Kỳ vọng: +0,03…+0,08 | Tự tin: vừa | Chi phí: M (3–4 lượt nộp, không re-encode)

**M7-B** (grok)

### Đề xuất B: doc_id anh em bị loại khỏi top-400
- Giả thuyết: Nhãn ~60 doc/câu trên corpus báo/bệnh viện crawl gồm nhiều URL cùng một bài (http/https, slash, bản syndication). Fusion trả về một URL; doc_id được chấm nằm ở bản sao ngoài top-400. Đó là trần recall, không phải thiếu k.
- Dựa trên bằng chứng nào trong brief: F2_doc giảm khi tăng 250→400 nên precision biên của hạng 251–400 gần 0, trong khi R chỉ 0,599; PubMed 0 nhãn nghĩa là nhãn gắn với tập URL cụ thể, không phải “mọi trang đúng y khoa”.
- Cách làm cụ thể: Simhash hoặc cosine >0,92 trên title+500 ký tự. Báo cáo: tỉ lệ trang có ≥1 anh em; số slot lãng phí trong top-250 (cùng cụm). Một bài nộp “dedupe”: gộp cụm trong top-400, giữ thành viên RRF cao nhất, lấp slot bằng cụm kế tiếp, vẫn 250 doc, chunk không đổi. Không trộn với bài “expand” (mỗi top-40 cụm nộp tối đa 3 doc_id).
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Dedupe bị bác nếu |Δ F2_doc| <0,005 và R không tăng ≥0,02 — anh em không chiếm slot hoặc không được cùng gán nhãn. Nếu R giảm >0,02 thì anh em có trong nhãn: chỉ khi đó mới nộp expand. Expand bị bác nếu F2_doc giảm >0,01. Cả hai thất bại thì dừng, không mang sang private.
- Kỳ vọng: +0,03…+0,07 F2_doc nếu anh em đồng nhãn; không thì ≤0 | Tự tin: thấp | Chi phí: S

## Câu trả lời vòng cuối (vòng 2)

---

# M1 = deepseek (deepseek-v4-pro) — vai: root_cause

## 1. Nhận xét từng thành viên
- M2: điểm mạnh là bám đúng bằng chứng F2_doc tăng khi giảm K và đề xuất thử sparse BGE-M3 rẻ, ít rủi ro hơn đổi model lớn. | lỗ hổng: chưa đưa ra công thức/ngưỡng cụ thể cho adaptive K; khẳng định “K thích ứng” có thể chưa kiểm chứng được nếu không có nhãn dev.
- M3: không có nội dung để đánh giá.
- M4: điểm mạnh là giả thuyết cụm/near-duplicate và doc2query mô phỏng đúng bias nhãn đầu bài — đây là hướng khác biệt có tiềm năng bước nhảy. | lỗ hổng: phụ thuộc giả định chưa kiểm chứng rằng |G|~60 tạo thành cụm; chi phí doc2query/fine-tune khá cao, và pseudo-label từ chính pipeline có rủi ro tự khóa lỗi cũ.
- M7: điểm mạnh là chỉ ra title có thể bị mất khi dùng `trafilatura.extract()` mặc định, đúng lỗi dữ liệu rẻ tiền; đề xuất audit title + dedupe sibling doc_id rất cụ thể. | lỗ hổng: chưa xác minh tỉ lệ mất title trước khi nộp; ước tính +0,03…+0,08 từ title có thể lạc quan nếu title chỉ thiếu ở số ít trang.
- M8: điểm mạnh là bảng trần F2 theo |G| giải thích logic vì sao k=250 kẹt precision cho câu ít nhãn; đề xuất audit near-dup bằng hash rất đáng làm. | lỗ hổng: thống kê |G| trung vị 60 mâu thuẫn với “không có dev có nhãn”; tín hiệu “knee” của RRF để dự đoán |G| chưa có kiểm chứng offline.

## 2. Tôi đổi quan điểm thế nào (giữ / bỏ / sửa gì, vì sao)
- Tôi **bỏ ưu tiên** đề xuất cũ M1-A (mở rộng top-300 lên top-1.000 để nộp ngay). Thay vào đó, tôi chấp nhận lập luận của M7/M8 rằng phải audit offline trước: nếu top-300 không phải nút thắt thì bài nộp top-1.000 phí lượt; audit độ sâu rất rẻ sẽ phân định điều đó.
- Tôi **giữ** hướng thử K thấp hơn nhưng sửa theo M8: thử K=150/120 kèm bảng trần F2 để tránh mò ngưỡng bằng LB; coi đây là phép phân định giả thuyết H3 (k cố định quá dài) chứ không phải tinh chỉnh.
- Tôi **thêm** hai giả thuyết title/head và near-duplicate từ M7/M8 mà vòng trước tôi bỏ sót. Đây là hai lỗi dữ liệu rất rẻ để kiểm tra, lại giải thích được P_doc thấp và tại sao vector phần sau không giúp; vì vậy tôi đưa lên trước các thay đổi embedding lớn.
- Tôi **giữ nguyên** đề xuất cũ M1-C (chọn top-100 chunk theo max-sim chunk-level) nhưng hạ ưu tiên: chỉ nên làm sau khi đã loại trừ lỗi dữ liệu, vì nếu title/duplicate là nguyên nhân gốc thì sửa chunk-level tác động nhỏ.

## 3. Đề xuất cuối (tối đa 3)
### Đề xuất A: Audit offline 3 nguyên nhân gốc (title/đầu bài, near-duplicate, độ sâu top-300) (dựa trên: M7-A, M8-B, M4-A, M1-A)
- Giả thuyết: Điểm kẹt do một trong ba lỗi dữ liệu/truy hồi: (i) title/đoạn đầu bị bỏ khi index, (ii) near-duplicate chiếm slot top-250, (iii) top-300 mỗi nhánh cắt mất tài liệu đúng.
- Cách làm cụ thể:
  1. **Audit title**: lấy 200 URL mẫu, so sánh `trafilatura.bare_extraction().title` với 500 ký tự đầu văn bản hiện dùng; tính tỉ lệ title dài ≥10 ký tự bị thiếu.
  2. **Audit near-dup**: với 50 câu mẫu, lấy top-400 theo pipeline hiện tại; dùng hash chuẩn hóa/SimHash trên title+500 ký tự đầu; đếm tỉ lệ slot trong top-250 bị chiếm bởi trang gần trùng với một trang xếp hạng cao hơn.
  3. **Audit depth**: với 20 câu, chạy lại retrieval với top-1.000 mỗi nhánh rồi RRF cắt 250; đo tỉ lệ tài liệu trong top-250 mới đến từ hạng 301+ của ít nhất một nhánh.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Nếu title thiếu <10%, near-dup waste <3%, và thay đổi do depth <5% → bác bỏ cả ba giả thuyết dữ liệu/độ sâu; chuyển nguồn lực sang H3 (K) và H4 (biểu diễn embedding/reranker). Nếu một chỉ số vượt ngưỡng, thực hiện LB tương ứng ở Đề xuất C hoặc B.
- Kỳ vọng: không trực tiếp tăng LB nhưng tiết kiệm 2–3 lượt nộp; khả năng phát hiện ≥1 nguyên nhân khoảng 60% | Tự tin: vừa | Chi phí: S (1–2 giờ CPU, không cần GPU, không nộp)

### Đề xuất B: Kiểm tra H3 bằng hai bài nộp K=150 và K=120 (dựa trên: M8-A, M2-A, M7-C)
- Giả thuyết: K=250 cố định là nguồn mất điểm chính: các câu có |G| nhỏ bị trần precision thấp (F2 ≈ 5g/(4g+K)), trong khi câu lớn vẫn còn recall. Nếu K thấp hơn cải thiện F2 doc, giả thuyết đúng và đáng đầu tư adaptive K.
- Cách làm cụ thể: Trước khi nộp, tính bảng trần F2 cho g∈{5,10,20,60,190} tại K=150/120/250 để xác định slice nào được lợi. Giữ nguyên thứ hạng hiện tại; nộp một bản K=150 (chunk vẫn lấy top-100 nếu K≥100, ngược lại lấy toàn bộ). Nếu K=150 cải thiện ≥+0,01 F2_doc, nộp tiếp K=120 để định vị đỉnh; nếu cải thiện ít thì dừng, không nộp K=120.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Bác bỏ H3 nếu F2_doc của K=150 không vượt 0,3428 (tăng ≥+0,01 so với 0,3328) và overall không tăng ≥+0,005; khi đó dừng mọi tinh chỉnh k cố định/adaptive. Nếu K=150 thắng, chỉ tiếp K=120 khi F2_doc tăng thêm ≥+0,005; nếu K=120 lại giảm hoặc không tăng, dừng và không fit thêm ngưỡng trên public.
- Kỳ vọng: +0,005…+0,02 overall nếu H3 đúng; ≤0 nếu sai | Tự tin: vừa | Chi phí: S (1–2 lượt nộp, không re-encode)

### Đề xuất C: Một can thiệp dữ liệu rẻ nhất theo kết quả audit A (dựa trên: M7-A, M7-B, M8-B)
- Giả thuyết: Nếu audit A cho title thiếu >20% hoặc near-dup waste >10%, nguyên nhân gốc nằm ở dữ liệu đầu vào, không phải model. Sửa đúng lỗi đó sẽ tăng precision/recall mà không phải đổi retriever.
- Cách làm cụ thể:
  - Nếu **title thiếu >20%**: nộp một bản chỉ đổi chuỗi đầu vào BM25 Việt và BGE-M3 dense thành `title + "\n" + 1000 ký tự đầu`; giữ nguyên trọng số RRF, K=250, chunk.
  - Ngược lại, nếu **near-dup waste >10%**: gộp cụm gần trùng (cos >0,92 trên title+500 ký tự) trong top-400, giữ doc_id có RRF cao nhất, lấp đầy đến 250 doc; chunk dùng chính 250 doc này.
  - Nếu cả hai cùng vượt ngưỡng, ưu tiên title trước vì một bài nộp không cần đổi toàn bộ pipeline.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Với bản title: bác bỏ nếu F2_doc <0,3428 (không tăng ≥+0,01) hoặc overall <0,306; khi đó title không phải nguyên nhân chính. Với bản gộp near-dup: bác bỏ nếu |ΔF2_doc| <0,005 và R_doc không tăng ≥0,02; nếu R_doc giảm >0,02, chuyển sang thử expand (nộp tối đa 3 doc/cụm) vì khả năng anh em sinh đôi cũng có nhãn. Nếu cả hai thất bại, dừng hướng dữ liệu và chuyển sang H4 (embedding/reranker).
- Kỳ vọng: +0,01…+0,04 overall nếu title; +0,01…+0,03 nếu near-dup; ≤0 nếu audit sai | Tự tin: thấp–vừa | Chi phí: S–M (một bài nộp; nếu title cần re-encode corpus thì khoảng 2–3 giờ GPU)

## 4. Bình chọn
VOTES: M7-A, M8-A, M7-B

---

# M2 = openai (openai/gpt-6-luna) — vai: plan_critic

❌ LỖI: HTTP 402: {"error":{"message":"Insufficient credits. Add more using https://openrouter.ai/settings/credits","code":402,"metadata":{"limit_source":"openrouter_credits","remedy_hint":"Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance."}}}

---

# M3 = qwen (qwen/qwen3.8-max-0902) — vai: competition_veteran

❌ LỖI: HTTP 402: {"error":{"message":"Insufficient credits. Add more using https://openrouter.ai/settings/credits","code":402,"metadata":{"limit_source":"openrouter_credits","remedy_hint":"Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance."}}}

---

# M4 = kimi (moonshotai/kimi-k3) — vai: alternative

❌ LỖI: HTTP 402: {"error":{"message":"Insufficient credits. Add more using https://openrouter.ai/settings/credits","code":402,"metadata":{"limit_source":"openrouter_credits","remedy_hint":"Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance."}}}

---

# M7 = grok (x-ai/grok-4.7) — vai: red_team

❌ LỖI: HTTP 402: {"error":{"message":"Insufficient credits. Add more using https://openrouter.ai/settings/credits","code":402,"metadata":{"limit_source":"openrouter_credits","remedy_hint":"Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance."}}}

---

# M8 = minimax (xiaomi/mimo-v2.6-flash) — vai: data_detective

❌ LỖI: HTTP 402: {"error":{"message":"Insufficient credits. Add more using https://openrouter.ai/settings/credits","code":402,"metadata":{"limit_source":"openrouter_credits","remedy_hint":"Add credits at https://openrouter.ai/settings/credits, or lower max_tokens / prompt size to fit your remaining balance."}}}

---

_Câu trả lời các vòng trước: thư mục r1/_

_Nguồn tra cứu: 134 link từ 0 lượt search — xem sources.md_
