#!/usr/bin/env bash
# build_submission.sh NAME [MEAN] [VI_SHARE] [WEIGHTS]
#   Mặc định = bài tốt nhất 0,3606 (exp-073): gộp RRF k=150 (trọng số = DEFAULT_WEIGHTS trong search_docs.py)
#   → Qwen3-Reranker-4B chấm top 150 Việt + 50 Trung → cắt theo điểm reranker, TB 140 tài liệu/câu, 75% Việt.
#   vd: ./build_submission.sh best                  → submissions/sub_best.zip
#       ./build_submission.sh m160 160 0.75
#   RERANK=0   ./build_submission.sh ...   bỏ reranker (= bài 0,3442, nên đặt MEAN=180).
#   RERANK=ens ./build_submission.sh ...   gộp Qwen3-Reranker-4B + 8B (trung bình P(yes), ensemble_rerank.py; 8B nạp 8-bit).
#   CAND=results/D_bi02.jsonl ./build_submission.sh best   dùng danh sách ứng viên có sẵn (trong git), bỏ bước gộp
#       → máy khác (run_* khác) vẫn ra ĐÚNG bài 0,3606 và dùng lại điểm reranker trong cache, không cần GPU 6 giờ.
#   PARTS=1  ./build_submission.sh ...   chia thêm ZIP thành phần ≤ 9 MB (submissions/parts/) để nộp qua Chrome extension.
#   Cần sẵn results/run_*.jsonl (search_docs.py chạy đủ một lần). Reranker: ~6 giờ GPU lần đầu, chạy lại chỉ vài phút
#   nhờ results/qwen_rerank_cache_q3r4B_passage.pkl (có trong git). Nén LZMA-XL mất ~10–15 phút.
#   Python: biến PY nếu đặt; không thì venv Windows (.venv_search/Scripts) hoặc Linux (.venv_search/bin);
#   không có venv thì dùng `python` của môi trường đang kích hoạt (vd conda activate vibiomir).
set -e
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
py=${PY:-}
if [ -z "$py" ]; then
  for c in .venv_search/Scripts/python.exe .venv_search/bin/python; do [ -x "$c" ] && py=$c && break; done
fi
py=${py:-python}
NAME=$1; MEAN=${2:-140}; VS=${3:-0.75}; W=${4:-}
[ -z "$NAME" ] && { sed -n 2,15p "$0"; exit 1; }
if [ -n "${CAND:-}" ]; then
  [ "$CAND" -ef "results/D_$NAME.jsonl" ] || cp "$CAND" "results/D_$NAME.jsonl"
else
  $py search_docs.py --only-fuse --quota 300,130,0 --rrf-k 150 --weights "$W" --out "D_$NAME"
fi
DOCS="results/D_$NAME.jsonl"
if [ "${RERANK:-1}" != "0" ]; then
  $py qwen_rerank.py --docs "$DOCS" --pool 150,50 --quota 0,0 --model Qwen/Qwen3-Reranker-4B --text passage \
      --passage-chars 1200 --tokens-per-batch 12000
  if [ "${RERANK:-1}" = "ens" ]; then
    $py qwen_rerank.py --docs "$DOCS" --pool 150,50 --quota 0,0 --model Qwen/Qwen3-Reranker-8B --load-8bit \
        --text passage --passage-chars 1200 --tokens-per-batch 8000
    $py ensemble_rerank.py --a "results/D_${NAME}_q3r4Bprr_all.jsonl" --b "results/D_${NAME}_q3r8Bprr_all.jsonl" \
        --out "results/D_${NAME}_q3rEnsprr_all.jsonl"
    DOCS="results/D_${NAME}_q3rEnsprr_all.jsonl"
  else
    DOCS="results/D_${NAME}_q3r4Bprr_all.jsonl"
  fi
fi
$py dyn_cut.py --docs "$DOCS" --mean "$MEAN" --vi-share "$VS" --lo 80 --hi 400 --out "results/DC_$NAME.jsonl"
$py make_submission.py --docs "results/DC_$NAME.jsonl" --chunk-chars 4000:400 --compress lzma-xl --name "sub_$NAME"
rm -f "submissions/sub_$NAME.json"   # bản JSON chưa nén ~800 MB, chỉ cần .zip
ls -la "submissions/sub_$NAME.zip"
if [ "${PARTS:-0}" = "1" ]; then
  mkdir -p submissions/parts && rm -f "submissions/parts/sub_$NAME.zip.part"*
  split -b 9000000 -d -a 2 "submissions/sub_$NAME.zip" "submissions/parts/sub_$NAME.zip.part"
  echo "$NAME $(ls submissions/parts/sub_$NAME.zip.part* | wc -l) phần, sha256 $(sha256sum submissions/sub_$NAME.zip | cut -c1-64)"
fi
