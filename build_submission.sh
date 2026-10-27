#!/usr/bin/env bash
# build_submission.sh NAME [RRF_K] [VI_SHARE] [MEAN] [WEIGHTS]
#   Mặc định = bài tốt nhất 0,3427 (exp-049): RRF k=150, 75% tài liệu Việt, TB 180 tài liệu/câu.
#   vd: ./build_submission.sh k150vs75                 → submissions/sub_k150vs75.zip
#       ./build_submission.sh k150bm05 150 0.75 180 bm25_vi=0.5
#   PARTS=1 ./build_submission.sh ...   chia thêm ZIP thành phần ≤ 9 MB (submissions/parts/) để nộp qua Chrome extension.
#   Cần sẵn results/run_*.jsonl (search_docs.py chạy đủ một lần). Nén LZMA-XL mất ~10–15 phút.
#   Python: biến PY nếu đặt; không thì venv Windows (.venv_search/Scripts) hoặc Linux (.venv_search/bin);
#   không có venv thì dùng `python` của môi trường đang kích hoạt (vd conda activate vibiomir).
set -e
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
py=${PY:-}
if [ -z "$py" ]; then
  for c in .venv_search/Scripts/python.exe .venv_search/bin/python; do [ -x "$c" ] && py=$c && break; done
fi
py=${py:-python}
NAME=$1; K=${2:-150}; VS=${3:-0.75}; MEAN=${4:-180}; W=${5:-}
[ -z "$NAME" ] && { sed -n 2,7p "$0"; exit 1; }
$py search_docs.py --only-fuse --quota 300,130,0 --rrf-k "$K" --weights "$W" --out "D_$NAME"
$py dyn_cut.py --docs "results/D_$NAME.jsonl" --mean "$MEAN" --vi-share "$VS" --lo 80 --hi 400 --out "results/DC_$NAME.jsonl"
$py make_submission.py --docs "results/DC_$NAME.jsonl" --chunk-chars 4000:400 --compress lzma-xl --name "sub_$NAME"
rm -f "submissions/sub_$NAME.json"   # bản JSON chưa nén ~800 MB, chỉ cần .zip
ls -la "submissions/sub_$NAME.zip"
if [ "${PARTS:-0}" = "1" ]; then
  mkdir -p submissions/parts && rm -f "submissions/parts/sub_$NAME.zip.part"*
  split -b 9000000 -d -a 2 "submissions/sub_$NAME.zip" "submissions/parts/sub_$NAME.zip.part"
  echo "$NAME $(ls submissions/parts/sub_$NAME.zip.part* | wc -l) phần, sha256 $(sha256sum submissions/sub_$NAME.zip | cut -c1-64)"
fi
