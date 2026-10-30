"""
Mục tiêu 1 — tìm tài liệu cho 1.200 câu hỏi theo TỪNG ngôn ngữ, rồi gộp theo hạn mức Việt/Trung/Anh.

    conda activate vibiomir
    python search_docs.py                         # chạy mọi lượt tìm có thể + gộp (hạn mức 10,5,5)
    python search_docs.py --quota 8,6,6           # đổi hạn mức Việt,Trung,Anh
    python search_docs.py --only-fuse --quota 8,6,6   # chỉ gộp lại từ các lượt đã chạy (vài giây)

Lượt tìm → results/run_<tên>.jsonl:
    bm25_vi, dense_vi_vi, dense_vi_zh, dense_vi_en            (câu hỏi tiếng Việt gốc)
    bm25_zh, dense_zh_zh, bm25_en, dense_en_en                (cần results/queries_translated.jsonl)
Kết quả gộp → results/docs_fused_<vi>-<zh>-<en>.jsonl: {query_id, query, doc_ids, scores, langs}
"""

import os
import glob
import json
import argparse
from multiprocessing import Pool

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import scipy.sparse as sp
from sklearn.feature_extraction.text import HashingVectorizer
from tqdm import tqdm

CORPUS = "clean/corpus"
EMB = "emb"
OUT = "results"
INDEX = "index/bm25"
QUERIES = "btc_data_v2/query.parquet"
TRANSLATED = "results/queries_translated.jsonl"
PUBMED = "pubmed.ncbi.nlm.nih.gov"
GROUPS = ("vi", "zh", "en")
K1, B = 1.2, 0.75
N_FEATURES = 2 ** 23
BM25_MAX_CHARS = 10000
POOL = 300
RRF_K = 60
# BM25 trên câu dịch lệch từ vựng với bài gốc (top-10 chỉ trùng ~3% với dense) → trọng số thấp
DEFAULT_WEIGHTS = ("bm25_vi=0.33,bm25_zh=0.3,bm25_en=0,"  # cấu hình tốt nhất (exp-010/029)
                   "bm25bi_vi=0,bm25bi_zh=0")  # đang thử (exp-054+) — bật bằng --weights bm25bi_vi=...

RUNS = {  # tên: (cách tìm, ngôn ngữ câu hỏi, nhóm tài liệu)
    "bm25_vi": ("bm25", "vi", "vi"),
    "bm25_zh": ("bm25", "zh", "zh"),
    "bm25_en": ("bm25", "en", "en"),
    "bm25bi_vi": ("bm25", "vi", "vi"),  # BM25 trên cặp âm tiết liền nhau ("huyết áp", "đau đầu")
    "bm25bi_zh": ("bm25", "zh", "zh"),  # BM25 trên cặp chữ Hán liền nhau (không qua jieba) của câu dịch Trung
    "dense_vi_vi": ("dense", "vi", "vi"),
    "dense_vi_zh": ("dense", "vi", "zh"),
    "dense_vi_en": ("dense", "vi", "en"),
    "dense_zh_zh": ("dense", "zh", "zh"),
    "dense_en_en": ("dense", "en", "en"),
}  # fuse() chỉ gộp các lượt có tên ở đây — file results/run_*.jsonl lạ bị bỏ qua

_hv = dict(n_features=N_FEATURES, alternate_sign=False, norm=None, dtype=np.float32)
VEC = {
    "vi": HashingVectorizer(lowercase=True, token_pattern=r"(?u)\b\w+\b", **_hv),
    "en": HashingVectorizer(lowercase=True, token_pattern=r"(?u)\b\w\w+\b", stop_words="english", **_hv),
    "zh": HashingVectorizer(lowercase=True, token_pattern=r"\S+", **_hv),  # văn bản đã tách từ bằng jieba
    # cặp âm tiết: nhiều tổ hợp hơn từ đơn → 2^24 chiều để giảm va chạm băm
    "vi_bi": HashingVectorizer(lowercase=True, token_pattern=r"(?u)\b\w+\b", ngram_range=(2, 2),
                               **{**_hv, "n_features": 2 ** 24}),
    # cặp chữ liền nhau (cách chuẩn của tìm kiếm tiếng Trung) — chạy trên văn bản gốc, không tách từ
    "zh_bi": HashingVectorizer(lowercase=True, analyzer="char", ngram_range=(2, 2),
                               **{**_hv, "n_features": 2 ** 24}),
}
BM25_VEC = {"bm25bi_vi": "vi_bi", "bm25bi_zh": "zh_bi"}  # lượt BM25 dùng bộ tách khác nhóm ngôn ngữ của nó (mặc định = tên nhóm)


# ── Dữ liệu ──────────────────────────────────────────────────────────────

def load_meta():
    """Nhóm ngôn ngữ theo website (đa số bài của site), PubMed = 'en'."""
    m = pd.concat(pq.read_table(p, columns=["doc_id", "host", "lang"]).to_pandas()
                  for p in sorted(glob.glob(f"{CORPUS}/*.parquet")))
    host_group = (m[m["lang"].isin(["vi", "zh"])].groupby("host")["lang"]
                  .agg(lambda s: s.value_counts().index[0]).to_dict())
    host_group[PUBMED] = "en"
    group = m["host"].map(host_group).fillna("vi")
    return pd.Series(group.to_numpy(), index=m["doc_id"].to_numpy()), host_group


def load_queries():
    q = pd.read_parquet(QUERIES)
    base = [(int(i), s) for i, s in zip(q["id"], q["query"])]
    qs = {"vi": base}
    if os.path.exists(TRANSLATED):
        with open(TRANSLATED, encoding="utf-8") as f:
            tr = {r["id"]: r for r in map(json.loads, f)}
        if all(i in tr for i, _ in base):
            qs["zh"] = [(i, tr[i]["zh"]) for i, _ in base]
            qs["en"] = [(i, tr[i]["en"]) for i, _ in base]
        else:
            print(f"  Bản dịch chưa đủ ({len(tr)}/{len(base)} câu) → bỏ qua các lượt cần bản dịch")
    else:
        print("  Chưa có bản dịch → chỉ chạy các lượt dùng câu hỏi tiếng Việt")
    return qs


def save_run(name, queries, ids, scores):
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/run_{name}.jsonl", "w", encoding="utf-8") as f:
        for (qid, _), d, s in zip(queries, ids, scores):
            f.write(json.dumps({"query_id": qid, "doc_ids": [int(x) for x in d],
                                "scores": [round(float(x), 5) for x in s]}) + "\n")


def load_run(name):
    with open(f"{OUT}/run_{name}.jsonl", encoding="utf-8") as f:
        return {r["query_id"]: r["doc_ids"] for r in map(json.loads, f)}


# ── BM25 theo từng nhóm ngôn ngữ ─────────────────────────────────────────

def prepare(key, texts):
    if key != "zh":  # chỉ chỉ mục BM25 "zh" tách từ bằng jieba
        return texts
    import jieba
    jieba.setLogLevel(60)
    return [" ".join(w for w in jieba.cut_for_search(t) if any(ch.isalnum() for ch in w)) for t in texts]


def _part_tf(args):
    path, group, host_group, key = args
    t = pq.read_table(path, columns=["doc_id", "host", "title", "text"]).to_pandas()
    t = t[t["host"].map(host_group).fillna("vi") == group]
    if t.empty:
        return None
    docs = (t["title"] + "\n" + t["text"]).str.slice(0, BM25_MAX_CHARS).tolist()
    return t["doc_id"].to_numpy(), VEC[key].transform(prepare(key, docs)).tocsr()


def build_bm25(group, host_group, key):
    d = f"{INDEX}/{key}"
    nf = VEC[key].n_features
    parts = sorted(glob.glob(f"{CORPUS}/*.parquet"))
    newest = max(os.path.getmtime(p) for p in parts)
    if os.path.exists(f"{d}/W.npz") and os.path.getmtime(f"{d}/W.npz") > newest:
        return sp.load_npz(f"{d}/W.npz"), np.load(f"{d}/ids.npy")
    with Pool(min(30, os.cpu_count() or 4)) as pool:
        res = [r for r in tqdm(pool.imap(_part_tf, [(p, group, host_group, key) for p in parts]),
                               total=len(parts), desc=f"BM25 {key}: tách từ") if r is not None]
    ids = np.concatenate([i for i, _ in res])
    mats = [m for _, m in res]
    dls = [np.asarray(m.sum(axis=1)).ravel() for m in mats]
    avgdl = np.concatenate(dls).mean()
    df = np.zeros(nf, dtype=np.int64)
    for m in mats:
        df += np.bincount(m.indices, minlength=nf)
    n = len(ids)
    idf = np.log(1 + (n - df + 0.5) / (df + 0.5)).astype(np.float32)
    for m, dl in zip(mats, dls):
        rows = np.repeat(np.arange(m.shape[0]), np.diff(m.indptr))
        norm = K1 * (1 - B + B * dl[rows] / avgdl)
        m.data = (m.data * (K1 + 1) / (m.data + norm) * idf[m.indices]).astype(np.float32)
    W = sp.vstack(mats).tocsr()
    os.makedirs(d, exist_ok=True)
    sp.save_npz(f"{d}/W.npz", W, compressed=False)
    np.save(f"{d}/ids.npy", ids)
    print(f"  BM25 {key}: {n:,} tài liệu")
    return W, ids


def run_bm25(name, queries, host_group):
    _, _, group = RUNS[name]
    key = BM25_VEC.get(name, group)
    W, ids = build_bm25(group, host_group, key)
    Q = VEC[key].transform(prepare(key, [q for _, q in queries])).tocsr()
    Q.data[:] = 1.0
    WT = W.T.tocsr()
    all_ids, all_scores = [], []
    for i in tqdm(range(0, Q.shape[0], 50), desc=f"{name}: tìm kiếm"):
        S = (Q[i:i + 50] @ WT).toarray()
        top = np.argpartition(-S, POOL, axis=1)[:, :POOL]
        for row, cand in zip(S, top):
            order = cand[np.argsort(-row[cand])]
            all_ids.append(ids[order])
            all_scores.append(row[order])
    save_run(name, queries, all_ids, all_scores)


# ── Dense (BGE-M3), tìm riêng trong từng nhóm ngôn ngữ ──────────────────

def run_dense(names, qs, doc_group):
    if not names:
        return
    import torch
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("BAAI/bge-m3", device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = 512
    qv = {l: model.encode([q for _, q in qs[l]], batch_size=64, normalize_embeddings=True,
                          convert_to_tensor=True).half()
          for l in {RUNS[n][1] for n in names}}
    del model
    torch.cuda.empty_cache()

    files = sorted(glob.glob(f"{EMB}/*.parquet.npy"))
    sizes = [np.load(f, mmap_mode="r").shape[0] for f in files]
    E = torch.empty((sum(sizes), np.load(files[0], mmap_mode="r").shape[1]), dtype=torch.float16, device="cuda")
    ids = np.empty(sum(sizes), dtype=np.int64)
    o = 0
    for f, n in tqdm(list(zip(files, sizes)), desc="Dense: nạp vector lên GPU"):
        E[o:o + n] = torch.from_numpy(np.load(f)).to("cuda")
        ids[o:o + n] = np.load(f[:-4] + ".ids.npy")
        o += n
    grp = doc_group.reindex(ids).to_numpy()

    for name in names:
        _, qlang, g = RUNS[name]
        rows = np.where(grp == g)[0]
        Eg = E.index_select(0, torch.from_numpy(rows).to("cuda"))
        all_ids, all_scores = [], []
        for i in range(0, len(qv[qlang]), 64):
            S = qv[qlang][i:i + 64] @ Eg.T
            s, top = torch.topk(S, POOL, dim=1)
            for srow, irow in zip(s.float().cpu().numpy(), top.cpu().numpy()):
                all_ids.append(ids[rows[irow]])
                all_scores.append(srow)
        save_run(name, qs[qlang], all_ids, all_scores)
        print(f"  {name}: xong ({len(rows):,} tài liệu nhóm {g})")
        del Eg
        torch.cuda.empty_cache()


# ── Gộp: RRF trong từng ngôn ngữ, rồi ghép theo hạn mức ──────────────────

def fuse(qs, quota, weights, out_name=None, rrf_k=RRF_K):
    have = [n for n in RUNS if os.path.exists(f"{OUT}/run_{n}.jsonl") and weights.get(n, 1.0) > 0]
    runs = {n: load_run(n) for n in have}
    by_group = {g: [n for n in have if RUNS[n][2] == g] for g in GROUPS}
    for g in GROUPS:
        desc = ", ".join(f"{n}×{weights.get(n, 1.0):g}" for n in by_group[g]) or "(chưa có)"
        print(f"  Nhóm {g}: hạn mức {quota[g]:>3} | lượt tìm: {desc}")
    tag = "-".join(str(quota[g]) for g in GROUPS)
    path = f"{OUT}/{out_name or f'docs_fused_{tag}'}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for qid, q in qs["vi"]:
            merged = []
            for gi, g in enumerate(GROUPS):
                score = {}
                for n in by_group[g]:
                    w = weights.get(n, 1.0)
                    for rank, d in enumerate(runs[n].get(qid, [])):
                        score[d] = score.get(d, 0.0) + w / (rrf_k + rank + 1)
                best = sorted(score.items(), key=lambda x: -x[1])[:quota[g]]
                merged += [((j + 1) / quota[g], gi, d, s, g) for j, (d, s) in enumerate(best)]
            merged.sort()
            f.write(json.dumps({"query_id": qid, "query": q, "doc_ids": [m[2] for m in merged],
                                "scores": [round(m[3], 5) for m in merged],
                                "langs": [m[4] for m in merged]}, ensure_ascii=False) + "\n")
    print(f"  → {path}")
    return path


def show_examples(path, n=3):
    with open(path, encoding="utf-8") as f:
        res = [json.loads(l) for l in f][:n]
    need = {d for r in res for d in r["doc_ids"]}
    titles = {}
    for p in glob.glob(f"{CORPUS}/*.parquet"):
        t = pq.read_table(p, columns=["doc_id", "title"]).to_pandas()
        t = t[t["doc_id"].isin(need)]
        titles.update(zip(t["doc_id"], t["title"]))
    print("\n=== Ví dụ ===")
    for r in res:
        print(f"\n❓ {r['query'][:150]}")
        for d, l in list(zip(r["doc_ids"], r["langs"]))[:9]:
            print(f"   [{l}] {d}: {titles.get(d, '')[:80]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quota", default="10,5,5", help="Số tài liệu mỗi câu cho Việt,Trung,Anh")
    ap.add_argument("--only-fuse", action="store_true", help="Không tìm lại, chỉ gộp từ các lượt đã chạy")
    ap.add_argument("--weights", default="",
                    help="Ghi đè trọng số từng lượt lên DEFAULT_WEIGHTS, vd 'bm25_zh=0,bm25_vi=0.5' "
                         "(0 = bỏ hẳn; lượt không có trong mặc định = 1)")
    ap.add_argument("--out", default=None, help="Tên file kết quả gộp (không cần .jsonl)")
    ap.add_argument("--runs", default=None, help="Chỉ chạy các lượt này, vd 'dense_vi_zh' (mặc định: tất cả)")
    ap.add_argument("--rrf-k", type=int, default=RRF_K, help="Hằng số k của RRF khi gộp (mặc định 60)")
    args = ap.parse_args()
    quota = dict(zip(GROUPS, map(int, args.quota.split(","))))
    parse = lambda s: {k: float(v) for k, v in (kv.split("=") for kv in s.split(",") if kv)}
    weights = {**parse(DEFAULT_WEIGHTS), **parse(args.weights)}  # --weights ghi đè TỪNG lượt lên mặc định

    qs = load_queries()
    print(f"{len(qs['vi'])} câu hỏi | ngôn ngữ câu hỏi sẵn có: {', '.join(qs)}")
    if not args.only_fuse:
        doc_group, host_group = load_meta()
        print("Tài liệu theo nhóm:", doc_group.value_counts().to_dict())
        todo = [n for n, (_, ql, _) in RUNS.items() if ql in qs and (not args.runs or n in args.runs.split(","))]
        for n in todo:
            if RUNS[n][0] == "bm25":
                run_bm25(n, qs[RUNS[n][1]], host_group)
        run_dense([n for n in todo if RUNS[n][0] == "dense"], qs, doc_group)
    show_examples(fuse(qs, quota, weights, args.out, args.rrf_k))


if __name__ == "__main__":
    main()
