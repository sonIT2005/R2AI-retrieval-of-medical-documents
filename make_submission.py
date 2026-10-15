"""
Tạo file nộp bài: tài liệu (từ search_docs.py) + đoạn khớp nhất trong mỗi tài liệu → JSON + ZIP.

    conda activate vibiomir
    python make_submission.py                                   # từ results/docs_fused_10-5-5.jsonl
    python make_submission.py --docs results/docs_fused_6-7-7.jsonl --chunks-per-doc 2

Kết quả: submissions/<tên>.json và submissions/<tên>.zip (ZIP chỉ chứa đúng 1 file JSON).
Định dạng: [{"id": int, "relevant_docs": [int], "relevant_chunks": [{"doc_id": int, "chunk_text": str}]}]
"""

import os
import re
import glob
import json
import zipfile
import argparse

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from tqdm import tqdm

CORPUS = "clean/corpus"
QUERIES = "btc_data_v2/query.parquet"
TRANSLATED = "results/queries_translated.jsonl"
CORPUS_IDS = "btc_data_v2/links_corpus_vi_en_zh.parquet"
CHUNK_CACHE = "results/chunk_cache.pkl"
MAX_CHARS = {"vi": 1000, "en": 1000, "zh": 500}
SENT_END = re.compile(r"(?<=[.!?。！？；;])\s*")
HEADING_END = (".", "。", "?", "？", "!", "！", ";", "；")


def is_heading(line):
    return len(line) < 80 and not line.endswith(HEADING_END)


def sentence_spans(line, max_chars):
    """Đoạn quá dài → các khoảng (bắt đầu, kết thúc) cắt tại ranh giới câu."""
    if len(line) <= max_chars * 1.5:
        return [(0, len(line))]
    cuts = [m.end() for m in SENT_END.finditer(line)] + [len(line)]
    spans, start, last = [], 0, 0
    for c in cuts:
        if c - start > max_chars and last > start:
            spans.append((start, last))
            start = last
        last = c
    spans.append((start, len(line)))
    return spans


def chunk_doc(text, max_chars):
    """Gom các dòng liên tiếp tới ~max_chars; dòng tiêu đề mục đi cùng đoạn ngay sau.
    Mỗi chunk là một lát cắt text[a:b] của văn bản gốc → luôn là trích dẫn nguyên văn."""
    pieces, pos = [], 0
    for line in text.split("\n"):
        if line.strip():
            pieces += [(pos + a, pos + b) for a, b in sentence_spans(line, max_chars)]
        pos += len(line) + 1
    chunks, start, last, size = [], None, None, 0
    for a, b in pieces:
        if start is not None and size + (b - a) > max_chars and not is_heading(text[last[0]:last[1]].strip()):
            chunks.append(text[start:last[1]].strip())
            start, size = None, 0
        start = a if start is None else start
        last = (a, b)
        size += b - a
    if start is not None:
        chunks.append(text[start:last[1]].strip())
    return [c for c in chunks if c]


def load_docs(need):
    docs = {}
    for p in tqdm(sorted(glob.glob(f"{CORPUS}/*.parquet")), desc="Đọc nội dung tài liệu"):
        t = pq.read_table(p, columns=["doc_id", "title", "text"]).to_pandas()
        t = t[t["doc_id"].isin(need)]
        docs.update({d: (ti, tx) for d, ti, tx in zip(t["doc_id"], t["title"], t["text"])})
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default="results/docs_fused_10-5-5.jsonl")
    ap.add_argument("--chunks-per-doc", type=int, default=1)
    ap.add_argument("--max-docs", type=int, default=0, help="Chỉ giữ N tài liệu đầu mỗi câu (0 = tất cả)")
    ap.add_argument("--chunk-docs", type=int, default=0, help="Chỉ lấy chunk cho N tài liệu đầu (0 = tất cả)")
    ap.add_argument("--name", default=None, help="Tên file nộp (mặc định theo tên file --docs)")
    args = ap.parse_args()
    name = args.name or "sub_" + os.path.basename(args.docs).replace("docs_", "").replace(".jsonl", "")

    with open(args.docs, encoding="utf-8") as f:
        res = {r["query_id"]: r for r in map(json.loads, f)}
    if args.max_docs:
        for r in res.values():
            r["doc_ids"], r["langs"] = r["doc_ids"][:args.max_docs], r["langs"][:args.max_docs]
    q = pd.read_parquet(QUERIES)
    qids = [int(i) for i in q["id"]]
    qtext = {"vi": dict(zip(qids, q["query"]))}
    if os.path.exists(TRANSLATED):
        with open(TRANSLATED, encoding="utf-8") as f:
            tr = {r["id"]: r for r in map(json.loads, f)}
        for l in ("zh", "en"):
            qtext[l] = {i: tr[i][l] for i in qids if i in tr}

    need = {d for r in res.values() for d in r["doc_ids"]}
    docs = load_docs(need)
    lang_of = {d: l for r in res.values() for d, l in zip(r["doc_ids"], r["langs"])}

    chunk_need = {d for r in res.values() for d in r["doc_ids"][:args.chunk_docs or None]}
    chunks = {d: chunk_doc(docs[d][1], MAX_CHARS.get(lang_of.get(d, "vi"), 1000)) for d in docs if d in chunk_need}

    import pickle
    import torch
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("BAAI/bge-m3", device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = 512
    enc = lambda xs: model.encode(xs, batch_size=64, normalize_embeddings=True, convert_to_numpy=True,
                                  show_progress_bar=len(xs) > 2000).astype(np.float32)

    # Bộ nhớ đệm vector chunk theo tài liệu → các bản nộp sau không phải mã hoá lại
    cache = {}
    if os.path.exists(CHUNK_CACHE):
        with open(CHUNK_CACHE, "rb") as f:
            cache = pickle.load(f)
    todo = [d for d in chunks if d not in cache or cache[d][0] != chunks[d]]
    flat = [(d, i) for d in todo for i in range(len(chunks[d]))]
    print(f"{len(chunks):,} tài liệu cần chunk | đã có sẵn {len(chunks) - len(todo):,} | "
          f"mã hoá mới {len(todo):,} tài liệu = {len(flat):,} đoạn")
    if flat:
        new = enc([f"{docs[d][0]}\n{chunks[d][i]}" for d, i in flat]).astype(np.float16)
        o = 0
        for d in todo:
            n = len(chunks[d])
            cache[d] = (chunks[d], new[o:o + n])
            o += n
        with open(CHUNK_CACHE, "wb") as f:
            pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
    qvec = {l: dict(zip(m.keys(), enc(list(m.values())))) for l, m in qtext.items()}

    out, n_chunks = [], 0
    for qid in qids:
        r = res.get(qid, {"doc_ids": [], "langs": []})
        rel_docs = [int(d) for d in r["doc_ids"] if d in docs]
        rel_chunks = []
        for d, lang in zip(r["doc_ids"], r["langs"]):
            if d not in chunks or not chunks[d]:
                continue
            cv = cache[d][1].astype(np.float32)
            sims = cv @ qvec["vi"][qid]
            if lang in qvec and qid in qvec[lang]:
                sims = np.maximum(sims, cv @ qvec[lang][qid])
            for i in np.argsort(-sims)[:args.chunks_per_doc]:
                rel_chunks.append({"doc_id": int(d), "chunk_text": chunks[d][i]})
        n_chunks += len(rel_chunks)
        out.append({"id": qid, "relevant_docs": rel_docs, "relevant_chunks": rel_chunks})

    # Kiểm tra trước khi nộp
    valid = set(pq.read_table(CORPUS_IDS, columns=["id"])["id"].to_pylist())
    assert len(out) == 1200 and len({o["id"] for o in out}) == 1200, "phải đủ 1.200 câu, không trùng"
    assert all(d in valid for o in out for d in o["relevant_docs"]), "có doc_id ngoài corpus BTC"
    assert all(c["chunk_text"] in docs[c["doc_id"]][1] for o in out for c in o["relevant_chunks"]), \
        "chunk_text phải là đoạn trích nguyên văn"

    os.makedirs("submissions", exist_ok=True)
    jpath, zpath = f"submissions/{name}.json", f"submissions/{name}.zip"
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(jpath, arcname=os.path.basename(jpath))
    empty = sum(1 for o in out if not o["relevant_docs"])
    print(f"\n✓ {len(out)} câu | TB {np.mean([len(o['relevant_docs']) for o in out]):.1f} tài liệu, "
          f"{n_chunks / len(out):.1f} đoạn mỗi câu | câu rỗng: {empty}")
    print(f"  JSON: {jpath} ({os.path.getsize(jpath) / 1e6:.1f} MB)")
    print(f"  ZIP : {zpath} ({os.path.getsize(zpath) / 1e6:.1f} MB) ← tải file này lên leaderboard")


if __name__ == "__main__":
    main()
