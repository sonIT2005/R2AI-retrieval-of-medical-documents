#!/usr/bin/env bash
# Đóng gói dữ liệu chia sẻ qua Google Drive (tài liệu thuyết minh mục 1.2) → OUT/ + SHA256SUMS.
#   ./tools/pack_data.sh [OUT=../drive_upload]
# Mỗi file .tar giải nén từ THƯ MỤC GỐC repo:  tar -xf <file>.tar   (kiểm tra: sha256sum -c SHA256SUMS)
#   vibiomir_db_extra.tar      BẮT BUỘC — trang đội tự crawl bổ sung (vibiomir_s3/db_extra, SQLite nén zstd)
#   vibiomir_clean_corpus.tar  tăng tốc — văn bản đã làm sạch (bỏ qua clean_corpus.py, ~1h20)
#   vibiomir_emb.tar           tăng tốc — vector BGE-M3 (bỏ qua embed_corpus.py, ~3 giờ GPU)
#   vibiomir_results.tar       tăng tốc — 9 lượt tìm run_*.jsonl, vector đoạn chunk_cache.pkl, điểm Qwen3-Reranker-8B
set -e
cd "$(dirname "$0")/.."
OUT=${1:-../drive_upload}
mkdir -p "$OUT"
pack() {  # tên  đường-dẫn...
  local name=$1; shift
  echo "→ $OUT/$name.tar ($(du -shc "$@" | tail -1 | cut -f1))"
  tar -cf "$OUT/$name.tar" "$@"
}
pack vibiomir_db_extra vibiomir_s3/db_extra
pack vibiomir_clean_corpus clean/corpus
pack vibiomir_emb emb
pack vibiomir_results results/run_*.jsonl results/chunk_cache.pkl \
     $(ls results/qwen_rerank_cache_q3r8B_passage.pkl 2>/dev/null)
(cd "$OUT" && sha256sum vibiomir_*.tar > SHA256SUMS && cat SHA256SUMS && du -shc vibiomir_*.tar | tail -1)
