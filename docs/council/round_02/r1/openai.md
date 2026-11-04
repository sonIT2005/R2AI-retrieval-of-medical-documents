# M2 = openai (openai/gpt-6-luna) — vai: plan_critic — vòng 1

## 1. Chẩn đoán nhanh
Điểm dừng chủ yếu ở truy hồi tài liệu: G có R doc 0,322, trong khi precision đã ở mức 0,174; reranking không thể tìm tài liệu bị loại khỏi pool ban đầu. Có cơ hội tăng recall vì dense mạnh hơn BM25 tiếng Việt và các lượt truy hồi có độ trùng thấp, nhưng chỉ 2.000 ký tự đầu có thể bỏ sót nội dung ở tài liệu dài. L=4.000 giúp chunk rõ rệt, nên tăng N mà giữ nguyên L có rủi ro vỡ giới hạn file. Kết quả H đang chấm là phép thử quan trọng: chờ kết quả đó trước khi đổi thêm phân bổ ngôn ngữ.

## 2. Đề xuất (tối đa 3, xếp theo kỳ vọng/chi phí)
### Đề xuất A: Tăng N, chia L theo thứ hạng
- Giả thuyết: Có thể lấy thêm recall từ tài liệu ở đuôi danh sách, trong khi dành chunk dài hơn cho tài liệu có thứ hạng cao để hạn chế mất F2_chunk.
- Dựa trên bằng chứng nào trong brief: Recall doc của G là 0,322; phép thử BM25 cho thấy tăng N từ 30 lên 100 vẫn tăng recall, nhưng đó **không phải** bằng chứng định lượng cho precision biên của danh sách fused. F2_chunk tăng từ 0,0775 ở L=2.000 lên 0,2104 ở L=4.000.
- Cách làm cụ thể: Sau khi H có kết quả, giữ nguyên phân bổ ngôn ngữ của bản tốt hơn rồi thử N=120–150; điểm khởi đầu để kiểm byte là top 40 tài liệu L=4.000, phần còn lại L=2.000. Tạo đúng file nộp, nén bzip2 và đo dung lượng thực; chừa ít nhất 10% dưới mức 95 MB.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Chỉ đổi N/L so với bản tốt nhất; kiểm cả dung lượng lẫn LB. Bác bỏ nếu file vượt ngưỡng, P doc <0,15, hoặc F2_doc không tăng ít nhất 0,01 và điểm tổng không vượt bản gốc.
- Kỳ vọng: <+0,01–0,03 điểm tổng, ước lượng thô | Tự tin: vừa | Chi phí: S

### Đề xuất B: Tăng trọng số dense tiếng Việt
- Giả thuyết: Dense đang đóng góp nhiều tài liệu có ích hơn BM25 tiếng Việt; tăng trọng số có thể đưa các tài liệu dense tốt vào top-N mà không cần thêm lượt truy hồi.
- Dựa trên bằng chứng nào trong brief: Dense Việt có P@30 khoảng 0,38 so với 0,156 của BM25 Việt; độ trùng top-40 giữa hai lượt là 15%, cho thấy chúng không chỉ trả cùng một danh sách. Tuy vậy, hai con số precision này không đảm bảo dense cải thiện sau khi fusion.
- Cách làm cụ thể: Giữ N, ngôn ngữ, chunk và các lượt truy hồi khác cố định; trong nhóm Việt chỉ, thử trọng số dense gấp 2 BM25 trong RRF. Không đổi đồng thời số lượt top-k.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: So với cùng bản nền trên LB; bác bỏ nếu P doc xuống dưới 0,15 hoặc F2_doc/điểm tổng không tăng. RRF là phép gộp theo hạng, nên đây là thay đổi rẻ để kiểm trước reranker; bài gốc mô tả RRF là cách gộp các bảng xếp hạng: https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf
- Kỳ vọng: <0–0,01 điểm tổng | Tự tin: thấp–vừa | Chi phí: S

### Đề xuất C: Thêm vector phần sau cho tài liệu dài
- Giả thuyết: Vector chỉ từ 2.000 ký tự đầu làm rơi tài liệu đúng có thông tin liên quan ở phần sau; thêm một vector phần sau rồi lấy điểm cao nhất có thể tăng recall trước bước fusion.
- Dựa trên bằng chứng nào trong brief: Tài liệu Việt trung bình 3.553 ký tự nhưng chỉ biểu diễn 2.000 ký tự đầu; BGE-M3 được thiết kế cho nhiều độ hạt và hỗ trợ dense, multi-vector, sparse retrieval: https://arxiv.org/abs/2402.03216
- Cách làm cụ thể: Với tài liệu dài hơn 2.000 ký tự, mã hóa thêm một đoạn ở phần sau; dùng max(head, tail) làm điểm dense cho lượt tiếng Việt, giữ mọi bước còn lại cố định. Đây là thử nghiệm hai vector/tài liệu, chưa cần thay cả hệ bằng index chunk đầy đủ.
- Thí nghiệm kiểm chứng + tiêu chí bác bỏ: Nộp một bản so với nền tốt nhất. Bác bỏ nếu không tăng F2_doc ít nhất 0,01, P doc xuống dưới 0,15, hoặc thời gian mã hóa gây rủi ro cho lịch nộp.
- Kỳ vọng: <+0,005–0,02 điểm tổng | Tự tin: thấp | Chi phí: M

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief
- **Thứ tự ưu tiên đề xuất:** 1) chốt H và dùng phân bổ Việt/Trung tốt hơn, không dành quota cho Anh nếu kết quả H xác nhận; 2) tăng N với L theo thứ hạng và kiểm byte thật; 3) weighted RRF; 4) thêm vector phần sau; 5) reranker trên pool đã có. Reranker chỉ đổi thứ tự ứng viên hiện có, nên xếp sau các cách tăng recall ứng viên; model card chính thức mô tả bge-reranker-v2-m3 là reranker đa ngôn ngữ nhận cặp query–document để chấm điểm: https://huggingface.co/BAAI/bge-reranker-v2-m3
- Tôi sẽ **chưa ưu tiên HyDE/mở rộng truy vấn**: đội đã có các bản dịch Việt–Trung–Anh, còn HyDE cần sinh văn bản giả định và bài gốc lưu ý văn bản đó có thể chứa chi tiết sai; rủi ro và độ khó diễn giải cao hơn các ablation trên: https://arxiv.org/abs/2212.10496
- Chưa có phép đo recall nội bộ có nhãn, nên mọi ngưỡng tăng điểm phải được hiểu là **tiêu chí kiểm trên LB**, không phải kết luận thống kê chắc chắn. BM25 30→100 không đủ để khẳng định precision biên của danh sách fused.
- Kiểm tra dung lượng trên **toàn bộ file ZIP nộp sau nén**, không suy ra từ số ký tự hay kích thước JSON thô; phân bổ byte có thể lệch do tỷ lệ chữ Trung và độ nén khác nhau. Cần xác nhận giới hạn 95 MB áp vào thành phần nào của ZIP và tránh sát ngưỡng 100 MB.
- **Bài an toàn private:** giữ G (0,2207) làm fallback hiện tại; chỉ thay bằng H nếu H thực sự cao hơn, P doc ≥0,15 và file qua kiểm tra dung lượng. Không dùng 5 bài private để dò các hướng chưa thắng trên public. Cần xác nhận thể lệ tính điểm private dùng bài tốt nhất hay bài cuối.
- Theo ngày hiện tại 22/10/2026, hạn 31/10/2026 07:00 là khoảng 9 ngày lịch; brief ghi còn 8 ngày. Hãy xác nhận giờ hiện tại và múi giờ để lập lịch chính xác.

## 4. Nguồn đã tra cứu
- *BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation* — https://arxiv.org/abs/2402.03216 — hỗ trợ nhận định BGE-M3 được thiết kế cho dense, multi-vector và sparse retrieval, nhiều ngôn ngữ và độ hạt.
- *BAAI/bge-reranker-v2-m3 model card* — https://huggingface.co/BAAI/bge-reranker-v2-m3 — xác nhận đây là reranker đa ngôn ngữ chấm điểm query–document.
- *Reciprocal Rank Fusion outperforms Condorcet and Borda methods* — https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf — nguồn gốc phương pháp RRF.
- *Precise Zero-Shot Dense Retrieval without Relevance Labels* — https://arxiv.org/abs/2212.10496 — mô tả HyDE và rủi ro nội dung giả định sai.
