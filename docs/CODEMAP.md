# CODEMAP — bản đồ codebase
> Chạy /map để subagent code-mapper cập nhật tự động. Agent nên đọc file này thay vì đọc toàn bộ code.

## Tổng quan
Câu hỏi Việt → 8 lượt tìm theo ngôn ngữ (BM25 + BGE-M3) → RRF trong từng nhóm Việt/Trung/Anh → cắt số tài liệu theo câu → 1 đoạn/tài liệu → ZIP.

## Điểm vào & lệnh
`./build_submission.sh <tên> [k=150] [vi-share=0.75] [mean=180] [weights]` — tạo bài nộp từ results/run_*.jsonl có sẵn.

## Module
| Đường dẫn | Trách nhiệm | Phụ thuộc | Ghi chú |
|---|---|---|---|
| clean_corpus.py | SQLite HTML/XML (vibiomir_s3/) → clean/corpus/*.parquet | trafilatura, zstd | clean/parts = trung gian để chạy lại |
| embed_corpus.py | clean/corpus → emb/*.npy (BGE-M3, fp16) | sentence-transformers | chạy lại bỏ qua phần đã xong |
| translate_queries.py | câu hỏi → bản dịch Trung/Anh (Qwen3-8B, Ollama) | ollama | → results/queries_translated.jsonl (trong git) |
| search_docs.py | `RUNS` (8 lượt) → results/run_*.jsonl; `fuse()` RRF + hạn mức → results/D_*.jsonl | index/, emb/ | fuse chỉ gộp lượt có tên trong RUNS; `DEFAULT_WEIGHTS` = tốt nhất |
| dyn_cut.py | D_*.jsonl → DC_*.jsonl: số tài liệu theo câu (ngưỡng tau·top-1, dò tau theo --mean) | — | |
| make_submission.py | DC_*.jsonl → chunk + chọn đoạn (BGE-M3) → submissions/sub_*.zip | results/chunk_cache.pkl | tự kiểm định dạng; ZIP phải < 100 MB |
| scripts/crawl/ | find_missing.py, crawl_*.py: crawl bổ sung | curl_cffi, aiohttp | xong, chỉ tham khảo |

## Luồng dữ liệu
vibiomir_s3/ → clean/corpus → emb/ + index/bm25 → results/run_* → D_* → DC_* → submissions/

## Muốn sửa X thì vào đâu
- Trọng số / k RRF / hạn mức: search_docs.py (`DEFAULT_WEIGHTS`, `--rrf-k`, `--quota`)
- Số tài liệu mỗi câu, tỷ lệ Việt: dyn_cut.py (`--mean`, `--vi-share`)
- Độ dài / số đoạn, nén: make_submission.py (`--chunk-chars`, `--compress`)

## Vùng nguy hiểm
- btc_data*/, vibiomir_s3/ (dữ liệu gốc) — được bảo vệ bởi hook
