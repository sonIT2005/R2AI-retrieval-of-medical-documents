"""
Xếp hạng lại tài liệu ứng viên bằng cross-encoder BAAI/bge-reranker-v2-m3 (568M, phát hành 03/2024).

    conda activate vibiomir
    python rerank.py --docs results/docs_fused_120-180-0.jsonl              # chấm + ghi 2 bản xếp hạng
    python rerank.py --docs results/docs_fused_120-180-0.jsonl --limit 50   # đo tốc độ trên 50 câu

Mỗi tài liệu: đoạn = tiêu đề + 1.500 ký tự đầu (Trung: 700). Tài liệu Việt dùng câu hỏi tiếng Việt, tài liệu Trung dùng
bản dịch tiếng Trung. Điểm không cùng thang giữa hai ngôn ngữ → xếp lại TRONG từng ngôn ngữ rồi xen kẽ theo hạn mức
như search_docs.fuse (giữ nguyên số tài liệu mỗi ngôn ngữ của file --docs).
Kết quả:
    results/<tên>_rr.jsonl     thứ tự theo điểm reranker
    results/<tên>_rrf.jsonl    RRF(k=60) giữa thứ tự cũ và thứ tự reranker (an toàn hơn)
Điểm lưu đệm ở results/rerank_cache.pkl (khoá: câu, tài liệu) → chạy lại chỉ chấm cặp mới.
"""

import os
import glob
import json
import pickle
import argparse

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from tqdm import tqdm

CORPUS = "clean/corpus"
QUERIES = "btc_data_v2/query.parquet"
TRANSLATED = "results/queries_translated.jsonl"
CACHE = "results/rerank_cache.pkl"
HEAD = {"vi": 1500, "zh": 700, "en": 1500}
RRF_K = 60


def interleave(by_lang, quota):
    """Xen kẽ các danh sách theo tỉ lệ hạn mức như search_docs.fuse."""
    merged = []
    for gi, (lang, docs) in enumerate(by_lang.items()):
        merged += [((j + 1) / quota[lang], gi, d, lang) for j, d in enumerate(docs)]
    merged.sort()
    return [m[2] for m in merged], [m[3] for m in merged]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True)
    ap.add_argument("--limit", type=int, default=0, help="Chỉ chấm N câu đầu (đo tốc độ)")
    ap.add_argument("--batch-size", type=int, default=32)
    args = ap.parse_args()

    res = [json.loads(l) for l in open(args.docs, encoding="utf-8")]
    if args.limit:
        res = res[:args.limit]
    q = pd.read_parquet(QUERIES)
    qtext = {"vi": dict(zip(q["id"].astype(int), q["query"]))}
    tr = {r["id"]: r for r in map(json.loads, open(TRANSLATED, encoding="utf-8"))}
    qtext["zh"] = {i: tr[i]["zh"] for i in tr}
    qtext["en"] = {i: tr[i]["en"] for i in tr}

    need = {d for r in res for d in r["doc_ids"]}
    docs = {}
    for p in tqdm(sorted(glob.glob(f"{CORPUS}/*.parquet")), desc="Đọc tài liệu"):
        t = pq.read_table(p, columns=["doc_id", "title", "text"]).to_pandas()
        t = t[t["doc_id"].isin(need)]
        docs.update({d: (ti or "", tx) for d, ti, tx in zip(t["doc_id"], t["title"], t["text"])})

    cache = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else {}
    pairs, keys = [], []
    for r in res:
        for d, lang in zip(r["doc_ids"], r["langs"]):
            if (r["query_id"], d) in cache or d not in docs:
                continue
            ti, tx = docs[d]
            body = tx if tx.startswith(ti) else f"{ti}\n{tx}"
            pairs.append((qtext[lang].get(r["query_id"], qtext["vi"][r["query_id"]]), body[:HEAD.get(lang, 1500)]))
            keys.append((r["query_id"], d))
    print(f"{len(res)} câu | {len(pairs):,} cặp cần chấm | đã có sẵn {len(cache):,}")

    if pairs:
        import torch
        from sentence_transformers import CrossEncoder
        model = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512, device="cuda",
                             model_kwargs={"torch_dtype": torch.float16})
        order = np.argsort([len(a) + len(b) for a, b in pairs])  # gom cặp cùng độ dài → ít padding
        step = 20000
        for s in tqdm(range(0, len(order), step), desc="Chấm (khối 20k cặp)"):
            idx = order[s:s + step]
            scores = model.predict([pairs[i] for i in idx], batch_size=args.batch_size, show_progress_bar=False)
            for i, sc in zip(idx, scores):
                cache[keys[i]] = float(sc)
            with open(CACHE + ".tmp", "wb") as f:
                pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(CACHE + ".tmp", CACHE)

    base = os.path.basename(args.docs).replace(".jsonl", "")
    outs = {"rr": [], "rrf": []}
    for r in res:
        langs = list(dict.fromkeys(r["langs"]))
        quota = {l: r["langs"].count(l) for l in langs}
        old = {l: [d for d, x in zip(r["doc_ids"], r["langs"]) if x == l] for l in langs}
        rr = {l: sorted(old[l], key=lambda d: -cache.get((r["query_id"], d), -1e9)) for l in langs}
        rrf = {}
        for l in langs:
            sc = {}
            for ranking in (old[l], rr[l]):
                for k, d in enumerate(ranking):
                    sc[d] = sc.get(d, 0.0) + 1 / (RRF_K + k + 1)
            rrf[l] = sorted(old[l], key=lambda d: -sc[d])
        for name, by_lang in (("rr", rr), ("rrf", rrf)):
            ids, ls = interleave(by_lang, quota)
            outs[name].append({"query_id": r["query_id"], "query": r.get("query", ""), "doc_ids": ids,
                               "scores": [cache.get((r["query_id"], d), 0.0) for d in ids], "langs": ls})
    for name, rows in outs.items():
        path = f"results/{base}_{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  → {path}")


if __name__ == "__main__":
    main()
