# M8 = minimax (xiaomi/mimo-v2.6-flash) — vai: data_detective — vòng 1

## 1. Chẩn đoán nhanh

Với F2 macro và |G| dao động 5…190, k=250 cố định tạo trần precision theo từng câu: F2_max ≈ 5g/(4g+250), nên câu có g≤20 bị kẹt ≤0,30 **ngay cả khi xếp hạng hoàn hảo** (g=5 → 0,093; g=60 → 0,61; g=190 → 0,94) — slice nhỏ kéo cả macro xuống. Ngược lại, slice g lớn cần k lớn để giữ recall (R đã rơi 0,630 → 0,599 khi hạ 300→250), nên **bất kỳ k toàn cục nào cũng sai ở một trong hai đầu** — đó là lý do bảng 400/350/300/250 chưa thấy đỉnh và vì sao ý tưởng (b) đúng hướng. Quan sát "vector phần sau tài liệu làm tệ" là bằng chứng gián tiếp về **distribution shift giữa nhãn và văn bản thật**: nhiều khả năng nhãn sinh ra từ phần đầu tài liệu, nên pipeline đang khớp bias của người tạo nhãn (tốt cho LB, vô nghĩa với mọi chỉnh ở phần sau). Corpus tự crawl 699k+237k trang không thấy bước dedup nào trong pipeline → near-duplicate chiếm slot top-250 và biến thể cùng nội dung nhưng doc_id khác vừa tốn slot vừa mất credit chunk (LCS bắt buộc cùng doc_id). Và 45 lượt tune trên public không có dev có nhãn khiến mọi chênh lệch ±0,002 không phân biệt được tín hiệu với nhiễu LB.

## 2. Đề xuất (tối đa 3, xếp theo kỳ vọng/chi phí)

### Đề xuất A: Đọc trần F2 theo slice |G|, quét k toàn cục, rồi k theo từng câu
- Giả thuyết: mất điểm tập trung ở hai slice ngược nhau — g nhỏ bị trần precision vì k=250, g lớn bị mất recall vì k不够 lớn; k theo câu (cắt tại "knee" điểm RRF/cos) đánh bại mọi k cố định.
- Dựa trên bằng chứng nào trong brief: |G| 5…190 (trung vị ~60); F2doc tăng đều khi k giảm 400→250 (0,302→0,333) trong khi R giảm (0,630→0,599); P doc chỉ 0,157 → chế độ precision-limited.
- Cách làm cụ thể: (1) vẽ bảng trần F2(k)=5g/(4g+k) cho g∈{5,10,20,60,190}, k∈{50,100,150,200,250,300} để biết mỗi slice "được phép" mất bao nhiêu; (2) nộp **k=200 và k=150** (chỉ cắt ranking đã có, 0 giờ encode); (3) nếu cả hai xác nhận precision-limited, làm adaptive k: cắt danh sách tại điểm mà số RRF tích lũy của câu đạt ~80–90% tổng (hoặc cos so với top-1 rơi dưới ngưỡng), hiệu chỉnh 2 ngưỡng để ra k trung bình ~200 và ~300.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: ΔF2doc(k=150 hoặc 200) ≥ +0,01 so với 250 → giả thuyết slice nhỏ là bottleneck đúng → làm tiếp adaptive; nếu cả 150 và 200 đều ≤ 250 (Δ < +0,003) → **bác bỏ**, slice nhỏ không phải nơi mất điểm (hoặc ranker không xếp gold vào top nhỏ), chuyển resources sang hướng khác; nếu adaptive không beats best global k quá +0,004 → tín hiệu không chứa thông tin |G|, dừng (b).
- Kỳ vọng: +0,03…+0,08 | Tự tin: vừa | Chi phí: M (3–4 lượt nộp, không re-encode)

### Đề xuất B: Audit near-duplicate corpus + collapse lúc merge RRF
- Giả thuyết: >10% slot top-250 bị trùng lặp nội dung (báo syndicated, trang bệnh viện/nhà thuốc nhân bản), gộp cụm giải phóng slot cho tài liệu đa dạng → P doc tăng mà không đổi retriever.
- Dựa trên bằng chứng nào trong brief: corpus "tự crawl" 699k VI + 237k ZH, pipeline liệt kê trafilatura nhưng không có bước dedup; chunk đúng đòi hỏi đúng doc_id nên biến thể cùng chữ là FP/FN kép.
- Cách làm cụ thể: hash văn bản chuẩn hoá (lowercase, bỏ khoảng trắng/punctuation) trên cả hai corpus → đếm nhóm trùng chính xác; MinHash shingle 5-gram → % trang nằm trong cụm ≥2 thành viên; với ~30 câu mẫu, đếm % top-250 nằm trong cụm đã có thành viên rank cao hơn ("slot waste").
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: slot waste <3% → **bỏ hướng, không tốn lượt**; waste >10% → collapse cụm trùng chính xác (giữ ID rank cao nhất) ngay sau merge RRF, nộp 1 bài: ΔF2doc ≥ +0,01 → áp dụng; F2doc **giảm** → gold thường là biến thể không phải ID "gốc" ⇒ suy ra cách người tạo nhãn xử lý trùng lặp (thông tin quý cho mọi quyết định sau); |Δ| < +0,005 → duplicates không phải yếu tố, abandon.
- Kỳ vọng: +0,005…+0,02 | Tự tin: thấp/vừa | Chi phí: S (inspection 30–60 phút, 1 lượt nộp, 0 re-encode)

### Đề xuất C: Audit độ phủ chunk — vị trí cửa sổ best và tài liệu vượt 4000/2000 ký tự
- Giả thuyết: F2chunk/F2doc = 0,81 do hai thứ: cửa sổ BGE-M3 1.000 ký tự được chọn nằm xa phần đầu (trong khi nhãn thiên đầu), và tài liệu dài bị cắt ở 4000 (VI) / 2000 (ZH).
- Dựa trên bằng chứng nào trong brief: chunk 1000→4000 từng +0,127 (độ phủ là đòn bẩy thật, chưa thử >4000); "vector phần sau làm tệ" (−0,04) nghi ngờ nhãn thiên đầu; TB trang VI 3.553 ký tự nên có một phần đáng kể >4000.
- Cách làm cụ thể: (0 chi phí) histogram start-offset của cửa sổ 1.000 ký tự được chọn trên top-100/câu — bao nhiêu % mass nằm trong 25% đầu văn bản; phân bố độ dài top-100 docs: % >4000 (VI), % >2000 (ZH); xem tay 30 mẫu câu mà cửa sổ best nằm ở giữa/cuối doc.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nếu ≥70% mass tập trung ở đầu **và** ≥25% docs vượt ngưỡng length → nộp chunk mở rộng 8000 VI / 4000 ZH (LZMA cho file <100MB); ΔF2chunk ≥ +0,015 → giữ hướng "dài hơn"; Δ < +0,005 → **bác bỏ**, độ phủ hết hạn mức, chuyển sang tăng số chunk (ý tưởng e) thay vì dài hơn; nếu mass cửa sổ rải rộng → nghi ngờ "nhãn thiên đầu" sai, phải xem lại cách diễn giải quan sát "vector phần sau".
- Kỳ vọng: +0,005…+0,02 (tổng, =(Δdoc+Δchunk)/2) | Tự tin: vừa | Chi phí: S–M (1 lượt nộp)

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief
- **Stats |G| (trung vị 60, 5…190) lấy từ đâu** khi ghi "không có dev có nhãn"? Nếu tồn tại train/dev có nhãn thì toàn bộ câu hỏi 2 và đề xuất A cần làm lại trên nhãn thật — đây là thông tin quyết định.
- **Định nghĩa precision ở mức chunk**: một chunk nộp dài có thể khớp nhiều reference cùng lúc không? P tính theo chunk nộp hay theo token? Nếu có penalty ẩn (ví dụ mỗi chunk nộp chỉ được khớp 1 reference, hoặc cắt theo độ dài) thì cơ sở "dài không bị phạt" và Đề xuất C sụp.
- **Nhãn được tạo bằng gì** (pooling bởi retriever nào? LLM chấm? head bao nhiêu ký tự?) — brief chỉ suy đoán từ −0,04; đây là giả thuyết chưa kiểm chứng, nhưng nó quyết định nên *bắt chước* bias đó hay chống lại.
- **Nhiễu LB**: nộp lại nguyên file có đổi điểm không? Không có ước lượng độ lệch chuẩn này thì mọi kết luận ±0,002 (vd. RRF k=100 "+0,001", bm25_zh "±0") đều vô nghĩa.
- **Private cùng phân phối với public?** 45 lượt tune public có thể overfit; và per-slice P/R không đọc được từ macro — cần kỹ thuật "slice-isolated A/B" (đổi hành vi của đúng 1 slice, suy ra hiệu ứng slice từ Δ macro của 1 lượt nộp), ví dụ chỉ bật chia câu hỏi dài (>60 từ, max 283 so với trung vị 18) để đo riêng đóng góp của slice hiếm này.

## 4. Nguồn đã tra cứu
- Sampling Bias Due to Near-Duplicates in Learning to Rank — https://downloads.webis.de/publications/papers/froebe_2020c.pdf — near-duplicate trong web crawl làm sai lệch đánh giá và giảm chất lượng xếp hạng; dedup hệ thống trước train/eval có lợi →支撑 Đề xuất B.
- Bias and the Limits of Pooling for Large Collections — https://dlnext.acm.org/doi/10.1007/s10791-007-9032-x — bộ nhãn sinh từ pooling có xu hướng thiên tài liệu chứa từ khoá title/truy vấn → giải thích vì sao pipeline khớp "phần đầu tài liệu" lại thắng LB.
- TRACE — label_manual.py (GitHub) — https://github.com/kushagrathisside/TRACE/blob/eeb09202/backend/eval/label_manual.py — "labels drawn from a single system's output encode that system's bias as ground truth": nhãn sinh bởi một retriever đơn lẻ sẽ đóng khung bias retriever đó → nên khớp bias người tạo nhãn thay vì giao tranh với nó.
- LLMs can be Fooled into Labelling a Document as Relevant — https://arxiv.org/html/2501.17969v1 — nhãn LLM chấm liên quan dễ bị query-term làm nhiễu, thiên "relevant" → cảnh báo noise nếu BTC sinh nhãn bằng LLM.
- Retrieval Metrics — sources of relevance labels — https://sarangk90.github.io/awesome-agent-evals-and-guardrails/02-offline-evals/02-retrieval-metrics/ — nhãn tổng hợp từ chunk gốc làm chunk hợp lệ khác bị tính miss và làm BM25 "phình" nhờ lặp từ khoá → giải thích nhãn không đầy đủ + BM25 mạnh.
- Qwen3-Embedding (0.6B/4B, 06/2025) — **không tra cứu** (đã chạm giới hạn lượt tìm kiếm của công cụ).
