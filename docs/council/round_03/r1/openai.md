# M2 = openai (openai/gpt-6-luna) — vai: plan_critic — vòng 1

## 1. Chẩn đoán nhanh
Nút thắt chính là **xếp hạng tài liệu**, không phải chunk: precision doc chỉ 0,157 và F2_doc tăng khi giảm K từ 400 xuống 250. K cố định có vẻ không hợp với độ biến thiên lớn của số tài liệu liên quan giữa các câu, nên adaptive K là giả thuyết đáng thử nhất. Nhưng 45 lần nộp đã làm tăng rủi ro tối ưu quá tay theo public LB; dữ liệu hiện có chưa đủ cơ sở để kỳ vọng chắc chắn bước nhảy +0,05.

## 2. Đề xuất (tối đa 3, xếp theo kỳ vọng/chi phí)
### Đề xuất A: K thích ứng theo đường cong RRF
- **Giả thuyết:** Cắt ít hơn ở câu có tín hiệu liên quan còn mạnh ở hạng sâu, cắt nhiều hơn khi điểm RRF rơi nhanh sẽ tận dụng việc K=250 tốt hơn K=300–400.
- **Dựa trên bằng chứng nào trong brief:** F2_doc tăng từ khoảng 0,302 ở 400 tài liệu lên 0,333 ở 250; |G| dao động 5–190, nhưng hiện mỗi câu đều trả cùng số tài liệu.
- **Cách làm cụ thể:** Lấy tối đa 400 ứng viên như hiện tại. Dùng **điểm RRF tương đối so với top-1** để tìm điểm cắt; chặn K trong [100, 400]. Chạy hai chính sách đã định trước: ngưỡng tương đối theo RRF, và điểm gãy của đường điểm RRF. Chọn ngưỡng trên toàn bộ câu hỏi sao cho K trung bình gần 250, rồi giữ nguyên; không dò nhiều ngưỡng bằng LB.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** Nộp hai biến thể trên, so với baseline 250 đã có. Bác bỏ nếu cả hai không vượt 0,3018, hoặc F2_doc tăng nhưng điểm tổng giảm do chunk. Chỉ số phụ cần ghi lại: phân bố K, điểm RRF ở cutoff, và số retriever cùng hỗ trợ các tài liệu được giữ.
- **Kỳ vọng:** +0,005–0,02 F2 tổng *(ước lượng, không phải bảo đảm; +0,05 vẫn khó)* | **Tự tin:** vừa | **Chi phí:** S

### Đề xuất B: Thử sparse của BGE-M3 trước khi đổi embedding
- **Giả thuyết:** BGE-M3 sparse có thể bổ sung tín hiệu từ thuật ngữ y khoa mà BM25 âm tiết và dense hiện tại chưa xếp cao; thử nhánh bổ sung ít rủi ro hơn thay toàn bộ retriever.
- **Dựa trên bằng chứng nào trong brief:** BM25 thuần có precision thấp; reranker BGE hiện tại đã làm điểm giảm, nên chưa có lý do ưu tiên thêm reranking. BGE-M3 được thiết kế để hỗ trợ đồng thời dense, sparse và multi-vector—đây là khả năng bổ sung chưa thấy được khai thác trong brief (https://arxiv.org/abs/2402.03216).
- **Cách làm cụ thể:** Trước tiên tạo chỉ mục sparse BGE-M3 cho đúng phần đầu tài liệu đang dùng; thêm một danh sách top-300 tiếng Việt vào RRF hiện tại với trọng số nhỏ, giữ nguyên K=250 và chunk. **Chưa** thử ColBERT cùng lúc để biết riêng sparse có ích không.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** Một bài public so với baseline hiện tại. Bác bỏ nếu F2_doc không tăng, hoặc F2 tổng giảm. Trước khi nộp, xác nhận chỉ mục chạy được trong RAM và pipeline nộp không đổi thứ tự/ID tài liệu.
- **Kỳ vọng:** +0,005–0,02 F2 tổng *(ước lượng)* | **Tự tin:** thấp–vừa | **Chi phí:** M

### Đề xuất C: Tăng số tài liệu có chunk từ 100 lên 120
- **Giả thuyết:** Có thể tăng F2_chunk bằng cách trả chunk cho thêm tài liệu trong danh sách đã xếp hạng mà không thay retriever.
- **Dựa trên bằng chứng nào trong brief:** Chunk hiện chỉ tạo cho 100 tài liệu đầu; F2_chunk 0,2709 thấp hơn F2_doc 0,3328. Đây là thay đổi tách biệt, rẻ và dễ kiểm chứng.
- **Cách làm cụ thể:** Giữ nguyên danh sách doc 250 và cách chọn/mở rộng chunk; tăng đúng 100 → 120, giữ tỷ lệ Việt/Trung gần 85/15.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** Nộp một biến thể; kiểm tra kích thước **sau đúng bước nén/đóng gói được chấp nhận**. Bác bỏ nếu F2_chunk không tăng hoặc điểm tổng giảm.
- **Kỳ vọng:** +0,002–0,01 F2 tổng *(ước lượng; trần tăng có thể thấp)* | **Tự tin:** vừa | **Chi phí:** S

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief
- **Xếp hạng lại 5 hướng (từ nên làm trước đến sau):** **1) (b) K thích ứng** — trực tiếp nhắm vào xu hướng K=250 tốt hơn K lớn; **2) (a) embedding/sparse** — thử BGE-M3 sparse trước, chưa làm ColBERT/Qwen 4B–8B; **3) (e) tăng chunk** — rẻ nhưng chỉ tác động một nửa metric; **4) (d) mở rộng truy vấn** — rẻ nhưng từ khóa/HyDE có thể kéo thêm nhiễu; **5) (c) reranker** — ưu tiên thấp vì reranker BGE đã làm giảm điểm. Qwen3-Embedding có báo cáo kết quả tốt trên benchmark multilingual, nhưng điều đó không chứng minh sẽ cải thiện truy hồi cho corpus/metric này; nếu thử thì bắt đầu ở 0.6B, không phải 4B/8B (https://arxiv.org/abs/2506.05176).
- **Tín hiệu cho K:** Tôi sẽ thử trước **độ rơi tương đối của điểm RRF theo hạng**, rồi đối chiếu với **số retriever cùng ủng hộ**. Không có nhãn dev thì không thể xác nhận tín hiệu nào dự đoán |G| tốt nhất; vì vậy chỉ nên thử hai chính sách đã chốt trước và không dò ngưỡng qua nhiều lần nộp. Nếu hai chính sách cho kết quả trái chiều hoặc không hơn baseline, dừng thay vì tiếp tục tối ưu public.
- **Vì sao vector phần sau tài liệu có thể làm tệ:** Có thể phần sau chứa ít thông tin khớp câu hỏi hơn, hoặc nhiễu/độ dài làm thay đổi thứ hạng; việc đó **không chứng minh** nhãn được tạo từ phần đầu. Nhãn có thể đơn giản ưu tiên extractive evidence đầu bài, nhưng brief không xác nhận cách tạo nhãn. Do thử cửa sổ sau đã giảm điểm, tôi sẽ giữ phần đầu làm tín hiệu chính, không đầu tư thêm vào late-window trong 6 ngày còn lại.
- **Năm bài private:** Không dùng private để dò tham số. Chỉ đưa vào private các biến thể đã qua public: (1) baseline 0,3018; (2) biến thể adaptive K tốt nhất; (3) sparse + retriever tốt nhất; (4) tăng chunk nếu đã tăng điểm tổng; (5) tổ hợp hai thay đổi chỉ khi tổ hợp đó đã được kiểm tra public. Nếu một hướng không thắng public, không dành một bài private để “hy vọng”. Hãy xác nhận luật chọn kết quả cuối có lấy điểm cao nhất trong 5 bài hay cách khác.
- **Thông tin còn thiếu:** Tên/link cuộc thi và luật chọn private; số tài liệu trung bình thực tế được giữ bởi từng chính sách K; độ dài/định dạng giới hạn cho từng chunk; và liệu có thể kiểm tra sai khác dự đoán theo từng câu hay chỉ nhận điểm tổng. Không có tên cuộc thi nên không thể xác định đáng tin cậy các đội 0,40+ đang dùng gì hoặc tìm write-up cụ thể của họ.

## 4. Nguồn đã tra cứu
- *BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation* — https://arxiv.org/abs/2402.03216 — xác nhận BGE-M3 hỗ trợ dense, sparse và multi-vector; không chứng minh sparse sẽ tăng điểm ở bài này.
- *Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models* — https://arxiv.org/abs/2506.05176 — mô tả các cỡ Qwen3-Embedding/Reranker và kết quả multilingual tổng quát; không bảo đảm hiệu quả với corpus này.
- *Qwen3-Reranker-0.6B model card* — https://huggingface.co/Qwen/Qwen3-Reranker-0.6B — xác nhận model card và checkpoint của reranker 0.6B; không có đánh giá trên cuộc thi này.
- *Bias and the Limits of Pooling for Large Collections* — https://www.nist.gov/publications/bias-and-limits-pooling-large-collections — nêu một giới hạn chung của đánh giá khi nhãn được tạo bằng pooling; không cho biết nhãn của cuộc thi này được tạo theo cách đó.
