"""
Tách câu hỏi nhiều ý thành các câu tìm kiếm con tiếng Việt (mỗi câu một bệnh/vấn đề) bằng Qwen3-8B (Ollama).
Câu hỏi bệnh nhân hay hỏi 2–3 bệnh cùng lúc → một vector dense trộn các ý, bài chỉ nói một bệnh bị xếp thấp.

    conda activate vibiomir
    python decompose_queries.py --limit 20     # thử, xem results/queries_sub.jsonl
    python decompose_queries.py                # 1.200 câu (~1 giờ)

Kết quả: results/queries_sub.jsonl — {id, query, subs: [câu con, ...]}.
BGE-M3 tìm chéo Việt → Trung được nên không cần LLM dịch câu con (thử 30/10: LLM dịch sai tên thuốc). Chạy lại sẽ bỏ qua câu đã tách.
"""

import os
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import urllib.request

import pandas as pd
from tqdm import tqdm

QUERIES = "btc_data_v2/query.parquet"
OUT = "results/queries_sub.jsonl"
OLLAMA = "http://localhost:11434/api/chat"

SYSTEM = (
    "You split a Vietnamese patient's medical question into search queries, one per DISTINCT disease, condition "
    "or test the patient asks about.\n"
    "Rules:\n"
    "- If the patient asks about only ONE disease/condition/test, return exactly ONE query: the question itself, "
    "shortened. Never return two queries about the same disease.\n"
    "- If the patient lists several different diseases/conditions/tests, return one query per item (max 4), each "
    "naming that item plus the patient's question about it.\n"
    "- Write in Vietnamese. Copy medical terms, drug names, numbers and units exactly as the patient wrote them.\n"
    "- Add no new diseases, no explanations, and do not answer.\n"
    "Example 1: \"Em bị viêm họng hạt và trào ngược dạ dày, uống thuốc gì?\" -> "
    "[\"Viêm họng hạt uống thuốc gì\", \"Trào ngược dạ dày uống thuốc gì\"]\n"
    "Example 2: \"Bé 2 tuổi sốt 39 độ có nên dùng hạ sốt không?\" -> "
    "[\"Bé 2 tuổi sốt 39 độ có nên dùng thuốc hạ sốt không\"]"
)
SCHEMA = {
    "type": "object",
    "properties": {"subs": {"type": "array", "minItems": 1, "maxItems": 4, "items": {"type": "string"}}},
    "required": ["subs"],
}


def decompose(query, model):
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
    subs = list(dict.fromkeys(x.strip() for x in out["subs"] if x.strip()))[:4]
    assert subs, "không có câu con"
    return subs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--workers", type=int, default=4, help="Số câu gửi Ollama cùng lúc")
    ap.add_argument("--limit", type=int, default=0, help="Chỉ tách N câu đầu (để thử)")
    args = ap.parse_args()

    q = pd.read_parquet(QUERIES)
    if args.limit:
        q = q.head(args.limit)
    done = set()
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            done = {json.loads(l)["id"] for l in f}
    todo = [(int(i), s) for i, s in zip(q["id"], q["query"]) if int(i) not in done]
    print(f"{len(q)} câu, đã tách {len(done)}, còn {len(todo)}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    errors = 0
    with open(OUT, "a", encoding="utf-8") as fout, ThreadPoolExecutor(args.workers) as pool:
        futs = {pool.submit(decompose, s, args.model): (i, s) for i, s in todo}
        for f in tqdm(as_completed(futs), total=len(futs), unit="câu"):
            i, s = futs[f]
            try:
                subs = f.result()
            except Exception as e:
                errors += 1
                tqdm.write(f"  lỗi câu {i}: {str(e)[:100]}")
                continue
            fout.write(json.dumps({"id": i, "query": s, "subs": subs}, ensure_ascii=False) + "\n")
            fout.flush()
    print(f"Xong → {OUT}" + (f" ({errors} câu lỗi — chạy lại để tách nốt)" if errors else ""))


if __name__ == "__main__":
    main()
