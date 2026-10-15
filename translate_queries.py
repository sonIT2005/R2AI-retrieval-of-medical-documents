"""
Mục tiêu 3 — dịch 1.200 câu hỏi sang tiếng Trung và tiếng Anh bằng Qwen3-8B (Ollama).

    ollama pull qwen3:8b
    conda activate vibiomir
    python translate_queries.py

Kết quả: results/queries_translated.jsonl — {id, query, zh, en}. Chạy lại sẽ bỏ qua câu đã dịch.
"""

import os
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import urllib.request

import pandas as pd
from tqdm import tqdm

QUERIES = "btc_data_v2/query.parquet"
OUT = "results/queries_translated.jsonl"
OLLAMA = "http://localhost:11434/api/chat"

SYSTEM = (
    "You are a professional medical translator. Translate the Vietnamese medical question into:\n"
    "1. zh: Simplified Chinese, phrased naturally like a patient asking on a Chinese medical Q&A website, "
    "using standard Chinese medical terms.\n"
    "2. en: English, using standard medical terminology as used in PubMed articles.\n"
    "Keep every number, unit, lab value, drug name and abbreviation exactly as written. "
    "Translate faithfully: keep all details, add nothing, and do not answer the question."
)
SCHEMA = {
    "type": "object",
    "properties": {"zh": {"type": "string"}, "en": {"type": "string"}},
    "required": ["zh", "en"],
}


def translate(query, model):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": query}],
        "stream": False,
        "think": False,
        "format": SCHEMA,
        "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.loads(json.loads(r.read())["message"]["content"])
    return out["zh"].strip(), out["en"].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--workers", type=int, default=4, help="Số câu gửi Ollama cùng lúc")
    ap.add_argument("--limit", type=int, default=0, help="Chỉ dịch N câu đầu (để thử)")
    args = ap.parse_args()

    q = pd.read_parquet(QUERIES)
    if args.limit:
        q = q.head(args.limit)
    done = set()
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            done = {json.loads(l)["id"] for l in f}
    todo = [(int(i), s) for i, s in zip(q["id"], q["query"]) if int(i) not in done]
    print(f"{len(q)} câu, đã dịch {len(done)}, còn {len(todo)}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    errors = 0
    with open(OUT, "a", encoding="utf-8") as fout, ThreadPoolExecutor(args.workers) as pool:
        futs = {pool.submit(translate, s, args.model): (i, s) for i, s in todo}
        for f in tqdm(as_completed(futs), total=len(futs), unit="câu"):
            i, s = futs[f]
            try:
                zh, en = f.result()
            except Exception as e:
                errors += 1
                tqdm.write(f"  lỗi câu {i}: {str(e)[:100]}")
                continue
            fout.write(json.dumps({"id": i, "query": s, "zh": zh, "en": en}, ensure_ascii=False) + "\n")
            fout.flush()
    print(f"Xong → {OUT}" + (f" ({errors} câu lỗi — chạy lại để dịch nốt)" if errors else ""))


if __name__ == "__main__":
    main()
