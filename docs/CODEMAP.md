# CODEMAP — bản đồ codebase
> Chạy /map để subagent code-mapper cập nhật tự động. Agent nên đọc file này thay vì đọc toàn bộ code.

## Tổng quan
Câu hỏi Việt → 9 lượt tìm theo ngôn ngữ (BM25 từ đơn + cặp âm tiết + BGE-M3) → RRF k=150 trong từng nhóm Việt/Trung/Anh → Qwen3-Reranker-4B chấm top 150 Việt + 50 Trung → cắt số tài liệu theo câu (TB 140) → 1 đoạn 4.000 ký tự/tài liệu → ZIP.

## Điểm vào & lệnh
`./build_submission.sh <tên> [mean=140] [vi-share=0.75] [weights]` — tạo bài nộp (mặc định = BEST 0,3606). `CAND=results/D_bi02.jsonl` bỏ bước gộp; `RERANK=0` bỏ reranker.

## Module
| Đường dẫn | Trách nhiệm | Phụ thuộc | Ghi chú |
|---|---|---|---|
| clean_corpus.py | SQLite HTML/XML (vibiomir_s3/) → clean/corpus/*.parquet | trafilatura, zstd | clean/parts = trung gian để chạy lại |
| embed_corpus.py | clean/corpus → emb/*.npy (BGE-M3, fp16) | sentence-transformers | chạy lại bỏ qua phần đã xong |
| translate_queries.py | câu hỏi → bản dịch Trung/Anh (Qwen3-8B, Ollama) | ollama | → results/queries_translated.jsonl (trong git) |
| search_docs.py | `RUNS` (8 lượt) → results/run_*.jsonl; `fuse()` RRF + hạn mức → results/D_*.jsonl | index/, emb/ | fuse chỉ gộp lượt có tên trong RUNS; `DEFAULT_WEIGHTS` = tốt nhất |
| qwen_rerank.py | D_*.jsonl → D_*_q3r4Bprr_all.jsonl: Qwen3-Reranker-4B chấm (câu hỏi, tiêu đề + đoạn khớp nhất), thứ tự theo P(yes) | transformers, make_submission (chunk_doc, chunk_cache) | cache results/qwen_rerank_cache_q3r4B_passage.pkl; --tokens-per-batch 12000 (24000 OOM) |
| dyn_cut.py | D_*.jsonl → DC_*.jsonl: số tài liệu theo câu (ngưỡng tau·top-1, dò tau theo --mean) | — | |
| make_submission.py | DC_*.jsonl → chunk + chọn đoạn (BGE-M3) → submissions/sub_*.zip | results/chunk_cache.pkl | tự kiểm định dạng; ZIP phải < 100 MB |
| scripts/crawl/ | find_missing.py, crawl_*.py: crawl bổ sung | curl_cffi, aiohttp | xong, chỉ tham khảo |
| tools/build_demo_data.py | file nộp (submissions/sub_prr_m140.zip) + clean/corpus → web/data/questions.json + q/<id>.json | pyarrow | thiếu file nộp → dự phòng D_bi02 (chưa rerank, không đoạn trích) |
| web/ | Web demo tĩnh (taste-skill): index.html + app/{search,upload,i18n,bm25}.js, pdf.js trong vendor/ | web/assets (kit, không vào git), web/data | chạy: `python -m http.server 8000 -d web` |

## Luồng dữ liệu
vibiomir_s3/ → clean/corpus → emb/ + index/bm25 → results/run_* → D_* → DC_* → submissions/

## Muốn sửa X thì vào đâu
- Trọng số / k RRF / hạn mức: search_docs.py (`DEFAULT_WEIGHTS`, `--rrf-k`, `--quota`)
- Số tài liệu mỗi câu, tỷ lệ Việt: dyn_cut.py (`--mean`, `--vi-share`)
- Reranker (mô hình, số ứng viên chấm, độ dài đoạn): qwen_rerank.py (`--model`, `--pool`, `--passage-chars`)
- Độ dài / số đoạn, nén: make_submission.py (`--chunk-chars`, `--compress`)

## Vùng nguy hiểm
- btc_data*/, vibiomir_s3/ (dữ liệu gốc) — được bảo vệ bởi hook
