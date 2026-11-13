"""Dựng dữ liệu cho web demo (web/data/) từ bài nộp + kho sạch — đội loi_cuda, ViBioMIR.

    python tools/build_demo_data.py                         # submissions/sub_prr_m140.zip + clean/corpus
    python tools/build_demo_data.py --sub submissions/sub_ens_m140.zip

Ra: web/data/questions.json (1.200 câu + bản dịch) và web/data/q/<id>.json (tài liệu theo hạng + đoạn trích).
Thiếu file nộp → chế độ dự phòng: thứ tự ứng viên results/D_bi02.jsonl (chưa qua reranker, 140 đầu), không có
đoạn trích; thiếu clean/corpus → không có tiêu đề/URL. Web đọc cờ "complete" và báo "chưa đủ dữ liệu".
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import pyarrow.parquet as pq

TRANSLATED = "results/queries_translated.jsonl"
CANDIDATES = "results/D_bi02.jsonl"
CORPUS = "clean/corpus"
OUT = "web/data"
FALLBACK_N = 140


def load_sub(path):
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.endswith(".json"))
            return json.loads(z.read(name))
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_meta(ids):
    """doc_id → (title, url, host, lang) cho các id cần, đọc từng file parquet của kho sạch."""
    meta = {}
    files = sorted(glob.glob(f"{CORPUS}/*.parquet"))
    for i, p in enumerate(files, 1):
        t = pq.read_table(p, columns=["doc_id", "title", "url", "host", "lang"]).to_pydict()
        for d, ti, u, h, l in zip(t["doc_id"], t["title"], t["url"], t["host"], t["lang"]):
            if d in ids:
                meta[d] = (ti or "", u or "", h or "", l or "")
        print(f"\r  kho sạch {i}/{len(files)} — đã có {len(meta):,} tài liệu", end="", file=sys.stderr)
    if files:
        print(file=sys.stderr)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", default="submissions/sub_prr_m140.zip", help="File nộp (.zip hoặc .json)")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    queries = {}
    with open(TRANSLATED, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            queries[r["id"]] = {"vi": r["query"], "zh": r.get("zh", ""), "en": r.get("en", "")}

    cand_lang, cand_order = {}, {}
    with open(CANDIDATES, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            cand_order[r["query_id"]] = r["doc_ids"]
            cand_lang.update(zip(r["doc_ids"], r["langs"]))

    have_sub = os.path.exists(args.sub)
    if have_sub:
        ranked, chunks = {}, {}
        for o in load_sub(args.sub):
            ranked[o["id"]] = o["relevant_docs"]
            chunks[o["id"]] = {c["doc_id"]: c["chunk_text"] for c in o["relevant_chunks"]}
        source = os.path.basename(args.sub)
    else:
        print(f"! Không thấy {args.sub} → dự phòng: {CANDIDATES} (chưa rerank, không có đoạn trích)", file=sys.stderr)
        ranked = {q: ids[:FALLBACK_N] for q, ids in cand_order.items()}
        chunks = {}
        source = f"{os.path.basename(CANDIDATES)} (dự phòng)"

    need = {d for ids in ranked.values() for d in ids}
    meta = load_meta(need) if glob.glob(f"{CORPUS}/*.parquet") else {}
    if not meta:
        print(f"! Không thấy {CORPUS}/*.parquet → không có tiêu đề, URL", file=sys.stderr)

    os.makedirs(f"{args.out}/q", exist_ok=True)
    qlist, n_docs, no_chunk, no_meta = [], 0, 0, 0
    for qid in sorted(queries):
        docs = []
        for rank, d in enumerate(ranked.get(qid, []), 1):
            title, url, host, lang = meta.get(d, (None, None, None, None))
            chunk = chunks.get(qid, {}).get(d)
            no_chunk += chunk is None
            no_meta += title is None
            docs.append({"rank": rank, "doc_id": d, "lang": lang or cand_lang.get(d, ""),
                         "title": title, "host": host, "url": url, "chunk": chunk})
        n_docs += len(docs)
        with open(f"{args.out}/q/{qid}.json", "w", encoding="utf-8") as f:
            json.dump({"id": qid, "docs": docs}, f, ensure_ascii=False, separators=(",", ":"))
        qlist.append(dict(id=qid, n=len(docs), **queries[qid]))

    empty = sum(q["n"] == 0 for q in qlist)
    complete = have_sub and no_chunk == 0 and no_meta == 0 and empty == 0
    if empty:
        print(f"! {empty} câu không có tài liệu nào", file=sys.stderr)
    with open(f"{args.out}/questions.json", "w", encoding="utf-8") as f:
        json.dump({"complete": complete, "source": source, "questions": qlist}, f, ensure_ascii=False,
                  separators=(",", ":"))

    print(f"{len(qlist)} câu · {n_docs:,} tài liệu (TB {n_docs / max(1, len(qlist)):.1f}/câu) · "
          f"thiếu đoạn trích {no_chunk:,} · thiếu tiêu đề/URL {no_meta:,} · nguồn {source} · "
          f"{'ĐỦ dữ liệu' if complete else 'CHƯA đủ dữ liệu'}")
    assert len(qlist) == 1200, "phải đủ 1.200 câu"


if __name__ == "__main__":
    main()
