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
                   # lượt thử nghiệm đã bác bỏ: fuse() gộp MỌI results/run_*.jsonl có sẵn → mặc định tắt
                   "dense_vi_vimax=0,dense_vi_viprf=0,dense_vi_zhprf=0,dense_hyde_vi=0,dense_hyde_zh=0,"
                   # Qwen3-Embedding (đang thử, exp-047+) — bật bằng --weights dense_q3e_zh_zh=1,...
                   "dense_q3e_vi_vi=0,dense_q3e_vi_zh=0,dense_q3e_zh_zh=0")

RUNS = {  # tên: (cách tìm, ngôn ngữ câu hỏi, nhóm tài liệu)
    "bm25_vi": ("bm25", "vi", "vi"),
    "bm25_zh": ("bm25", "zh", "zh"),
    "bm25_en": ("bm25", "en", "en"),
    "dense_vi_vi": ("dense", "vi", "vi"),
    "dense_vi_zh": ("dense", "vi", "zh"),
    "dense_vi_en": ("dense", "vi", "en"),
    "dense_zh_zh": ("dense", "zh", "zh"),
    "dense_en_en": ("dense", "en", "en"),
    # như dense_vi_vi nhưng điểm = max(cos đầu bài, cos các cửa sổ phần sau trong emb_tail/) — cần chạy embed_tail.py
    "dense_vi_vimax": ("dense", "vi", "vi"),
    # sinh bởi prf.py (Rocchio trên vector) — chỉ dùng khi gộp, không tự chạy
    "dense_vi_viprf": ("prf", "vi", "vi"),
    "dense_vi_zhprf": ("prf", "vi", "zh"),
    # sinh bởi hyde.py (câu hỏi + đoạn trả lời giả định của Qwen3-8B) — chỉ dùng khi gộp, không tự chạy
    "dense_hyde_vi": ("hyde", "vi", "vi"),
    "dense_hyde_zh": ("hyde", "vi", "zh"),
    # mô hình embedding thứ hai (embed_corpus.py --model Qwen/Qwen3-Embedding-0.6B --out emb_q3e [--group zh])
    "dense_q3e_vi_vi": ("dense", "vi", "vi"),
    "dense_q3e_vi_zh": ("dense", "vi", "zh"),
    "dense_q3e_zh_zh": ("dense", "zh", "zh"),
}
EMB_TAIL = "emb_tail"
DENSE_MODELS = {  # lượt dense_q3e_* dùng mô hình/vector riêng; còn lại BGE-M3 + emb/
    "bge": dict(emb=EMB, model="BAAI/bge-m3", prompt=None),
    # Qwen3-Embedding cần câu chỉ dẫn tiếng Anh phía câu hỏi (thiếu → giảm 1–5% theo model card); tài liệu không cần
    # emb là mẫu glob: mỗi nhóm mã hoá vào thư mục riêng (emb_q3e/ = zh, emb_q3e_vi/ = vi) để --group không ghi đè nhau
    "q3e": dict(emb="emb_q3e*", model="Qwen/Qwen3-Embedding-0.6B",
                prompt="Instruct: Given a medical question from a Vietnamese patient, retrieve medical articles "
                       "or doctor answers that answer the question\nQuery:"),
}
dense_cfg = lambda name: "q3e" if name.startswith("dense_q3e_") else "bge"

_hv = dict(n_features=N_FEATURES, alternate_sign=False, norm=None, dtype=np.float32)
VEC = {
    "vi": HashingVectorizer(lowercase=True, token_pattern=r"(?u)\b\w+\b", **_hv),
    "en": HashingVectorizer(lowercase=True, token_pattern=r"(?u)\b\w\w+\b", stop_words="english", **_hv),
    "zh": HashingVectorizer(lowercase=True, token_pattern=r"\S+", **_hv),  # văn bản đã tách từ bằng jieba
}


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

def prepare(group, texts):
    if group != "zh":
        return texts
    import jieba
    jieba.setLogLevel(60)
    return [" ".join(w for w in jieba.cut_for_search(t) if any(ch.isalnum() for ch in w)) for t in texts]


def _part_tf(args):
    path, group, host_group = args
    t = pq.read_table(path, columns=["doc_id", "host", "title", "text"]).to_pandas()
    t = t[t["host"].map(host_group).fillna("vi") == group]
    if t.empty:
        return None
    docs = (t["title"] + "\n" + t["text"]).str.slice(0, BM25_MAX_CHARS).tolist()
    return t["doc_id"].to_numpy(), VEC[group].transform(prepare(group, docs)).tocsr()


def build_bm25(group, host_group):
    d = f"{INDEX}/{group}"
    parts = sorted(glob.glob(f"{CORPUS}/*.parquet"))
    newest = max(os.path.getmtime(p) for p in parts)
    if os.path.exists(f"{d}/W.npz") and os.path.getmtime(f"{d}/W.npz") > newest:
        return sp.load_npz(f"{d}/W.npz"), np.load(f"{d}/ids.npy")
    with Pool(min(30, os.cpu_count() or 4)) as pool:
        res = [r for r in tqdm(pool.imap(_part_tf, [(p, group, host_group) for p in parts]),
                               total=len(parts), desc=f"BM25 {group}: tách từ") if r is not None]
    ids = np.concatenate([i for i, _ in res])
    mats = [m for _, m in res]
    dls = [np.asarray(m.sum(axis=1)).ravel() for m in mats]
    avgdl = np.concatenate(dls).mean()
    df = np.zeros(N_FEATURES, dtype=np.int64)
    for m in mats:
        df += np.bincount(m.indices, minlength=N_FEATURES)
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
    print(f"  BM25 {group}: {n:,} tài liệu")
    return W, ids


def run_bm25(name, queries, host_group):
    _, _, group = RUNS[name]
    W, ids = build_bm25(group, host_group)
    Q = VEC[group].transform(prepare(group, [q for _, q in queries])).tocsr()
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
    for key, cfg in DENSE_MODELS.items():
        sub = [n for n in names if dense_cfg(n) == key]
        if sub:
            run_dense_model(sub, qs, doc_group, **cfg)


def run_dense_model(names, qs, doc_group, emb, model, prompt):
    import torch
    from sentence_transformers import SentenceTransformer

    kw = {"tokenizer_kwargs": {"padding_side": "left"}} if "Qwen3" in model else {}
    model = SentenceTransformer(model, device="cuda", model_kwargs={"torch_dtype": torch.float16}, **kw)
    model.max_seq_length = 512
    qv = {l: model.encode([q for _, q in qs[l]], batch_size=64, normalize_embeddings=True, prompt=prompt,
                          convert_to_tensor=True).half()
          for l in {RUNS[n][1] for n in names}}
    del model
    torch.cuda.empty_cache()

    files = sorted(glob.glob(f"{emb}/*.parquet.npy"))
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
        if len(rows) < POOL:  # vd emb_q3e mới mã hoá nhóm zh (--group zh) → chưa có vector nhóm vi
            print(f"  {name}: bỏ qua — {emb}/ chỉ có {len(rows):,} tài liệu nhóm {g}")
            continue
        Eg = E.index_select(0, torch.from_numpy(rows).to("cuda"))
        T = pos = None
        if name.endswith("max"):
            T, pos = load_tail(ids[rows], torch)
        all_ids, all_scores = [], []
        for i in range(0, len(qv[qlang]), 64):
            S = qv[qlang][i:i + 64] @ Eg.T
            if T is not None:  # điểm tài liệu = max(đầu bài, các cửa sổ phần sau)
                S = S.float().scatter_reduce(1, pos.expand(S.shape[0], -1), (qv[qlang][i:i + 64] @ T.T).float(),
                                             reduce="amax")
            s, top = torch.topk(S, POOL, dim=1)
            for srow, irow in zip(s.float().cpu().numpy(), top.cpu().numpy()):
                all_ids.append(ids[rows[irow]])
                all_scores.append(srow)
        save_run(name, qs[qlang], all_ids, all_scores)
        print(f"  {name}: xong ({len(rows):,} tài liệu nhóm {g})")
        del Eg, T, pos
        torch.cuda.empty_cache()


def load_tail(row_ids, torch):
    """Vector các cửa sổ phần sau (emb_tail/) + vị trí tài liệu tương ứng trong row_ids."""
    files = sorted(glob.glob(f"{EMB_TAIL}/*.parquet.npy"))
    vecs = np.concatenate([np.load(f) for f in files])
    tids = np.concatenate([np.load(f[:-4] + ".ids.npy") for f in files])
    order = np.argsort(row_ids)
    j = np.searchsorted(row_ids[order], tids).clip(0, len(row_ids) - 1)
    ok = row_ids[order][j] == tids  # bỏ cửa sổ của tài liệu không thuộc nhóm (an toàn)
    print(f"  Phần sau: {ok.sum():,} cửa sổ của {len(np.unique(tids[ok])):,} tài liệu")
    T = torch.from_numpy(vecs[ok]).to("cuda")
    pos = torch.from_numpy(order[j[ok]]).to("cuda").unsqueeze(0)
    return T, pos


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
                    help="Ghi đè trọng số từng lượt lên DEFAULT_WEIGHTS, vd 'bm25_zh=0,dense_hyde_vi=1' "
                         "(0 = bỏ hẳn; lượt không có trong mặc định = 1)")
    ap.add_argument("--out", default=None, help="Tên file kết quả gộp (không cần .jsonl)")
    ap.add_argument("--runs", default=None, help="Chỉ chạy các lượt này, vd 'dense_vi_vimax' (mặc định: tất cả)")
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
        todo = [n for n, (_, ql, _) in RUNS.items() if ql in qs
                and (not n.endswith("max") or glob.glob(f"{EMB_TAIL}/*.ids.npy"))
                and (dense_cfg(n) == "bge" or glob.glob(f"{DENSE_MODELS[dense_cfg(n)]['emb']}/*.ids.npy"))
                and (not args.runs or n in args.runs.split(","))]
        for n in todo:
            if RUNS[n][0] == "bm25":
                run_bm25(n, qs[RUNS[n][1]], host_group)
        run_dense([n for n in todo if RUNS[n][0] == "dense"], qs, doc_group)
    show_examples(fuse(qs, quota, weights, args.out, args.rrf_k))


if __name__ == "__main__":
    main()
