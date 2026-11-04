# M7 = grok (x-ai/grok-4.7) — vai: red_team — vòng 1

Tôi sẽ tra cứu metric F2 chunk/doc, cách nhãn retrieval y khoa thường được tạo, và các bẫy nộp bài trước khi chỉ ra lỗ hổng.## 1. Chẩn đoán nhanh
Điểm đang kẹt vì recall vàng bão hòa trước top-250: cùng kiểu xếp hạng, F2_doc 250→0,333 nhưng 400→0,302, nên ~40% doc vàng không nằm ở hạng 251–400. Tài khoản BTC đã 0,376 trong khi pipeline hiện tại 0,302 — lệch 0,07 này giống lỗi biểu diễn/doc_id hơn là thiếu model lớn hơn. Giả định đang dùng `trafilatura.extract()` mặc định: TXT không kèm metadata, title nằm ngoài thân bài. P=0,157 và R=0,599 cho F2 gộp ≈0,383 nhưng macro F2_doc chỉ 0,333; k=250 cố định nghiền các câu |G| nhỏ (5…60). Kết luận “vector phần sau làm nhãn lộ ra” và “reranker vô dụng” đều chưa được nhận diện: thí nghiệm max-sim có thể đã bỏ title, còn bge-reranker-v2-m3 được fine-tune ở 1024 token và objective kiểu “đoạn trả lời câu hỏi” lệch nhãn rộng ~60 doc/câu.

## 2. Đề xuất (tối đa 3, xếp theo kỳ vọng/chi phí)
### Đề xuất A: Prepend title — đừng re-embed 1,16M trang đầy đủ
- Giả thuyết: Title/<h1> không nằm trong chuỗi đã index (mặc định Trafilatura là TXT không metadata; heading có link còn bị bỏ). BM25 âm tiết và vector 2.000 ký tự đầu đều thiếu tín hiệu mạnh nhất. Cùng kiểu lỗi này, ở task F2 tiếng Việt tương tự, thêm title đã kéo private F2 từ 0,4982 lên 0,5822.
- Dựa trên bằng chứng nào trong brief: Bước 1 chỉ ghi “trafilatura → văn bản”; vector cửa sổ 1.800–5.400 (không có title) −0,04; BTC 0,376 với pipeline chắc chắn đơn giản hơn Qwen3-8B; recall không tăng khi nới k lên 400.
- Cách làm cụ thể: Trên 200 URL, so `extract()` mặc định với `bare_extraction().title` và với `<title>`/`<h1>` thô. Đo tỉ lệ title dài ≥10 ký tự bị vắng trong 500 ký tự đầu. Nếu >20%, một bài nộp duy nhất: giữ nguyên BM25, RRF, k=250, chunk; chỉ đổi văn bản dense thành `title + "\n" + 500 ký tự đầu` (BGE-M3, cùng chuẩn hóa). Không chỉnh trọng số. Không encode full-text Qwen3-4B/8B trước khi bài này về.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Bác bỏ nếu F2_doc giảm ≥0,015 so với 0,3328, hoặc audit local cho <10% trang mất title. Khi đó head-bias là giả và được phép nghĩ tới chunk-level index. Nếu F2_doc ≥0,3328, giả thuyết đúng: bước kế chỉ embed title+lead bằng Qwen3-Embedding-0.6B (query có instruction tiếng Anh, document không có instruction), không embed cả 1,16M trang.
- Kỳ vọng: +0,03…+0,08 overall nếu title đang mất; nếu không thì ≤0 | Tự tin: vừa | Chi phí: S

### Đề xuất B: doc_id anh em bị loại khỏi top-400
- Giả thuyết: Nhãn ~60 doc/câu trên corpus báo/bệnh viện crawl gồm nhiều URL cùng một bài (http/https, slash, bản syndication). Fusion trả về một URL; doc_id được chấm nằm ở bản sao ngoài top-400. Đó là trần recall, không phải thiếu k.
- Dựa trên bằng chứng nào trong brief: F2_doc giảm khi tăng 250→400 nên precision biên của hạng 251–400 gần 0, trong khi R chỉ 0,599; PubMed 0 nhãn nghĩa là nhãn gắn với tập URL cụ thể, không phải “mọi trang đúng y khoa”.
- Cách làm cụ thể: Simhash hoặc cosine >0,92 trên title+500 ký tự. Báo cáo: tỉ lệ trang có ≥1 anh em; số slot lãng phí trong top-250 (cùng cụm). Một bài nộp “dedupe”: gộp cụm trong top-400, giữ thành viên RRF cao nhất, lấp slot bằng cụm kế tiếp, vẫn 250 doc, chunk không đổi. Không trộn với bài “expand” (mỗi top-40 cụm nộp tối đa 3 doc_id).
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Dedupe bị bác nếu |Δ F2_doc| <0,005 và R không tăng ≥0,02 — anh em không chiếm slot hoặc không được cùng gán nhãn. Nếu R giảm >0,02 thì anh em có trong nhãn: chỉ khi đó mới nộp expand. Expand bị bác nếu F2_doc giảm >0,01. Cả hai thất bại thì dừng, không mang sang private.
- Kỳ vọng: +0,03…+0,07 F2_doc nếu anh em đồng nhãn; không thì ≤0 | Tự tin: thấp | Chi phí: S

### Đề xuất C: Một bài k=120 để chặn overfit cutoff — đừng fit (b) trên LB gộp
- Giả thuyết: Macro F2 bị kéo bởi câu |G| nhỏ, nhưng không có điểm từng câu nên không hiệu chỉnh được hàm cắt. Mọi ngưỡng cos/RRF-so-với-top-1 fit trên LB gộp sẽ ăn nhiễu public (đã ~45 bài; các delta k=30/100 chỉ −0,003/+0,001, coi là nhiễu). Cắt k có đỉnh, nhưng không phải bước +0,05. Chunk: LCS/|g|≥0,4 không phạt độ dài; cửa sổ 4.000 ký tự tâm theo cos chỉ hại nếu nhiều doc chunk >4.000 ký tự.
- Dựa trên bằng chứng nào trong brief: |G| 5…190, trung vị ~60; F2(P̄,R̄)≈0,383 ≠ macro 0,333; “chưa thấy đỉnh” ở dưới 250; chunk 1.000→4.000 đã +0,127 F2_chunk rồi đứng; không có dev có nhãn.
- Cách làm cụ thể: Một bài, cùng thứ hạng, chỉ cắt còn 120 doc (chunk vẫn 85/15 trong số đó). Song song, local, không nộp: histogram độ dài top-100. Chỉ nếu >25% doc chunk dài hơn 4.000 ký tự mới được phép một bài thứ hai “chunk = 4.000 ký tự đầu, hoặc cả bài nếu ngắn hơn”, danh sách doc giữ nguyên. Cấm nộp hàm k theo câu đã fit. Nếu vẫn muốn adaptive: đăng ký trước một công thức, một lần, không sửa sau khi thấy điểm.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Nếu k=120 không tăng overall ≥0,015 so với 0,3018, dừng mọi tinh chỉnh k/ngưỡng — không đủ +0,05. Bài chunk-đầu bị bác nếu F2_chunk không tăng ≥0,015 trong khi F2_doc lệch <0,005. Minh họa thiệt hại k cố định (giả định recall đủ, chưa đo được): |G|=5, k=250 → F2≈0,09; k=10 → F2≈0,83.
- Kỳ vọng: +0,00…+0,02 overall từ k=120; không phải bước nhảy | Tự tin: cao rằng đây không phải +0,05 | Chi phí: S

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief
- Chưa thấy log `with_metadata` / title có được nối vào text index và vào chuỗi chunk hay không. Đây là giả định của đề xuất A.
- Thí nghiệm “vector phần sau” không ghi rõ thay thế vector đầu hay max-sim cộng thêm, và có bỏ title không. −0,04 không chứng minh cách BTC sinh nhãn.
- bge-reranker −0,012 chạy trên 1.500 ký tự đầu; model được khuyến nghị `max_length=1024` vì fine-tune ở độ dài đó. Qwen3-Reranker mặc định chấm “passage that answer the query”; với nhãn ~60 doc/câu, instruction phải là tương đồng chủ đề, nếu không sẽ lặp lại thất bại. Chưa đủ chứng cứ để xếp (c) là bước nhảy.
- Qwen3-Embedding: instruction chỉ trên query, tiếng Anh, dạng `Instruct: …\nQuery:…`; document không thêm instruction. Lệch chỗ này làm (a) sụt dù model mạnh hơn trên MTEB. BGE-M3 còn đầu sparse chưa dùng; card mẫu khuyên hybrid, không chỉ 1 vector dense/tài liệu.
- Không có điểm từng câu trên LB → không thể kiểm (b) mà không overfit public. Private chỉ 5 bài: chốt trước tối đa 2 phương án đã thắng public (hiện tại vs title-prepend), không tiếp tục dò trọng số 0,33 / 175–75.
- Thiếu: tokenizer chính thức của LCS_token; chunk có phải là chuỗi con của field BTC hay chỉ cần LCS với gold; doc_id có phân biệt hoa thường, slash, `www` không; bản dịch Trung có temperature=0 và cache không. Không tìm thấy write-up của đúng cuộc thi (1.200 câu, LCS chunk, corpus Việt+Trung) nên không suy ra pipeline của đội 0,40+ từ nguồn ngoài.

## 4. Nguồn đã tra cứu
- Trafilatura — Python usage (TXT mặc định không metadata; `with_metadata`) — https://trafilatura.readthedocs.io/en/latest/usage-python.html — `extract()` mặc định không trả title; title nằm ở metadata/`bare_extraction`.
- trafilatura issue #70 — https://github.com/adbar/trafilatura/issues/70 — `extract()` chỉ trả plain text, không trả title như `bare_extraction()`.
- trafilatura issue #354 — https://github.com/adbar/trafilatura/issues/354 — heading có link hoặc fallback “chỉ lấy paragraph” làm rơi h2/h3.
- DRiLL at VLSP 2025 (Hieu & Do) — https://aclanthology.org/2025.vlsp-1.20.pdf — thêm title tăng private F2 0,4982 → 0,5822 trên task retrieval tiếng Việt cùng họ F2.
- BAAI/bge-m3 model card — https://huggingface.co/BAAI/bge-m3 — pipeline được khuyên là hybrid (dense+sparse) rồi mới rerank, không phải một vector/tài liệu.
- BAAI/bge-reranker-v2-m3 discussion #9 — https://huggingface.co/BAAI/bge-reranker-v2-m3/discussions/9 — context tới 8192 nhưng fine-tune max length 1024; nên đặt `max_length=1024`.
- Qwen3-Embedding README — https://raw.githubusercontent.com/QwenLM/Qwen3-Embedding/main/README.md — instruction trên query thường +1%…+5%; document không gắn instruction.
- Qwen/Qwen3-Reranker-4B — https://huggingface.co/Qwen/Qwen3-Reranker-4B — template mặc định là yes/no “passage answer the query”, không phải độ liên quan chủ đề rộng.
- The tipping point: F-score vs number retrieved — https://www.sciencedirect.com/science/article/abs/pii/S0306457312000295 — F có một đỉnh theo số tài liệu nộp; đỉnh đó phụ thuộc truy vấn, không phải một k toàn cục.
- Không có URL cuộc thi này: các truy vấn `relevant_docs`/`relevant_chunks`/LCS y khoa tiếng Việt không ra đề bài 1.200 câu, corpus 699k+237k.
