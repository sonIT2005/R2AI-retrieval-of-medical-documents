#!/usr/bin/env bash
# build_submission.sh NAME QUOTA WEIGHTS CHUNK_QUOTA COMPRESS [RRF_K] [CHUNK_CHARS]
#   → submissions/sub_NAME.zip + parts/ + in "NAME n_parts sha256 size"
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
NAME=$1; QUOTA=$2; W=$3; CQ=$4; COMP=$5; K=${6:-60}; CC=${7:-4000:400}
$py search_docs.py --only-fuse --quota "$QUOTA" --weights "$W" --rrf-k "$K" --out "D_$NAME" >/dev/null 2>&1
$py chunk_quota.py --docs "results/D_$NAME.jsonl" --chunk-quota "$CQ" --out "results/C_$NAME.jsonl" >/dev/null
$py make_submission.py --docs "results/C_$NAME.jsonl" --chunk-chars "$CC" --compress "$COMP" --name "sub_$NAME" 2>&1 \
  | tr '\r' '\n' | grep -E "Error|assert|Traceback" || true
rm -f "submissions/sub_$NAME.json"
mkdir -p submissions/parts
split -b 9000000 -d -a 2 "submissions/sub_$NAME.zip" "submissions/parts/sub_$NAME.zip.part"
echo "$NAME $(ls submissions/parts/sub_$NAME.zip.part* | wc -l) $(sha256sum submissions/sub_$NAME.zip | cut -c1-64) $(stat -c %s submissions/sub_$NAME.zip)"
