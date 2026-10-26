# M1 = deepseek (deepseek-v4-pro) — vai: root_cause — vòng 2

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
