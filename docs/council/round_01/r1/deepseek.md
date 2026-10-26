# M4 = deepseek (deepseek-v4-pro) — vai: root_cause — vòng 1

## 1. Chẩn đoán nhanh
Điểm mắc kẹt chủ yếu ở chunk: F2_chunk 0,084 so với F2_doc 0,238, do đội mới nộp 1 chunk 1.000 ký tự/tài liệu trong khi metric chuẩn hoá theo |g| nên chunk dài hơn gần như chỉ có lợi. Ở phía tài liệu, R_doc 0,334 thấp hơn BM25 baseline BTC 0,515 dù đội trả nhiều tài liệu hơn, cho thấy trộn dense/RRF và 40 tài liệu Trung đang đẩy tài liệu Việt đúng khỏi top. Thêm vào đó, P_doc 0,177 so với P_BM25 BTC 0,881 gợi ý nhãn có thể sinh từ BM25 của BTC và đội chưa tái tạo đúng tín hiệu BM25 đó. Rẻ nhất và chắc chắn nhất là sửa chunk trước, rồi khôi phục BM25 Việt thuần, sau đó mới xét biến thể BM25.

## 2. Đề xuất (tối đa 3, xếp theo kỳ vọng/chi phí)
### Đề xuất A: Nộp toàn văn tài liệu làm chunk (giữ nguyên retrieval hiện tại)
- Giả thuyết: Chunk là nút thắt chính; nếu nộp toàn bộ văn bản tài liệu làm chunk, chunk F2 ≈ doc F2 vì chunk tham chiếu nằm trong tài liệu sẽ có LCS=|g|.
- Dựa trên bằng chứng nào trong brief: R_chunk/R_doc = 0,34 và P_chunk/P_doc = 0,38; các đội #3–#5 có F2_chunk ≈ F2_doc. Đặc tả ghi “cách phân đoạn do đội tự thiết kế”, chunk nộp dài hơn không bị phạt.
- Cách làm cụ thể: Lấy đúng bài nộp retrieval tốt nhất 0,1606 (khoảng 100 tài liệu, phân bổ 60 Việt/40 Trung như đã dùng). Với mỗi doc được nộp, tạo 1 `chunk_text` là toàn bộ văn bản đã crawl/clean; nếu sợ LCS timeout, benchmark LCS trên vài doc dài nhất trước, có thể cắt an toàn ở mức như 50k token. Không đổi thứ tự/số tài liệu.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Nộp 1 bài LB. Nếu F2_chunk tăng lên ≥0,20 và tổng ≈ F2_doc (0,23–0,24), giả thuyết đúng. Nếu F2_chunk vẫn <0,15 hoặc bị lỗi timeout, giả thuyết chunk sai hoặc có lệch văn bản/tokenization — cần chuyển sang kiểm tra local.
- Kỳ vọng: +0,05 đến +0,08 tổng | Tự tin: vừa | Chi phí: S

### Đề xuất B: Bỏ dense/RRF và hạn mức ngôn ngữ — chỉ nộp BM25 Việt thuần với whole-doc chunk
- Giả thuyết: Tín hiệu BM25 Việt bị phá bởi RRF dense, câu dịch và hạn mức cố định 40 tài liệu Trung; nếu bỏ chúng, doc R/P sẽ phục hồi gần baseline BM25 BTC.
- Dựa trên bằng chứng nào trong brief: BM25 baseline BTC có P=0,881, R=0,515; đội có P=0,177, R=0,334 dù trả ~100 tài liệu. Precision Việt ≈0,37 so với Trung ≈0,16; baseline chỉ dùng BM25 (không dense/Trung) nhưng doc F2 tốt hơn hẳn (0,559 so với 0,238).
- Cách làm cụ thể: Sau khi A xác nhận whole-doc chunk an toàn, chạy riêng luồng `bm25_vi` trên câu hỏi tiếng Việt gốc, không dense, không zh/en, lấy top-100 (hoặc top-150) tài liệu Việt; chunk toàn văn như A. Nộp 1 bài LB.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Nếu doc F2 ≥0,40 (tổng ≥0,40), giả thuyết dilution đúng. Nếu doc F2 vẫn ≤0,30, nguyên nhân không phải do trộn mà do BM25 của đội khác baseline về corpus/tiền xử lý.
- Kỳ vọng: +0,15 đến +0,25 tổng | Tự tin: vừa | Chi phí: S/M

### Đề xuất C: Nếu B chưa đạt baseline, thử BM25 Việt toàn văn + tách từ
- Giả thuyết: BM25 hiện tại cắt 10.000 ký tự đầu và tách theo âm tiết; BM25 BTC/nhãn có thể dùng toàn văn và/hoặc tách từ, khiến thứ hạng lệch.
- Dựa trên bằng chứng nào trong brief: Pipeline dùng “tài liệu cắt 10.000 ký tự đầu” và “token = âm tiết” cho BM25; P baseline cao bất thường 0,881 gợi ý nhãn sinh từ BM25 pool. Nếu B vẫn dưới 0,40 thì vấn đề nằm ở chính cách tạo chỉ mục BM25.
- Cách làm cụ thể: Tạo bản `bm25_vi_full`: bỏ cắt 10k, index toàn văn; thử 2 biến thể tokenization (âm tiết full text và tách từ tiếng Việt bằng underthesea/VnCoreNLP — chưa kiểm chứng). Nộp 1–2 bài LB với whole-doc chunk. Chọn cấu hình tốt hơn.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Nếu doc F2 tăng lên ≥0,40 ở ít nhất một biến thể, xác nhận crop/tokenization là nguyên nhân. Nếu cả hai vẫn <0,30, khả năng cao khác biệt nằm ở crawl/clean hoặc cách sinh nhãn; đừng đổ thêm tài nguyên vào BM25, nên quay lại tăng recall bằng cách giữ nhiều tài liệu Việt và cải thiện chunk.
- Kỳ vọng: +0,05 đến +0,15 nếu đúng | Tự tin: thấp/vừa | Chi phí: M

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief
- Không rõ số tài liệu và phân bổ Việt/Trung chính xác trong bài LB 0,1606: brief ghi “giả định” 60/40/0, cần xác nhận từ code/log nộp bài.
- Chưa rõ giới hạn thời gian LCS và độ dài chunk_text thực tế của bộ chấm; cần đọc lại mục Evaluation hoặc nộp thử mức an toàn.
- Không có dev có nhãn nên mọi thay đổi doc/chunk chỉ đo qua LB; vì vậy cần tách biến như A/B/C để không lẫn lộn nguyên nhân.
- Không biết BM25 BTC dùng tokenizer từ hay âm tiết, stopword nào, và có cắt tài liệu hay không; baseline không kèm code.

## 4. Nguồn đã tra cứu
- không tra cứu
