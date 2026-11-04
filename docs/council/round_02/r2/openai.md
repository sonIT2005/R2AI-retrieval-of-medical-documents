# M2 = openai (openai/gpt-6-luna) — vai: plan_critic — vòng 2

## 1. Nhận xét từng thành viên
- M1: Điểm mạnh là phát hiện sai khác A–G và nêu khả năng tách số tài liệu khỏi số chunk. | Lỗ hổng là suy ra số tài liệu đúng của từng ngôn ngữ từ precision tổng hợp, rồi đề xuất quota, trọng số và lịch chunk cụ thể chưa có kiểm chứng; nhiều thay đổi bị gộp trong cùng một bài. Trích dẫn về RRF không chứng minh cấu hình trọng số được đề xuất sẽ tốt hơn ở bài này.
- M2: Điểm mạnh là cảnh báo precision biên BM25 không đại diện cho precision biên của xếp hạng đã fusion, và yêu cầu đo kích thước file nén thật. | Lỗ hổng là đặt trọng số RRF trước các bước kiểm tra tính tái lập và độc lập giữa `relevant_docs`/`relevant_chunks`; đề xuất trước đây cũng chưa đưa ra phép thử trực tiếp cho chênh lệch A–G.
- M3: Điểm mạnh là chỉ ra reranker không thể cứu tài liệu ngoài candidate pool và chú ý điểm mù do chỉ mã hóa phần đầu tài liệu. | Lỗ hổng là phép thử trên top-500 chỉ cải thiện thứ tự trong pool, không chứng minh recall toàn corpus tăng; chi phí mã hóa và lợi ích dự kiến chưa được đo. BGE-M3 paper liên quan tới multi-vector, nhưng không đảm bảo mức tăng tương tự trên corpus này.
- M4: Điểm mạnh là đòi đo precision biên của danh sách fused trước khi quyết định tăng N, và tận dụng điểm chunk có thể đã tính sẵn. | Lỗ hổng là suy ra N từ P/R tổng hợp và giả định số nhãn trung bình trong công thức macro có thể gây sai; bài dò N=200 đồng thời đổi L cũng làm khó kết luận. Kết quả reranker tiếng Việt được trích dẫn là benchmark khác, chưa chứng minh lợi ích trên tác vụ này và cần xác minh điều kiện dùng.

## 2. Tôi đổi quan điểm thế nào (giữ / bỏ / sửa gì, vì sao)
Tôi giữ ý “đợi H và kiểm dung lượng thật” từ câu trả lời trước, nhưng đổi thứ tự: trước cả thử nghiệm mới, phải xác minh A–G có cùng danh sách tài liệu hay không. Nếu baseline không tái lập, so sánh LB sau đó không đáng tin. Tôi cũng sửa đề xuất tăng N: chỉ thử trên thứ hạng cố định và tách rõ danh sách tài liệu khỏi danh sách chunk nếu định dạng cho phép. Chưa ưu tiên reranker hay HyDE; reranker bị giới hạn bởi candidate pool, còn HyDE thêm nhiễu mà hiện chưa có kiểm chứng.

**Thứ tự ưu tiên sửa đổi (5 hướng; kiểm tra tính hợp lệ là bước chặn trước):**
1. **(f) Phân bổ Việt/Trung:** chờ H trước; dùng kết quả để tránh tốn bài thử quota đã gần được trả lời.
2. **(a) Tăng N:** thử với thứ hạng giữ nguyên, đồng thời giới hạn riêng số chunk để kiểm ngân sách byte.
3. **(b) Trọng số RRF:** thử một thay đổi trọng số đơn lẻ; rẻ hơn reranker nhưng chưa có bằng chứng về precision biên sau fusion.
4. **(d) Dense cấp chunk/max-sim:** ưu tiên sau các phép thử rẻ; có thể xử lý tài liệu bị điểm mù ở phần sau.
5. **(c) Reranker:** chỉ sau khi candidate pool và cách xếp hạng đã ổn định; reranker không khôi phục tài liệu không lọt vào pool. **(e) HyDE** tạm hoãn vì lợi ích chưa được chứng minh trong khi đã có các lượt truy vấn dịch.

## 3. Đề xuất cuối (tối đa 3)
### Đề xuất A: Khóa baseline trước khi tiêu lượt nộp
- **Giả thuyết:** Chênh lệch A–G có thể do đầu vào hoặc danh sách tài liệu thay đổi, khiến kết luận về L và các cải tiến sau bị nhiễu.
- **Cách làm cụ thể:** So sánh trực tiếp `relevant_docs` của A và G theo từng câu; ghi lại bản dịch, seed/cấu hình, thứ tự tie-break và hash đầu vào. Chạy lại cùng cấu hình hai lần. Kiểm tra H và đo kích thước chính xác của ZIP bzip2 trước khi nộp.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** Nếu hai lần dựng cùng cấu hình cho danh sách giống hệt nhau, A–G khác nhau chỉ ở chunk như dự kiến, và file nén nằm dưới ngưỡng an toàn, bác bỏ giả thuyết lỗi tái lập; nếu không, chưa dùng các so sánh LB để chọn pipeline.
- **Kỳ vọng:** +0 trực tiếp; tránh tối ưu nhầm baseline | Tự tin: cao | Chi phí: S

### Đề xuất B: Tách số tài liệu và số chunk trong phép thử tăng N
- **Giả thuyết:** Có thể tăng F2_doc bằng cách lấy thêm tài liệu trong khi giữ số chunk và dung lượng chunk gần như cố định. **Giả định:** định dạng/chấm điểm cho phép `relevant_chunks` là tập con của `relevant_docs`.
- **Cách làm cụ thể:** Xác minh giả định từ schema/hướng dẫn chấm; giữ nguyên xếp hạng tốt nhất, so sánh N_doc=100 với N_doc=150, còn N_chunk và quy tắc L giữ cố định. Nén file hoàn chỉnh và để dư biên dưới giới hạn 95 MB.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** Nộp một biến thể chỉ đổi N_doc. Bác bỏ nếu F2_doc không tăng ít nhất 0,01, P_doc xuống dưới 0,15, điểm tổng không tăng, hoặc file vượt ngưỡng. Nếu schema không cho tách hai danh sách, dừng hướng này thay vì suy đoán.
- **Kỳ vọng:** +0,01–0,03 điểm tổng, chưa chắc | Tự tin: vừa | Chi phí: S

### Đề xuất C: Dùng điểm chunk sẵn có để xếp hạng tài liệu trước cross-encoder
- **Giả thuyết:** Nếu bước chọn chunk hiện đã tính similarity cho các chunk của tài liệu ứng viên, lấy điểm tốt nhất theo tài liệu có thể cải thiện thứ tự trong pool với chi phí thấp hơn xây index chunk toàn corpus.
- **Cách làm cụ thể:** **Giả định:** điểm similarity theo chunk có thể lấy lại mà không mã hóa lại. Trên cùng candidate pool, N, quota ngôn ngữ và L, thay riêng điểm xếp hạng tài liệu bằng max-sim chunk; chỉ xem xét cross-encoder sau khi phép thử này cho thấy lợi ích.
- **Thí nghiệm kiểm chứng + tiêu chí bác bỏ:** So với cùng baseline trên LB. Bác bỏ nếu điểm tổng tăng dưới 0,01 hoặc P_doc dưới 0,15; khi đó không đầu tư mã hóa/index chunk toàn corpus chỉ dựa trên lập luận tài liệu dài.
- **Kỳ vọng:** +0–0,02 điểm tổng | Tự tin: thấp–vừa | Chi phí: S nếu điểm đã cache; nếu phải mã hóa lại thì M

## 4. Bình chọn
VOTES: M4-A, M4-B, M1-A
