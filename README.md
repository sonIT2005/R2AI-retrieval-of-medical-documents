# R2AI 2026 · ViBioMIR — đội loi_cuda

Truy hồi thông tin y khoa **xuyên ngôn ngữ**: câu hỏi tiếng Việt → danh sách **tài liệu** (`doc_id`) và **đoạn nội dung**
(trích nguyên văn) liên quan trong kho khoảng 1,2 triệu tài liệu Việt – Trung – Anh (PubMed).
Điểm = trung bình F2 cấp tài liệu và F2 cấp đoạn (tính theo từng câu rồi lấy trung bình).

Tài liệu thuyết minh đầy đủ (phương pháp, sơ đồ, dữ liệu, mô hình): `docs/thuyet_minh_loi_cuda.pdf`.
Nhật ký toàn bộ thí nghiệm: `docs/EXPERIMENTS.md`.

| Bài nộp | Cấu hình | Điểm public (600 câu) |
|---|---|---|
| `sub_prr_m140` | 9 lượt tìm + RRF k=150 → Qwen3-Reranker-4B → cắt TB 140 tài liệu/câu | **0,3606** (F2 tài liệu 0,3938 · F2 đoạn 0,3274) |
| `sub_ens_m140` | như trên, điểm reranker = trung bình Qwen3-Reranker-4B và 8B | bài nộp vòng private |

---

## 1. Yêu cầu hệ thống

| Thành phần | Phiên bản đã dùng | Ghi chú |
|---|---|---|
| Hệ điều hành | Ubuntu 26.04 LTS | Linux bất kỳ có CUDA đều chạy được |
| GPU | NVIDIA RTX 5060 Ti 16 GB, driver 595.91 | ≥ 16 GB VRAM cho Qwen3-Reranker-4B fp16 / 8B 8-bit |
| CPU / RAM | 32 luồng / 29 GB | Tắt ứng dụng nặng khi chạy reranker (cần ~16 GB RAM) |
| Ổ đĩa | ~120 GB (chạy từ đầu) · ~50 GB (dùng dữ liệu tăng tốc, không cần `vibiomir_s3/`) | gồm ~34 GB mô hình |
| Conda | Miniconda | 2 môi trường: `base` (Python 3.14) và `vibiomir` (Python 3.11) |
| CUDA (PyTorch) | 12.8 | `torch==2.11.0+cu128` |
| Ollama | 0.31.1 | Chạy Qwen3-8B để dịch câu hỏi |

## 2. Cài đặt môi trường

```bash
git clone https://github.com/sonIT2005/R2AI-retrieval-of-medical-documents.git vibiomir && cd vibiomir

# (a) Làm sạch HTML — conda base, Python 3.14
pip install -r requirements-clean.txt

# (b) Vector, tìm kiếm, reranker, tạo file nộp — Python 3.11, GPU
conda create -n vibiomir python=3.11 -y && conda activate vibiomir
pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements-search.txt

# (c) Dịch câu hỏi — Ollama (https://ollama.com/download), bản 0.31.1
ollama pull qwen3:8b
```

Mọi lệnh bên dưới chạy **từ thư mục gốc repo**. Mọi bước dài đều dừng được bằng `Ctrl+C`; chạy lại sẽ tiếp tục từ chỗ dừng.

## 3. Dữ liệu

### 3.1. Bắt buộc

| Thư mục | Nội dung | Cách lấy |
|---|---|---|
| `btc_data_v2/` | Danh sách kho chính thức (1.220.598 URL) + 1.200 câu hỏi | `hf download AIGuruTinix/ViBioMIR links_corpus_vi_en_zh.parquet query.parquet --repo-type dataset --local-dir btc_data_v2` |
| `vibiomir_s3/` (`db/`, `db_cc/`, `db_wayback/`, `db_alt/`) | HTML/XML đã crawl (SQLite nén zstd, ~58 GB) | `hf download snute/ai_guru-S3 --repo-type dataset --local-dir vibiomir_s3` |
| `vibiomir_s3/db_extra/` | Trang đội tự crawl bổ sung (38 file SQLite, 6,1 GB) | Google Drive: `vibiomir_db_extra.tar` → `tar -xf vibiomir_db_extra.tar` |

### 3.2. Tăng tốc (không bắt buộc)

Bỏ qua được các bước tốn thời gian nhất. Tải từ cùng thư mục Google Drive, giải nén ở thư mục gốc repo:

| File | Bỏ qua bước | Dung lượng |
|---|---|---|
| `vibiomir_clean_corpus.tar` → `clean/corpus/` | Làm sạch (~1 giờ 20) | 1,5 GB |
| `vibiomir_emb.tar` → `emb/` | Vector BGE-M3 (~3 giờ GPU) | 2,4 GB |
| `vibiomir_results.tar` → `results/` | 9 lượt tìm, vector đoạn BGE-M3 (`chunk_cache.pkl`) | ~3,6 GB |

**Link Google Drive:** `<https://drive.google.com/drive/folders/1zoATII9wMD3SAhux7n9Cu49K1jRjEwYQ?usp=sharing>` · Kiểm tra toàn vẹn: `sha256sum -c SHA256SUMS`.

Đã có sẵn trong repo (không cần tải): `results/queries_translated.jsonl` (bản dịch câu hỏi),
`results/D_bi02.jsonl` (danh sách ứng viên của bài nộp), `results/qwen_rerank_cache_q3r4B_passage.pkl` và
`results/qwen_rerank_cache_q3r8B_passage.pkl` (điểm Qwen3-Reranker-4B / 8B).

## 4. Mô hình

Tất cả là mô hình mã nguồn mở ≤ 15 tỷ tham số, phát hành trước 01/08/2026; tải tự động khi chạy lần đầu.

| Mô hình | Vai trò | Phiên bản (commit / digest) | Tải |
|---|---|---|---|
| BAAI/bge-m3 | Vector tài liệu và câu hỏi; chọn đoạn khớp nhất | `5617a9f` | https://huggingface.co/BAAI/bge-m3 |
| Qwen/Qwen3-Reranker-4B | Xếp hạng lại 200 ứng viên/câu | `22e6836` | https://huggingface.co/Qwen/Qwen3-Reranker-4B |
| Qwen/Qwen3-Reranker-8B | Xếp hạng lại (gộp với 4B), nạp 8-bit | `77d193c` | https://huggingface.co/Qwen/Qwen3-Reranker-8B |
| qwen3:8b (Ollama, Q4_K_M) | Dịch câu hỏi sang Trung, Anh | `500a1f067a9f` | `ollama pull qwen3:8b` |

Chỉ dùng khi phát triển (không nằm trong quy trình tạo bài nộp): `qwen3:14b` và `gemma3:12b` (Ollama) làm giám khảo cho
tập phát triển tự gán nhãn (`llm_judge.py`).

## 5. Chạy lại từ đầu

| # | Lệnh | Việc | Thời gian* |
|---|---|---|---|
| 1 | `conda activate base && python clean_corpus.py` | HTML/XML → văn bản sạch, chỉ giữ id thuộc kho BTC → `clean/corpus/` | ~1 giờ 20 |
| 2 | `conda activate vibiomir && python embed_corpus.py` | BGE-M3, 1 vector/tài liệu → `emb/` | ~3 giờ |
| 3 | `python translate_queries.py` | Qwen3-8B dịch câu hỏi → `results/queries_translated.jsonl` (đã có trong repo) | ~1,5 giờ |
| 4 | `python search_docs.py --quota 300,130,0 --rrf-k 150 --out D_bi02` | Dựng chỉ mục BM25 + 9 lượt tìm → `results/run_*.jsonl`; gộp RRF → 300 ứng viên Việt + 130 Trung/câu | ~20 phút |
| 5 | `./build_submission.sh prr_m140` | Qwen3-Reranker-4B → cắt TB 140 → `submissions/sub_prr_m140.zip` | ~6 giờ (có cache: ~20 phút) |
| 5' | `RERANK=ens ./build_submission.sh ens_m140` | Thêm Qwen3-Reranker-8B, gộp điểm → `submissions/sub_ens_m140.zip` | ~14 giờ (có cache: ~20 phút) |

\* RTX 5060 Ti 16 GB, 32 luồng CPU.

`build_submission.sh` gồm: gộp RRF (`search_docs.py --only-fuse`) → reranker (`qwen_rerank.py`, `ensemble_rerank.py`)
→ cắt số tài liệu theo từng câu (`dyn_cut.py`) → trích đoạn và nén (`make_submission.py`, tự kiểm tra định dạng).

### Tái tạo đúng bài nộp mà không chạy lại tìm kiếm

Dùng danh sách ứng viên và điểm reranker có trong repo / Google Drive:

```bash
conda activate vibiomir
CAND=results/D_bi02.jsonl ./build_submission.sh prr_m140             # bài 0,3606 — chỉ cần clean/corpus + results/
CAND=results/D_bi02.jsonl RERANK=ens ./build_submission.sh ens_m140  # bài nộp private (điểm 8B cũng có trong repo)
```

Nếu chưa có `results/chunk_cache.pkl` (trong `vibiomir_results.tar`), lần chạy đầu `make_submission.py` và `qwen_rerank.py`
phải mã hoá đoạn văn bằng BGE-M3 (thêm ~1 giờ GPU).

## 6. Định dạng file nộp

ZIP chứa **đúng 1 file** `.json` (không thư mục con), đủ 1.200 câu:
```json
[{"id": 1, "relevant_docs": [123, 456], "relevant_chunks": [{"doc_id": 123, "chunk_text": "trích nguyên văn…"}]}]
```

## 7. Cấu trúc mã nguồn

| File | Việc |
|---|---|
| `clean_corpus.py` | Giải mã bảng mã, trafilatura, lọc dòng rác giao diện theo website, đọc XML PubMed |
| `embed_corpus.py` | Vector BGE-M3 cho kho tài liệu |
| `translate_queries.py` | Dịch câu hỏi bằng Qwen3-8B (Ollama, JSON schema) |
| `search_docs.py` | BM25 (âm tiết, cặp âm tiết, jieba) + dense BGE-M3 theo từng nhóm ngôn ngữ; gộp RRF có trọng số |
| `qwen_rerank.py` | Qwen3-Reranker chấm (câu hỏi, tiêu đề + đoạn khớp nhất), lưu đệm điểm |
| `ensemble_rerank.py` | Trung bình điểm hai reranker |
| `dyn_cut.py` | Số tài liệu theo từng câu: giữ tài liệu có điểm ≥ τ·điểm cao nhất, τ dò để đạt trung bình mong muốn |
| `make_submission.py` | Chia đoạn, chọn đoạn khớp nhất, mở rộng cửa sổ 4.000 ký tự, nén LZMA, kiểm tra định dạng |
| `build_submission.sh` | Bước 4–7 trong một lệnh |
| `llm_judge.py` | Tập phát triển gán nhãn bằng LLM (chỉ dùng khi phát triển) |
| `scripts/crawl/` | Crawl bổ sung các trang còn thiếu (đã chạy xong) |
| `tools/pack_data.sh` | Đóng gói dữ liệu chia sẻ qua Google Drive |
| `requirements-clean.txt`, `requirements-search.txt` | Phiên bản thư viện |
