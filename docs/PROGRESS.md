# PROGRESS — cập nhật: 2026-10-26 10:30 bởi claude
> File này là "bộ nhớ" của dự án. Hook SessionStart tự nạp nó sau mỗi lần mở phiên / compact / clear.
> Giữ ngắn (< 80 dòng). Ghi đè thay vì viết thêm.

## Mục tiêu hiện tại
- Vào top 6 (> 0,311) rồi top 5 (> 0,32) trước khi public đóng 31/10 23:59 GMT+7 (theo trang thi; phase 44 hết 16:59Z).

## Điểm tốt nhất
| Metric local | LB public | File nộp | Thí nghiệm | Ghi chú |
|---|---|---|---|---|
| — | **0,3193** | id 7095 | exp-040 | `dyn_cut.py --docs results/D_wide.jsonl --mean 180 --vi-share 0.7 --lo 80 --hi 400` → `make_submission.py --chunk-chars 4000:400 --compress lzma-xl` (chunk cho mọi tài liệu, 83,8 MB) |
| — | 0,3182 | id 7088 | exp-038 | như trên, TB 200 |
| — | 0,2968 (đang hiện trên bảng) | id 6760 | exp-019 | đổi bài hiển thị: hỏi người dùng trước |

## Đang làm (26/10)
- Đã nộp 26/10 đủ 10/10: S1, S2, S3, B1, H1, B2, C1, D1, E1, D2. Lượt mới mở 00:00 GMT+7.
- Hướng tiếp theo cho dyn_cut: thử TB 160 (vẫn tăng khi giảm?) và đổi tỉ lệ Việt/Trung; D2 còn ~11 MB trống.
- Đang chạy nền: `qwen_rerank.py --docs results/D_wide.jsonl --pool 250,100 --quota 140,60 --limit 600` (Qwen3-Reranker-4B,
  ~11 cặp/giây, ~6 giờ, log logs/qwen_rr_600.log) → results/D_wide_q3rr_140-60.jsonl, D_wide_q3rrf_140-60.jsonl.
  Chỉ 600 câu đầu được chấm (còn lại giữ thứ tự cũ) → hiệu ứng trên LB ≈ một nửa nếu tập public ngẫu nhiên.

## Đã xong (mới nhất ở trên, tối đa 10 dòng)
- 26/10 — số tài liệu: 150 → F2doc 0,3364 · 200 → **0,3387** · 250 → 0,3328 (đỉnh ≈ 200)
- 26/10 — HyDE (hyde.py, Qwen3-8B) → tệ hơn (−0,003); cửa sổ đầu bài (`--window head`) → tệ hơn (−0,0006)
- 26/10 — lzma-xl: nén 88 → 54 MB cùng bài → chunk cho nhiều tài liệu hơn: chunk Việt 86–135 +0,0066 (0,3084)
- 24/10 — 250 tài liệu (0,3018); chunk_quota 85/15; bm25_vi 0,33; chunk 4.000 ký tự

## Bước tiếp theo (1–3 việc, có lệnh chạy)
1. Đọc điểm C1/D1. Cấu hình tốt hơn → dùng làm nền cho reranker.
2. Khi reranker xong: chunk cho tất cả trên D_wide_q3rrf_140-60 (`make_submission.py --docs ... --chunk-chars 4000:200
   --compress lzma-xl`), so với C1. Nếu thắng → chấm nốt 600 câu còn lại (bỏ --limit, cache giữ phần đã chấm).
3. Cách đo không cần nhãn: số trúng = P × số mục; hai bài khác đúng một lát → độ chính xác biên của lát đó;
   giữ lát nếu > F2/5 (doc ~0,068 · chunk ~0,057). Xem bảng cuối docs/EXPERIMENTS.md.

## Vướng mắc / câu hỏi mở
- Dự án ở **E:\project_r2ai** (btc_data_v2 → E:\project_r2ai\data\v2, vibiomir_s3 → E:\project_r2ai\crawl).
- Nộp bài: Chrome extension, chia ZIP phần ≤ 9 MB (mỗi file_upload 1 phần — gộp nhiều phần trong browser_batch bị từ chối),
  ô tải phụ `document.body.prepend` rồi read_page depth 1 lấy ref (công cụ find hay bị giới hạn), ghép + kiểm SHA-256
  trên trang, mỗi bài một tab mới.
- Bộ chấm chỉ trả 7 số tổng hợp (FINAL, F2/P/R doc, F2/P/R chunk) — không có chi tiết từng câu.

## Thay đổi 26/10 (Sơn) — đọc trước khi chạy lệnh cũ
- `search_docs.py`: `DEFAULT_WEIGHTS` = cấu hình tốt nhất (bm25_vi=0.33, bm25_zh=0.3, bm25_en=0) và **tắt** vimax/prf/hyde.
  `--weights` giờ **ghi đè từng lượt lên mặc định** (trước đây thay thế toàn bộ → lượt không ghi bị về 1).
  Lệnh cũ có ghi đủ mọi lượt → kết quả không đổi; lệnh cũ bỏ sót lượt nào → lượt đó giờ lấy mặc định thay vì 1.
- `qwen_rerank.py`: thêm `--model`, `--text passage` (đoạn khớp nhất), `--quota 0,0` (giữ hết, để dyn_cut cắt);
  bản `*rrf` nay ghi `scores` = điểm RRF (trước ghi điểm reranker → dyn_cut cắt sai thang). Cache 4B + head giữ nguyên.
- `build_submission.sh`: tự chọn Python (PY / venv Windows / venv Linux / python đang kích hoạt); tham số 7 = chunk-chars (mặc định 4000:400).
- Hướng dẫn tái tạo bài 0,3193: `docs/HUONG_DAN_TAI_TAO_BEST.md` (việc của Nguyen).

## Bẫy đã biết (đừng lặp lại)
- File > 100 MB → lỗi 413 (Cloudflare). lzma-xl ~0,35 MB/suất chunk; chunk cho cả 250 tài liệu = 106 MB (quá).
- fuse() gộp MỌI results/run_*.jsonl với trọng số 1 → luôn đặt =0 cho lượt không dùng (prf, hyde, vimax).
- GPU 16 GB: reranker 4B + một tiến trình BGE-M3 → tràn VRAM, chậm 5–60×. make_submission giờ nhả GPU trước khi nén.
- "BM25 Baseline" là tài khoản BTC. Thứ tự trong tập không đổi F2 doc — chỉ đổi tài liệu nào được kèm chunk.
