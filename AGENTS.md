# AGENTS.md — Luật chung cho MỌI AI agent trong repo này
> Claude Code đọc file này qua CLAUDE.md. Antigravity / Codex / Cursor / Gemini… cũng phải đọc file này TRƯỚC khi làm.

## 0. Nguồn sự thật (đọc trước khi làm bất cứ gì)
1. `docs/PROGRESS.md` — đang ở đâu, làm dở gì, bước tiếp theo
2. `docs/PLAN.md` — backlog đã xếp hạng (mục đầu tiên = việc tiếp theo)
3. `docs/CODEMAP.md` — file nào làm gì (đọc cái này thay vì đọc cả codebase)
4. `docs/EXPERIMENTS.md` — đã thử gì, kết quả ra sao (không lặp lại)

## 1. Bài toán
- Cuộc thi: R2AI2026 Truy hồi tài liệu y khoa đa ngôn ngữ (ViBioMIR) — https://leaderboard.aiguru.com.vn/competitions/15
  1.200 câu hỏi tiếng Việt → danh sách `relevant_docs` (id trong `links_corpus_vi_en_zh.parquet`, 1,19M URL:
  714k Việt, 240k Trung, 240k PubMed Anh) + `relevant_chunks` (doc_id + chunk_text trích NGUYÊN VĂN từ tài liệu).
- Metric: càng cao càng tốt. Điểm = trung bình (F2 tài liệu, F2 chunk); F2 = 5PR/(4P+R), tính từng câu rồi macro-average.
  Chunk đúng nếu overlap(c,g) = LCS_token(c,g) / max(|c|, |g|) ≥ 0,4 với ít nhất 1 chunk tham chiếu g cùng câu + cùng doc_id
  (chuẩn hoá NFKC, giải mã HTML entity, chữ thường, gộp khoảng trắng) — theo mục "Phương pháp đánh giá" trên trang thi
  (người dùng gửi 30/10). Trước 30/10 tài liệu đội ghi nhầm "/|g|". Chia cho max → chunk nộp QUÁ DÀI so với g bị phạt
  (cần |c| ≤ 2,5·|g|). Độ dài 4.000 ký tự hiện tại được chọn theo điểm LB thật nên vẫn đúng với bộ chấm.
  Chunk P = số chunk nộp đúng / số chunk nộp; chunk R = số chunk tham chiếu được tìm thấy / tổng chunk tham chiếu.
- Hạn nộp: public đến 31/10/2026 23:59 GMT+7 (người dùng xác nhận 29/10); private 01–04/11/2026; 23:59 GMT+7.
  Ràng buộc: 10 bài/ngày; private chỉ 5 bài TỔNG; ZIP chứa đúng 1 file .json; phải có working-notes paper.
- Luật cứng: chỉ model mở ≤15B, phát hành trước 01/08/2026 (không GPT/Gemini… trong pipeline). Dữ liệu ngoài phải
  trích nguồn. Cấm dò đáp án: `details.jsonl` chỉ dùng phân tích tổng quát, không ghi nhớ đáp án từng câu.
- Tài nguyên: RTX 5060 Ti 16GB, 32 luồng CPU, 29GB RAM. Dữ liệu (~75GB) KHÔNG nằm trong repo (xem README).
- Lệnh chuẩn (chạy từ gốc repo; làm sạch: conda base Py3.14; còn lại: conda env `vibiomir` Py3.11):
  - Làm sạch: `python clean_corpus.py` · Vector: `python embed_corpus.py` · Dịch: `python translate_queries.py`
  - Tìm (8 lượt → results/run_*.jsonl): `python search_docs.py --quota 300,130,0 --rrf-k 150` (`--only-fuse` chỉ gộp lại, vài giây)
  - Tạo file nộp (gộp → dyn_cut → make_submission, mặc định = bài tốt nhất): `./build_submission.sh <tên> [k] [vi-share] [mean] [weights]`
  - **Eval chuẩn**: CHƯA có eval local (không có nhãn) → thước đo duy nhất là LB public (600 câu).
- Nhiễu đã đo: chưa đo. LB public chấm 600/1.200 câu.

### Hợp đồng eval (bắt buộc, làm đầu tiên)
- Split cố định lưu ở `data/splits/` (không sinh lại), seed cố định.
- Mỗi lần eval ghi ra `results/<run>/metrics.json` (metric chính + metric phụ + theo từng lớp)
  và `results/<run>/predictions.csv` (id, y_true, y_pred, score/prob, + cột meta hữu ích: độ dài, nguồn…).
- Không có predictions từng mẫu thì KHÔNG thể tìm nguyên nhân lỗi → không được bỏ qua.
- Khi eval đã chốt: bật dòng `eval/**` trong `.claude/protected_paths.txt`.

## 2. Phạm vi sửa code (quan trọng nhất)
- Trước khi sửa, ghi rõ: **"Sẽ sửa: file1, file2 — lý do"**. Mặc định ≤ 3 file mỗi bước.
- Chỉ sửa đúng những file đã nêu. Cần thêm file → DỪNG, nói lý do, chờ đồng ý.
- Không refactor, đổi tên, format lại, "dọn dẹp" ngoài yêu cầu. Không xoá code/comment không liên quan.
- Không đụng đường dẫn được bảo vệ (`.claude/protected_paths.txt`): dữ liệu gốc, eval đã chốt, split, file `.env`.
- Ưu tiên diff nhỏ nhất làm được việc.

## 3. Quy trình thí nghiệm
- Mỗi thí nghiệm thay đổi MỘT thứ. Viết giả thuyết + tiêu chí bác bỏ TRƯỚC khi chạy.
- Luôn so bằng lệnh eval chuẩn, cùng split, cùng seed. Chênh lệch nhỏ hơn nhiễu giữa các seed = "không kết luận".
- Kết quả tốt bất thường → nghi leakage/bug trước khi tin.
- Không cải thiện → KHÔNG đổi hyperparameter mò mẫm. Phân tích lỗi từ `predictions.csv` (nhóm lỗi, đếm, xem ví dụ), rồi đặt giả thuyết dựa trên bằng chứng.
- 3 thí nghiệm liên tiếp không cải thiện → dừng, đề xuất phân tích lỗi + hội đồng model hoặc tranh luận giả thuyết.
- Ghi MỌI thí nghiệm (kể cả thất bại) vào `docs/EXPERIMENTS.md`.

## 4. Theo dõi tiến độ
- Xong mỗi bước: cập nhật `docs/PROGRESS.md` (Đang làm / Đã xong / Bước tiếp theo). Ngắn, ghi đè — không viết dài thêm.
- Mỗi bước chạy được: git commit nhỏ, message dạng `[exp-012] thêm focal loss` hoặc `[web] trang đăng nhập`.
- Không commit: data lớn, checkpoint, `.env`, `node_modules`.

## 5. Codebase lớn
- Dùng `docs/CODEMAP.md` để định vị. Chỉ mở file cần thiết; tìm bằng grep thay vì đọc toàn bộ.
- Thêm/đổi module → cập nhật CODEMAP.md (1–2 dòng).

## 6. Giao tiếp
- Trả lời bằng tiếng Việt, ngắn gọn. Kết thúc mỗi bước bằng: đã làm gì → kết quả → bước tiếp theo.
- Không chắc → hỏi 1 câu cụ thể thay vì đoán.
- Bị hook chặn → không tìm cách lách, báo người dùng.
