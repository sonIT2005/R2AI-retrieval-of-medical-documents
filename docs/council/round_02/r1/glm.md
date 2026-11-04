# M4 = glm (z-ai/glm-5.3) — vai: simplifier — vòng 1

## 1. Chẩn đoán nhanh

- Đại số điểm: với P=T/N, R=T/G (G≈60 tài liệu đúng/câu), thì **F2_doc = 5T/(4G+N)** — điểm tài liệu chỉ phụ thuộc (T, N), thứ tự trong tập nộp vô nghĩa; mọi tài liệu nộp thêm đều pha loãng **cả** hạng mục doc lẫn chunk (giả sử 1 chunk/tài liệu). Chunk đã "tự giải" vì L=4.000 ≥ TB tài liệu Việt 3.553 ký tự (nộp ≈ cả tài liệu), tỷ lệ F2chunk/F2doc 0,91 của bạn ≈ 0,93–0,95 của #3/#4 → khoảng cách gần như toàn bộ ở **T**.
- Suy từ P/R của #3: họ nộp **N≈0,61×60/0,18 ≈ 200 tài liệu/câu** với P≈0,18 — bằng precision của bạn ở N≈111 → họ bắt được ~2× tài liệu đúng ở độ sâu tương tự. Đây là khoảng cách **chất lượng xếp hạng**, không phải kiến trúc.
- Ngưỡng "thêm tài liệu còn có lợi" của brief (F2/5≈0,046) **thiếu chính xác**: tính thêm pha loãng của hạng mục chunk, ngưỡng thực ≈ **0,06–0,07** (với h=LCS-hit 0,62 ở L=2.000, 0,35 ở L=1.000). Precision biên 0,068 của bm25_vi trùng đúng ngưỡng → "scan N lớn hơn" (plan 1) có thể gần như vô ích nếu không sửa xếp hạng trước. Thiếu số đo precision biên của xếp hạng **fused** — phải đo trước khi đặt lịch 8 ngày.
- Phức tạp vô dụng: 3 lượt tiếng Anh + quota 10% ngân sách dù nhãn ghi **0 tài liệu tiếng Anh**.
- Không có dev có nhãn → mỗi bài nộp là một thí nghiệm; mọi ý tưởng nên là post-processing trên bảng xếp hạng + embedding đã cache, kèm đo bzip2 local.

## 2. Đề xuất

### Đề xuất A: Xoá tiếng Anh + 3 bài nộp chẩn đoán (VI-only, ZH-only, dò độ sâu N=200)
- **Giả thuyết:** hệ đang đốt quota/lượt truy vấn vào phần vô dụng, và đang thiếu 2 số đo quyết định (đóng góp VI vs ZH, precision biên fused) — inexpensive và quyết định toàn bộ thứ tự ưu tiên còn lại.
- **Bằng chứng trong brief:** nhãn 0 tài liệu Anh; bảng chỉ có precision biên của bm25_vi thuần (0,068 dải 60→100), không có của fused; quota cố định 40/50/10 chưa từng được đo từng phần.
- **Cách làm:** khoá 3 lượt Anh (giữ index trên đĩa làm bảo hiểm). Trên bảng xếp hạng đã cache: (i) nộp VI-only 100 và ZH-only 100 → đọc R doc từng ngôn ngữ → quota ∝ đóng góp biên; (ii) nộp đúng xếp hạng fused như G nhưng N=200 với **L theo thứ hạng** (top-50 nguyên văn ≤4.000, 51–150 → 2.000, 151–200 → 1.000 ký tự; 50×4000+50×2000+100×1000 = 400k ký tự/câu ≈ same byte như G) → precision biên fused dải 111→200 = (T@200−T@111)/89.
- **Thí nghiệm + tiêu chí bác bỏ:** nếu dải biên fused ≥0,10 → độ sâu đáng giá, làm lưới N∈{150,200,250}; nếu ≤0,06 → **khoá độ sâu**, dồn toàn bộ cho Đề xuất C. Nếu R doc(ZH-only) <0,05 → cắt luôn các lượt Trung (bỏ plan dịch Qwen).
- **Kỳ vọng:** +0,01–0,03 trực tiếp (tái phân bổ quota), nhưng thông tin định hướng ≥0,05 | **Tự tin: cao** | **Chi phí: S** (≈0 GPU, chỉ tốn 3 slot nộp trong ~80 slot còn lại).

### Đề xuất B: Dùng lại embedding chunk của bước 5 làm tín hiệu xếp hạng tài liệu (max-sim vào RRF) — không build index mới
- **Giả thuyết:** vector dense cấp tài liệu chỉ thấy 2.000/3.553 ký tự đầu (≈56% tài liệu) → tài liệu có đoạn đúng ở nửa sau bị tụt hạng; max-sim theo chunk kéo chúng vào tập nộp.
- **Bằng chứng:** BGE-M3 hỗ trợ gốc multi-vector/ColBERT (late interaction) và input tới 8.192 token (không cần model mới); bước 5 đã tính cos chunk—theo—query cho ứng viên → tín hiệu gần như có sẵn, chỉ chưa được dùng để **xếp hạng tài liệu**.
- **Cách làm:** với top-300 fused mỗi câu, score(doc)=max cos(chunk, query) (dùng query cùng ngôn ngữ với doc), gộp RRF vào nhóm Việt/Trung. Cache embedding theo (doc, chunk) một lần (~2–5h GPU cho ~300 ứng viên × 1.200 câu), dùng lại cho mọi bài sau.
- **Thí nghiệm + tiêu chí bác bỏ:** 1 bài nộp giống G, chỉ đổi xếp hạng. Nếu |ΔR doc| < 0,015 (nhiễu LB trên 600 câu ≈ ±0,01) → đóng băng, không thêm lớp nào nữa.
- **Kỳ vọng:** +0,02–0,04 | **Tự tin: vừa** | **Chi phí: S–M**.

### Đ xuất C: Cross-encoder rerank top-200 (bge-reranker-v2-m3 / bản fine-tune tiếng Việt) — rồi mới tới lưới (N, L)
- **Giả thuyết:** T ở N cho trước là toàn bộ trận đấu; cross-encoder dồn tài liệu đúng lên top → cùng ngân sách byte nộp được N≈200 với P≈0,18 như #3.
- **Bằng chứng:** #3 có P doc 0,18 ≈ P của bạn nhưng T≈37 vs T≈19; trên retrieval tiếng Việt, reranker fine-tune từ bge-reranker-v2-m3 đạt acc@1 0,79 vs bi-encoder BGE-M3 0,57 (acc@10: 0,97 vs 0,89) — khoảng cách lớn; BAAI chính thức khuyến nghị cross-encoder để rerank top-k của embedding.
- **Cách làm:** rerank top-200 fused (~240k cặp, max_length 512, chạy đêm trên 5060 Ti ~3–6h, **cache điểm theo (câu, doc)** — chỉ tính lại khi xếp hạng đổi). Nộp top-120 (top-60 nguyên văn, đuôi 1.500) và bản N=200 (đuôi 1.000). **Dùng luôn điểm reranker để chọn vị trí chunk** (rerank top-3 chunk mỗi doc thay cos) — trả lời câu hỏi 2: L ngắn mà vẫn trúng nhờ localise tốt hơn.
- **Thí nghiệm + tiêu chí bác bỏ:** so T@120(reranked) với T@200(fused, từ bài dò ở A). Nếu R doc@120(reranked) ≤ R doc@200(fused) → cross-encoder không chuyển dịch sang y khoa Việt/Trung → khoá, trả lại thời gian cho quota + độ sâu.
- **Kỳ vọng:** +0,03–0,08 (R doc 0,32 → 0,42–0,50) | **Tự tin: vừa–cao** | **Chi phí: M**.

**Thứ tự cho câu hỏi 1:** C > B > (a) độ sâu sau-reranker > (b) trọng số RRF > (f) quota theo câu (A đo hộ) > (e) HyDE (để cùng). **Câu hỏi 2:** có, L theo thứ hạng; vị trí chunk tốt hơn = reranker (Đề xuất C). **Câu hỏi 3 (private):** bài private #1 = cấu hình tốt nhất **đã thắng trên public**, không đưa cấu kiện mới nào vào private; giữ ≥1 slot cho lỗi 413/định dạng (Cloudflare 100MB là ngưỡng cứng, không tăng được từ phía client); giữ G làm phương án an toàn.

## 3. Điểm đáng ngờ / thông tin còn thiếu trong brief

- **Không có precision biên của xếp hạng fused** — số quyết định xem độ sâu đáng giá hay không (Đề xuất A đo).
- **Format có cho phép `relevant_chunks` ⊂ `relevant_docs` không?** Nếu được, tài liệu đuôi nộp không kèm chunk chỉ pha loãng hạng mục doc (ngưỡng hạ từ ~0,06–0,07 xuống ~0,05, chi phí bytes ≈ 50B/tài liệu) — cần hỏi BTC FAQ; nếu được thì chiến lược (N, L) thay đổi hẳn.
- **0 tài liệu tiếng Anh** áp dụng cho cả 600 câu private? Nếu chỉ chắc cho public, giữ quota Anh bảo hiểm ~5% trong private.
- **Tỷ lệ crawl thất bại ngoài 1,6% "bẩn"**: mỗi URL không tải được là trần recall không thể vá bằng xếp hạng — brief không nêu; kiểm log và cài lại (chi phí CPU rẻ).
- Quy tắc F2/5 trong brief bỏ qua pha loãng chunk → có thể đang định hướng sai về độ sâu.
- **AITeamVN/Vietnamese_Reranker**: chưa kiểm được ngày phát hành/giấy phép (không còn lượt tìm kiếm) — phải xác nhận ≤15B và phát hành trước 01/08/2026 trước khi dùng cho bài dự thi; nếu không达标 thì dùng bge-reranker-v2-m3 gốc.
- Nhiễu LB ≈ ±0,01 trên 600 câu macro → đừng đốt slot cho các biến < 0,01 (ví dụ vi chỉnh trọng số RRF).

## 4. Nguồn đã tra cứu

- Cloudflare — lỗi 413 & giới hạn upload theo plan (Free/Pro = 100MB, tăng bằng plan/grey-cloud phía server) — https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/ — chứng minh 413 là ngưỡng cứng 100MB, không thể "đấu" từ client → phải nén/tách.
- Cloudflare Workers — request body size limits — https://developers.cloudflare.com/workers/platform/limits/ — xác nhận lại 100MB Free/Pro.
- BGE-M3 (M3-Embedding, arXiv) — hỗ trợ input tới 8.192 token và 3 chế độ dense/sparse/multi-vector (ColBERT) — https://arxiv.org/html/2402.03216v3 — nền cho Đề xuất B (max-sim late-interaction là chức năng gốc của model đang dùng) và cho thấy 512-token/2.000-ký tự là lựa chọn tự thu gọn, không phải giới hạn model.
- BAAI/bge-m3 (Hugging Face) — bảng model: sequence length 8192 — https://huggingface.co/BAAI/bge-m3 .
- BAAI/bge-reranker-v2-m3 (Hugging Face) — reranker đa ngôn ngữ "lightweight, easy to deploy", khuyến nghị cho ngữ cảnh multilingual, ví dụ dùng max_length 512 — https://huggingface.co/BAAI/bge-reranker-v2-m3 — cơ sở cho Đề xuất C.
- BAAI model page (model.baai.ac.cn) — pattern chuẩn "retrieve top-100 bằng embedding → cross-encoder rerank top-k" — https://model.baai.ac.cn/model-detail/100112 .
- AITeamVN/Vietnamese_Reranker — fine-tune tiếng Việt của bge-reranker-v2-m3 (1,1M triplet), acc@1 0,79 vs BGE-M3 0,57 trên retrieval tiếng Việt — https://huggingface.co/AITeamVN/Vietnamese_Reranker — bằng chứng chênh lệch bi-encoder vs cross-encoder trên tiếng Việt (cần kiểm ngày phát hành/giấy phép trước khi dùng).
- Không tra cứu được (đã hết lượt tìm kiếm): write-up giải thưởng Kaggle/RAG championship và việc định danh chính xác leaderboard này.
