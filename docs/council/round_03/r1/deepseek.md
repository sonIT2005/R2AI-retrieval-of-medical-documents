# M1 = deepseek (deepseek-v4-pro) — vai: root_cause — vòng 1

## 1. Chẩn đoán nhanh
Tôi thấy 4 giả thuyết cạnh tranh: (1) top-300 mỗi nhánh đang cắt mất tài liệu đúng ở hạng 301–1000, khiến recall doc kẹt quanh 0,599; (2) 250 tài liệu cố định quá dài so với |G| trung vị ~60, đuôi 150–250 làm giảm F2; (3) chọn top-100 tài liệu để trích chunk theo thứ tự doc-RRF chưa tối ưu cho chunk; (4) biểu diễn BGE-M3 đơn vector 2.000 ký tự đầu không đủ sắc để cạnh tranh top 0,40+. Việc vector phần sau làm tệ đi gợi ý nhãn/chunk nằm ở đầu tài liệu, nhưng không loại trừ khả năng first-stage hoặc rerank đang yếu.

## 2. Đề xuất (tối đa 3, xếp theo kỳ vọng/chi phí)

### Đề xuất A: Mở rộng vùng ứng viên từ top-300 lên top-1.000 mỗi nhánh, vẫn cắt 250
- Giả thuyết: `top-300` mỗi nhánh đang là nút thắt first-stage recall. Nếu một tài liệu đúng nằm ngoài top-300 của mọi nhánh, RRF không bao giờ lấy lại được; do đó recall doc không lên được dù top-300→250 đã cải thiện F2.
- Dựa trên bằng chứng nào trong brief: R_doc = 0,599 ở 250 tài liệu; F2_doc tăng khi giảm 400→250 nhưng P_doc vẫn rất thấp 0,157; brief không thấy đã thử tăng depth truy hồi thô.
- Cách làm cụ thể: vẫn dùng đúng các bộ retrieval hiện có (BM25 Việt, BM25 Trung, hai nhánh BGE-M3 dense), chỉ tăng số tài liệu lấy ra mỗi nhánh từ 300 lên 1.000 (hoặc ít nhất 500 nếu tốc độ chậm). Rồi chạy RRF như cũ và cắt 250 tài liệu/câu. Chunk giữ nguyên quy trình.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nộp 1 lần bản top-1.000 depth. Bác bỏ nếu F2_doc không vượt 0,342 (tăng dưới +0,009 so với 0,3328) hoặc overall không tăng ≥ +0,005 so với 0,3018; khi đó top-300 không phải nút thắt, cần cải thiện scoring thay vì mở rộng ứng viên.
- Kỳ vọng: +0,005…+0,02 overall | Tự tin: vừa | Chi phí: S

### Đề xuất B: Quét số tài liệu cố định dưới 250: nộp 150 và 125
- Giả thuyết: Dự đoán 250 vẫn quá dài so với |G| trung vị ~60; đuôi 150–250 có precision rất thấp nên F2_doc tiếp tục tăng nếu cắt sâu hơn.
- Dựa trên bằng chứng nào trong brief: chuỗi 400→250 cho F2_doc tăng đơn điệu 0,302→0,333 và brief ghi “chưa thấy đỉnh”; P_doc ở 250 chỉ 0,157.
- Cách làm cụ thể: dùng thứ tự hiện tại, lấy top N tài liệu với N=150 và N=125 cho tất cả query. Với chunk: nếu N ≥ 100 vẫn lấy top-100 trong N để trích chunk; nếu N < 100 lấy toàn bộ. Ưu tiên nộp 150 trước; nếu cải thiện rõ, nộp thêm 125/100 để định vị đỉnh.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nộp 2 lần (150, 125). Bác bỏ nếu F2_doc ở 150 < 0,345 (không tăng ít nhất +0,012 so với 0,3328) hoặc overall < 0,306; khi đó cắt cố định không phải đòn bẩy chính, dừng quét dưới 250.
- Kỳ vọng: +0,005…+0,02 overall | Tự tin: vừa | Chi phí: S

### Đề xuất C: Chọn top-100 trích chunk bằng max-sim chunk-level, không dùng thứ tự doc-RRF
- Giả thuyết: Thứ tự xếp hạng tài liệu đang tối ưu cho F2_doc nhưng chưa tối ưu cho việc có một chunk LCS≥0,4. Nhiều tài liệu đúng có chunk dễ tìm đang nằm hạng 101–250 nên không được nộp chunk, gây ra F2_chunk/F2_doc ≈ 0,81.
- Dựa trên bằng chứng nào trong brief: F2_chunk/F2_doc ≈ 0,81 dù chunk 4.000 ký tự đã cải thiện mạnh; các cấu hình chunk 95/5, 100/0 làm tệ hơn, cho thấy top-100 hiện tại có tín hiệu nhưng lựa chọn tài liệu chưa tốt.
- Cách làm cụ thể: trong 250 tài liệu hiện có của mỗi query, tính max cos BGE-M3 giữa câu hỏi Việt và các cửa sổ 1.000 ký tự trượt trên đầu 2.000 ký tự của mỗi tài liệu; xếp hạng 250 tài liệu theo max cos đó; lấy top-100 để trích chunk như cũ (mở rộng 4.000 ký tự). Không cần mã hoá lại toàn corpus; chỉ cần encode cửa sổ cho các doc trong top-250.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: nộp 1 lần, giữ nguyên 250 doc (F2_doc không đổi) nhưng thay top-100 chunk. Bác bỏ nếu F2_chunk không vượt 0,280 (tăng dưới +0,009 so với 0,2709) hoặc overall không tăng ≥ +0,005; khi đó vấn đề không nằm ở lựa chọn top-100 mà nằm ở chất lượng bản thân chunk.
- Kỳ vọng: +0,005…+0,02 overall | Tự tin: thấp | Chi phí: M

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief
- Brief không nói rõ mỗi nhánh thực sự chỉ lấy `top-300` để đưa vào RRF hay đã lấy nhiều hơn; nếu thực tế đã lấy `top-1.000` rồi cắt 250, Đề xuất A vô nghĩa.
- Không có dev có nhãn; các tiêu chí bác bỏ dựa vào LB public có nhiễu, vì vậy nên nộp cặp cấu hình cùng lúc và so sánh paired thay vì tuyệt đối một lần.
- Không rõ phân phối |G| thực tế theo từng query, chỉ có trung vị; điều này làm yếu cơ sở cho adaptive cutoff và cần bổ sung nếu có thể.
- Không rõ F2_chunk được xử lý thế nào với các tài liệu không nộp chunk; nếu nó coi doc 101–250 là mất chunk, Đề xuất C càng đáng ưu tiên.

## 4. Nguồn đã tra cứu
- không tra cứu
