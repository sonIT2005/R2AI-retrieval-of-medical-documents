# R2AI 2026 · ViBioMIR — đội loi_cuda

Truy hồi thông tin y sinh **xuyên ngôn ngữ**: câu hỏi tiếng Việt → tìm **tài liệu** (`doc_id`) và **đoạn nội dung** (chunk) liên quan trong corpus Việt – Trung – Anh.
Chấm điểm: F2 (coi trọng Recall) ở cấp tài liệu và cấp chunk, trung bình theo câu hỏi; điểm cuối = trung bình hai F2.

## Dữ liệu (không có trong repo)

Mọi script chạy từ thư mục gốc của repo và cần các thư mục sau:

| Thư mục | Nội dung | Cách lấy |
|---|---|---|
| `btc_data_v2/` | Danh sách corpus chính thức 1.220.598 URL + 1.200 câu hỏi | `hf download AIGuruTinix/ViBioMIR links_corpus_vi_en_zh.parquet query.parquet --repo-type dataset --local-dir btc_data_v2` |
| `vibiomir_s3/` | HTML/XML đã crawl (SQLite nén zstd, ~64GB) | `hf download snute/ai_guru-S3 --repo-type dataset --local-dir vibiomir_s3` |
| `clean/`, `emb/`, `index/`, `results/`, `submissions/` | Sinh ra bởi các bước bên dưới | — |

## Môi trường

```bash
# Làm sạch (conda base, Python 3.14)
pip install -r requirements-clean.txt

# Embedding / tìm kiếm / nộp bài (GPU)
conda create -n vibiomir python=3.11 -y && conda activate vibiomir
pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements-search.txt

# LLM dịch câu hỏi
ollama pull qwen3:8b
```

## Quy trình

| # | Lệnh | Việc | Thời gian* |
|---|---|---|---|
| 1 | `python clean_corpus.py` | HTML/XML → văn bản sạch, chỉ giữ id thuộc corpus BTC → `clean/corpus/` | ~1h20 lần đầu, chạy lại chỉ xử lý file SQLite mới |
| 2 | `python embed_corpus.py` | BGE-M3, 1 vector/tài liệu → `emb/` | ~3h cho 1,2M tài liệu, chạy lại dùng lại vector cũ |
| 3 | `python translate_queries.py` | Qwen3-8B dịch câu hỏi sang Trung + Anh → `results/queries_translated.jsonl` | ~1,5h |
| 4 | `python search_docs.py --quota 60,40,0` | 8 lượt tìm (BM25 + dense, theo từng ngôn ngữ) → gộp RRF có trọng số theo ngôn ngữ, ghép theo hạn mức Việt,Trung,Anh | ~15 phút; `--only-fuse` chỉ vài giây |
| 5 | `python make_submission.py --docs results/docs_fused_60-40-0.jsonl` | Cắt chunk + chọn đoạn khớp nhất mỗi tài liệu → `submissions/*.zip` | vài phút đến ~30 phút (có bộ nhớ đệm) |

\* trên RTX 5060 Ti 16GB, 32 luồng CPU, 29GB RAM. Mọi bước dừng bằng `Ctrl+C` và chạy lại sẽ tiếp tục.

Phụ trợ: `find_missing.py` (liệt kê URL chưa có nội dung), `crawl_missing2.py` (crawl bổ sung bằng curl_cffi, có phát hiện CAPTCHA).

### Chi tiết các bước chính

- **Làm sạch**: trafilatura + tự giải mã bảng mã (GBK → gb18030), học dòng rác giao diện theo từng site (dòng xuất hiện ở ≥3% trang), loại trang CAPTCHA, phương án dự phòng khi tách nội dung thất bại. PubMed lưu dạng XML của API efetch → bộ đọc riêng (tiêu đề + tóm tắt theo mục + Keywords + MeSH).
- **Tìm kiếm**: nhóm ngôn ngữ theo website (PubMed = `en`). Lượt tìm: `bm25_vi`, `dense_vi_{vi,zh,en}`, `bm25_zh` (jieba), `dense_zh_zh`, `bm25_en`, `dense_en_en`. BM25 trên câu dịch có trọng số 0,3 vì lệch từ vựng với bài gốc.
- **Chunk**: gom các dòng tới ~1.000 ký tự (Việt/Anh) / ~500 (Trung), tiêu đề mục đi cùng đoạn sau; mỗi chunk là lát cắt nguyên văn `text[a:b]`. Chọn đoạn theo max(cos với câu Việt, cos với bản dịch cùng ngôn ngữ).

## Nộp bài

ZIP chứa **đúng 1 file** `.json` (không thư mục con) → leaderboard.aiguru.com.vn → *My Submissions*.
```json
[{"id": 1, "relevant_docs": [123, 456], "relevant_chunks": [{"doc_id": 123, "chunk_text": "trích nguyên văn…"}]}]
```
Đủ 1.200 câu. Tối đa **10 lần/ngày**; vòng private chỉ **5 lần tổng cộng**. `make_submission.py` tự kiểm tra định dạng trước khi nén.

## Kết quả leaderboard (public, 600 câu)

| Bản nộp | F2 tài liệu | F2 chunk | Điểm |
|---|---|---|---|
| 10 Việt + 5 Trung + 5 Anh (20 tài liệu) | 0,114 | 0,030 | 0,0724 |
| 20 Trung | 0,061 | 0,046 | 0,0536 |
| 20 Anh | 0 | 0 | 0 |
| 40 Việt + 50 Trung + 10 Anh (100 tài liệu) | 0,238 | 0,084 | **0,1606** |

Nhận xét:
- Đáp án rất lớn: trung vị **60 tài liệu/câu** (tối đa 190), ~1 chunk đáp án/tài liệu → cần nộp nhiều tài liệu.
- Đáp án hiện **không có tài liệu tiếng Anh** (0/12.000) → hạn mức tiếng Anh = 0 cho tới khi BTC xác nhận.
- Precision tài liệu: Việt ≈ 0,38 > Trung ≈ 0,16; nhưng Precision chunk: Trung > Việt (bài Việt dài, chọn sai đoạn).
- `details.jsonl` chỉ dùng phân tích tổng quát, **không** ghi nhớ đáp án từng câu (dò đáp án → có thể bị loại).

## Việc tiếp theo

- Tăng số tài liệu/câu (100 → 150–200) và chỉnh tỷ lệ Việt/Trung.
- Reranker đa ngôn ngữ (BGE-reranker-v2-m3) cho cả tài liệu lẫn chunk.
- Cải thiện chọn chunk cho bài tiếng Việt dài.
