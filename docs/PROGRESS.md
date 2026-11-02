# PROGRESS — cập nhật: 2026-10-27 12:00 bởi claude
> File này là "bộ nhớ" của dự án. Hook SessionStart tự nạp nó sau mỗi lần mở phiên / compact / clear.
> Giữ ngắn (< 80 dòng). Ghi đè thay vì viết thêm.

## Mục tiêu hiện tại
- Tăng điểm trước khi public đóng 31/10 23:59 GMT+7; chốt cấu hình cho private (01–04/11, chỉ 5 lượt TỔNG).

## Điểm tốt nhất
| Metric local | LB public | File nộp | Thí nghiệm | Ghi chú |
|---|---|---|---|---|
| — | **0,3606** | prr_m140 | exp-073 | `CAND=results/D_bi02.jsonl ./build_submission.sh best` (đã kiểm: khớp từng byte với bài nộp). BEST cuối vòng public |
| — | 0,3593 | id 7828 | exp-069 | Nền bi02 → `qwen_rerank.py --docs results/D_bi02.jsonl --pool 150,50 --quota 0,0 --model Qwen/Qwen3-Reranker-4B --text passage --passage-chars 1200 --tokens-per-batch 12000` (~6 giờ GPU; điểm lưu ở results/qwen_rerank_cache_q3r4B_passage.pkl) → `dyn_cut.py --docs results/D_bi02_q3r4Bprr_all.jsonl --mean 160 --vi-share 0.75 --lo 80 --hi 400` → `make_submission.py --chunk-chars 4000:400 --compress lzma-xl` |
| — | 0,3442 | bi02 | exp-057 | `./build_submission.sh best` (mặc định = cấu hình này: k=150, vi-share 0,75, TB 180, bm25bi_vi 0,2). Cần chỉ mục index/bm25/vi_bi: `python search_docs.py --runs bm25bi_vi` (~30 giây) |
| — | 0,3437 | id 7478 | exp-054 | `./build_submission.sh bi033 150 0.75 180 bm25bi_vi=0.33` — như 0,3427 + lượt BM25 cặp âm tiết (bm25bi_vi, chỉ mục index/bm25/vi_bi, dựng ~30 giây) trọng số 0,33 |
| — | 0,3427 | id 7280 | exp-049 | `./build_submission.sh k150vs75` (= `search_docs.py --only-fuse --quota 300,130,0 --rrf-k 150` → `dyn_cut.py --mean 180 --vi-share 0.75 --lo 80 --hi 400` → `make_submission.py --chunk-chars 4000:400 --compress lzma-xl`, 85 MB). k=200 cũng 0,3427. Danh sách ứng viên: `results/D_wide_son_k150.jsonl` (trong git) |
| — | 0,3400 | id 7270 | exp-046 | như trên, k=100, vi-share 0,7 |
| — | 0,3365 | id 7238 | exp-041 | k=60, vi-share 0,7 (`results/D_wide_son.jsonl`) |
| — | 0,3193 | id 7095 | exp-040 | D_wide trên máy Nguyen — kém D_wide_son cùng pipeline, chưa rõ vì sao (xem Vướng mắc) |

## Đang làm (03/11 — vòng private, hạn 04/11 23:59)
- Lượt private 1: sub_prr_m140 (0,3606 public). Lượt 2: **sub_ens_m140** (gộp Qwen3-Reranker-4B + 8B; bộ dò +0,0051 ≈ +0,0015 LB).
  Tái tạo: `CAND=results/D_bi02.jsonl RERANK=ens ./build_submission.sh ens_m140` (khớp từng byte).
- Tài liệu thuyết minh BTC (hạn 04/11 23:59): README.md + docs/thuyet_minh_loi_cuda.pdf xong; còn: chạy tools/pack_data.sh,
  tải ~/R2AI/drive_upload lên Google Drive, điền link (`python tools/make_thuyet_minh.py --drive <link>` + README),
  gộp nhánh son → main, mở quyền repo cho BTC.

## Đã xong (mới nhất ở trên, tối đa 10 dòng)
- 31/10 — dọn repo lần 2: xoá rerank.py (gộp interleave vào qwen_rerank), decompose_queries.py, lượt dsub/bm25bi_zh, ~2,4 GB;
  build_submission.sh = BEST 0,3606 (có reranker); git giữ D_bi02.jsonl + cache điểm reranker. Kiểm: dựng lại khớp từng byte.
- 27/10 — dọn repo: xoá code thí nghiệm bác bỏ (rerank, qwen_rerank, hyde, prf, embed_tail, chunk_quota, Qwen3-Embedding
  trong search_docs); crawl → scripts/crawl/; build_submission.sh = pipeline tốt nhất; xoá ~7 GB file thừa.
- 27/10 — RRF k: 60 → 0,3365 · 100 → 0,3400 · 150 = 200 → **0,3427** (bão hoà). vi-share 0,65 tệ, 0,75 tốt.
- 27/10 — dyn_cut TB 160 / 200 đều kém 180. Qwen3-Embedding nhóm Trung −0,0011 (bác bỏ, không mã hoá nhóm Việt).
- 27/10 — Qwen3-Reranker theo đoạn: chỉ +0,0004 so với baseline cùng tập (bác bỏ).
- 26/10 — dyn_cut (số tài liệu theo câu), chunk cho mọi tài liệu nhờ lzma-xl → 0,3193.

## Bước tiếp theo (1–3 việc, có lệnh chạy)
1. Nén + nộp exp-052/053:
   `for n in son_k150vs80 son_k150bm05; do python make_submission.py --docs results/DC_$n.jsonl --chunk-chars 4000:400 --compress lzma-xl --name sub_$n; done`
2. Cách đo không cần nhãn: số trúng = P × số mục; hai bài khác đúng một lát → độ chính xác biên của lát đó;
   giữ lát nếu > F2/5 (doc ~0,068 · chunk ~0,057). Xem bảng cuối docs/EXPERIMENTS.md.

## Vướng mắc / câu hỏi mở
- Vì sao D_wide (Nguyen, 0,3193) < D_wide_son (0,3365) cùng pipeline? Nghi: máy Nguyen còn file run_* của vimax/hyde/prf
  bị gộp với trọng số 1, hoặc thiếu ~15K tài liệu Việt. Cần Nguyen gửi danh sách results\run_*.jsonl + D_wide.jsonl.
- Máy Nguyen: E:\project_r2ai (btc_data_v2 → data\v2, vibiomir_s3 → crawl).
- Nộp qua Chrome extension: `PARTS=1 ./build_submission.sh …` chia ZIP phần ≤ 9 MB (mỗi file_upload 1 phần), ghép + kiểm SHA-256.
- Bộ chấm trả 7 số tổng hợp (FINAL, F2/P/R doc, F2/P/R chunk).

## Bẫy đã biết (đừng lặp lại)
- File > 100 MB → lỗi 413 (Cloudflare). lzma-xl ~0,35 MB/suất chunk.
- Luôn nộp baseline CÙNG tập ứng viên trước khi kết luận một thay đổi có lợi (exp-041 từng kết luận sai +0,0176).
- `--weights` ghi đè từng lượt lên `DEFAULT_WEIGHTS`; fuse() chỉ gộp lượt có tên trong `RUNS` (file run_* lạ bị bỏ qua).
- "BM25 Baseline" là tài khoản BTC. Thứ tự trong tập không đổi F2 doc — chỉ đổi tài liệu nào được kèm chunk.
