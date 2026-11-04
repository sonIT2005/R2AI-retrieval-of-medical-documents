"""
"Bộ dò" thay bảng xếp hạng: Qwen3-14B (Ollama, ≤15B) chấm log-odds liên quan (Yes/No, log-xác suất) cho mọi tài liệu mà các cấu hình đã nộp,
trên một mẫu câu hỏi cố định → F2 tài liệu "giả" cho bất kỳ danh sách nộp nào, hiệu chuẩn bằng các bài đã có điểm public.

    ollama pull qwen3:14b
    conda activate vibiomir
    python llm_judge.py build              # dựng lại 22 cấu hình đã có điểm public (vài phút)
    python llm_judge.py judge --n 300      # chấm pool của 300 câu (lâu; Ctrl+C rồi chạy lại để tiếp tục)
    python llm_judge.py eval               # F2 giả của 22 cấu hình so với điểm public (tương quan)
    python llm_judge.py eval --docs results/DC_moi.jsonl   # chấm một danh sách mới (tài liệu chưa có nhãn → báo số lượng)

Kết quả: results/judge/cfg_*.jsonl (danh sách nộp từng cấu hình), results/judge/labels.jsonl (nhãn, chạy lại bỏ qua cặp
đã chấm). Chỉ chấm CẤP TÀI LIỆU — điểm đoạn cần đoạn tham chiếu của BTC nên không mô phỏng được.
"""

import os
import sys
import json
import glob
import random
import argparse
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from tqdm import tqdm

DIR = "results/judge"
LABELS = f"{DIR}/labels.jsonl"  # nhãn của qwen3:14b; giám khảo khác: labels_<tên>.jsonl


def labels_path(model):
    return LABELS if model == "qwen3:14b" else f"{DIR}/labels_{model.replace(':', '-').replace('/', '_')}.jsonl"
QUERIES = "btc_data_v2/query.parquet"
TRANSLATED = "results/queries_translated.jsonl"
CORPUS = "clean/corpus"
OLLAMA = "http://localhost:11434/api/chat"
SEED = 2026

# tên, k RRF, trọng số ghi đè, reranker (None/prr/prrf), TB tài liệu, tỉ lệ Việt, điểm public, F2 tài liệu public
CONFIGS = [
    ("k60_m180_vs70", 60, "bm25bi_vi=0", None, 180, 0.70, 0.3365, None),
    ("k60_m160_vs70", 60, "bm25bi_vi=0", None, 160, 0.70, 0.3346, None),
    ("k60_m200_vs70", 60, "bm25bi_vi=0", None, 200, 0.70, 0.3356, None),
    ("k60_m180_vs65", 60, "bm25bi_vi=0", None, 180, 0.65, 0.3333, None),
    ("k60_m180_vs75", 60, "bm25bi_vi=0", None, 180, 0.75, 0.3376, None),
    ("k100_m180_vs70", 100, "bm25bi_vi=0", None, 180, 0.70, 0.3400, None),
    ("k150_m180_vs75", 150, "bm25bi_vi=0", None, 180, 0.75, 0.3427, 0.3728),
    ("k200_m180_vs75", 200, "bm25bi_vi=0", None, 180, 0.75, 0.3427, 0.3730),
    ("k150_m180_vs80", 150, "bm25bi_vi=0", None, 180, 0.80, 0.3419, None),
    ("k150_bm05", 150, "bm25bi_vi=0,bm25_vi=0.5", None, 180, 0.75, 0.3414, None),
    ("bi033", 150, "bm25bi_vi=0.33", None, 180, 0.75, 0.3437, None),
    ("bi02", 150, "bm25bi_vi=0.2", None, 180, 0.75, 0.3442, 0.3748),
    ("bi05", 150, "bm25bi_vi=0.5", None, 180, 0.75, 0.3399, None),
    ("bi1", 150, "bm25bi_vi=1", None, 180, 0.75, 0.2996, None),
    ("bionly", 150, "bm25bi_vi=0.33,bm25_vi=0", None, 180, 0.75, 0.3410, None),
    ("prr_m180", 150, "bm25bi_vi=0.2", "prr", 180, 0.75, 0.3479, None),
    ("prr_m160", 150, "bm25bi_vi=0.2", "prr", 160, 0.75, 0.3593, None),
    ("prr_m190", 150, "bm25bi_vi=0.2", "prr", 190, 0.75, 0.3400, None),
    ("prr_vs70", 150, "bm25bi_vi=0.2", "prr", 180, 0.70, 0.3493, None),
    ("prr_vs80", 150, "bm25bi_vi=0.2", "prr", 180, 0.80, 0.3442, None),
    ("prr_m140", 150, "bm25bi_vi=0.2", "prr", 140, 0.75, 0.3606, 0.3938),
    ("prrf_m180", 150, "bm25bi_vi=0.2", "prrf", 180, 0.75, 0.3388, None),
]

SYSTEM = (
    "You are a medical information specialist judging search results for a Vietnamese patient's health question. "
    "The document may be in Vietnamese or Chinese. A document is RELEVANT only if a doctor answering THIS patient "
    "would actually use it: it must address the patient's specific concern (the same condition, test or drug AND what "
    "the patient asks about it), taking their situation into account. Documents that only share the disease or body "
    "area, general health news, hospital promotion, or related-but-different topics are NOT relevant. "
    "Ignore ads and menus. Answer with exactly one word: Yes or No."
)


def sh(cmd):
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)


def load_lists(path):
    with open(path, encoding="utf-8") as f:
        return {r["query_id"]: (r["doc_ids"], r["langs"]) for r in map(json.loads, f)}


def build():
    os.makedirs(DIR, exist_ok=True)
    py = sys.executable
    fused = set()
    for name, k, w, rr, mean, vs, *_ in tqdm(CONFIGS, desc="Dựng cấu hình"):
        cand = f"J_k{k}_{w.replace('=', '').replace(',', '_').replace('.', '')}"
        if cand not in fused:
            sh(f"{py} search_docs.py --only-fuse --quota 300,130,0 --rrf-k {k} --weights {w} --out {cand}")
            fused.add(cand)
        docs = f"results/{cand}.jsonl"
        if rr:
            out = f"results/{cand}_q3r4B{rr}_all.jsonl"
            if not os.path.exists(out):  # điểm reranker đã có trong cache → không cần GPU chấm lại
                sh(f"{py} qwen_rerank.py --docs {docs} --pool 150,50 --quota 0,0 --model Qwen/Qwen3-Reranker-4B "
                   f"--text passage --passage-chars 1200 --tokens-per-batch 12000")
            docs = out
        sh(f"{py} dyn_cut.py --docs {docs} --mean {mean} --vi-share {vs} --lo 80 --hi 400 --out {DIR}/cfg_{name}.jsonl")
    # kiểm: hai cấu hình đã nộp phải khớp từng byte với file đã nộp (nếu còn trên đĩa)
    for name, ref in (("bi02", "results/DC_bi02.jsonl"), ("prr_m140", "results/DC_prr_m140.jsonl"),
                      ("prr_m160", "results/DC_prr_m160.jsonl")):
        if os.path.exists(ref):
            same = open(f"{DIR}/cfg_{name}.jsonl", "rb").read() == open(ref, "rb").read()
            print(f"  kiểm {name}: {'KHỚP' if same else 'KHÁC — dừng lại kiểm tra!'} {ref}")


def sample(n):
    q = pd.read_parquet(QUERIES)
    ids = sorted(int(i) for i in q["id"])
    random.Random(SEED).shuffle(ids)  # thứ tự cố định → tăng --n vẫn giữ nguyên các câu cũ
    return sorted(ids[:n])


def load_labels(path=LABELS):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return {(r["q"], r["d"]): r["s"] for r in map(json.loads, f)}


def judge_one(query, title, body, model):
    """→ log P(Yes) − log P(No) của token đầu (xác suất bão hoà ở 1,000 với nhiều tài liệu, log-odds vẫn xếp hạng được).
    Token không có trong top 20 → coi log-xác suất = −40."""
    user = f"Question (Vietnamese): {query}\n\nDocument title: {title}\nDocument excerpt:\n{body}\n\nRelevant?"
    req = json.dumps({
        "model": model, "stream": False, "logprobs": True, "top_logprobs": 20,
        **({"think": False} if model.startswith("qwen3") else {}),  # Gemma không có chế độ suy nghĩ
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
        "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 1},
    }).encode()
    r = urllib.request.Request(OLLAMA, data=req, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=600) as resp:
        top = json.loads(resp.read())["logprobs"][0]["top_logprobs"]
    p = {"yes": 0.0, "no": 0.0}
    for t in top:
        k = t["token"].strip().lower()
        if k in p:
            p[k] += float(np.exp(t["logprob"]))
    lp = {k: max(float(np.log(v)) if v > 0 else -40.0, -40.0) for k, v in p.items()}
    return lp["yes"] - lp["no"]


def judge(args):
    from qwen_rerank import best_passages
    qids = sample(args.n)
    cfgs = [load_lists(p) for p in sorted(glob.glob(f"{DIR}/cfg_*.jsonl"))]
    assert cfgs, "chưa có cấu hình — chạy: python llm_judge.py build"
    lang, pool = {}, {}
    for c in cfgs:
        for q in qids:
            ids, ls = c[q]
            pool.setdefault(q, set()).update(ids)
            lang.update(zip(ids, ls))
    out_path = labels_path(args.model)
    done = load_labels(out_path)
    todo = [(q, d) for q in qids for d in sorted(pool[q]) if (q, d) not in done]
    n_pairs = sum(len(v) for v in pool.values())
    print(f"{len(qids)} câu | pool TB {n_pairs / len(qids):.0f} tài liệu/câu = {n_pairs:,} cặp | "
          f"đã chấm {n_pairs - len(todo):,} | còn {len(todo):,}")
    if not todo:
        return
    need = {d for _, d in todo}
    docs = {}
    for p in tqdm(sorted(glob.glob(f"{CORPUS}/*.parquet")), desc="Đọc tài liệu"):
        t = pq.read_table(p, columns=["doc_id", "title", "text"]).to_pandas()
        t = t[t["doc_id"].isin(need)]
        docs.update({d: (ti or "", tx) for d, ti, tx in zip(t["doc_id"], t["title"], t["text"])})
    q = pd.read_parquet(QUERIES)
    qtext = {"vi": dict(zip(q["id"].astype(int), q["query"]))}
    tr = {r["id"]: r for r in map(json.loads, open(TRANSLATED, encoding="utf-8"))}
    qtext["zh"] = {i: tr[i]["zh"] for i in tr}
    qtext["en"] = {i: tr[i]["en"] for i in tr}
    by_q = {}
    for qq, d in todo:
        if d in docs:
            by_q.setdefault(qq, []).append(d)
    rows = [{"query_id": qq, "doc_ids": ds, "langs": [lang[d] for d in ds]} for qq, ds in by_q.items()]
    passages = best_passages(rows, docs, qtext)  # đoạn khớp nhất (BGE-M3), như reranker/make_submission

    def body_of(qq, d):
        ti, tx = docs[d]
        head = tx[:args.head_chars]
        p = passages.get((qq, d), "")
        extra = "" if not p or p[:200] in head else f"\n[...]\n{p[:args.passage_chars]}"
        return ti, head + extra

    jobs = [(qq, d) for qq, ds in by_q.items() for d in ds]
    errors = 0
    with open(out_path, "a", encoding="utf-8") as fout, ThreadPoolExecutor(args.workers) as pool_ex:
        futs = {pool_ex.submit(judge_one, qtext["vi"][qq], *body_of(qq, d), args.model): (qq, d)
                for qq, d in jobs}  # jobs theo thứ tự câu → dừng giữa chừng chỉ thiếu vài câu cuối
        for f in tqdm(as_completed(futs), total=len(futs), unit="cặp", smoothing=0.02):
            qq, d = futs[f]
            try:
                g = f.result()
            except Exception as e:
                errors += 1
                tqdm.write(f"  lỗi ({qq}, {d}): {str(e)[:80]}")
                continue
            fout.write(json.dumps({"q": qq, "d": int(d), "s": round(g, 5)}) + "\n")
            fout.flush()
    print(f"Xong → {out_path}" + (f" ({errors} lỗi — chạy lại để chấm nốt)" if errors else ""))


def f2_of(lists, by_q, qids, thr):
    """by_q: {câu: {tài liệu: log-odds}}. F2 = 5H / (4G + N), G = số tài liệu có log-odds ≥ thr trong pool đã chấm."""
    vals, unj = [], 0
    for q in qids:
        ids, lab = lists[q][0], by_q[q]
        rel = {d for d, g in lab.items() if g >= thr}
        unj += sum(d not in lab for d in ids)
        h = sum(d in rel for d in ids)
        vals.append(5 * h / (4 * len(rel) + len(ids)) if rel and ids else 0.0)
    return float(np.mean(vals)), unj


def rank_corr(a, b):
    ra, rb = pd.Series(a).rank(), pd.Series(b).rank()
    return float(np.corrcoef(ra, rb)[0, 1]), float(np.corrcoef(a, b)[0, 1])


# Giám khảo cho tài liệu Trung "liên quan" nhiều hơn mức các bài nộp đầu (15–16/10) cho thấy (độ chính xác Việt ≈ 2,4×
# Trung) → trừ Δ vào log-odds GỐC của tài liệu Trung, Δ riêng từng giám khảo, chọn để tỉ lệ Việt/Trung trên bi02 ≈ 2,4×:
# qwen3:14b 38%/32% → Δ 16 (2,6×); gemma3:12b vốn khắt khe hơn (1,6×) → Δ 3. Qwen 300 câu: cặp đúng 85% → 99%.
ZH_SHIFT = {"qwen3:14b": 16.0, "gemma3:12b": 3.0}


def combined_labels(models, lang, shift):
    """Trừ Δ cho tài liệu Trung trên log-odds gốc từng giám khảo; nhiều giám khảo → z-score từng giám khảo rồi lấy
    trung bình (chỉ cặp mọi giám khảo đã chấm). shift < 0 → dùng ZH_SHIFT theo mô hình."""
    per = []
    for m in models:
        dz = ZH_SHIFT.get(m, 0.0) if shift < 0 else shift
        per.append({k: v - (dz if lang.get(k[1]) == "zh" else 0.0) for k, v in load_labels(labels_path(m)).items()})
    if len(per) == 1:
        return per[0]
    common = set.intersection(*(set(p) for p in per))
    z = []
    for p in per:
        v = np.array([p[k] for k in common])
        mu, sd = v.mean(), v.std() or 1.0
        z.append({k: (p[k] - mu) / sd for k in common})
    return {k: float(np.mean([zz[k] for zz in z])) for k in common}


def evaluate(args):
    models = args.model.split(",")
    cfgs = {name: load_lists(f"{DIR}/cfg_{name}.jsonl") for name, *_ in CONFIGS
            if os.path.exists(f"{DIR}/cfg_{name}.jsonl")}
    extra = [load_lists(p) for p in glob.glob(f"{DIR}/cfg_x_*.jsonl")] + ([load_lists(args.docs)] if args.docs else [])
    lang = {d: l for c in list(cfgs.values()) + extra for ids, ls in c.values() for d, l in zip(ids, ls)}
    labels = combined_labels(models, lang, args.zh_shift)
    print(f"Giám khảo: {' + '.join(models)} | Δ Trung: "
          + ", ".join(f"{m} {ZH_SHIFT.get(m, 0.0) if args.zh_shift < 0 else args.zh_shift:g}" for m in models))
    by_q = {}
    for (q, d), g in labels.items():
        by_q.setdefault(q, {})[d] = g
    if args.dense_k:
        # Biến thể của bộ dò: chỉ tài liệu có trong top-K của các lượt dense mới có thể được tính đúng. Chọn vì tương quan
        # với các bài nộp public tốt hơn (68 câu: Pearson 0,53 → 0,88). Chỉ dùng để ĐO, không dùng để chỉnh hệ thống.
        dense = {}
        for run in ("dense_vi_vi", "dense_vi_zh", "dense_zh_zh"):
            for r in map(json.loads, open(f"results/run_{run}.jsonl", encoding="utf-8")):
                if r["query_id"] in by_q:
                    dense.setdefault(r["query_id"], set()).update(r["doc_ids"][:args.dense_k])
        by_q = {q: {d: (v if d in dense.get(q, ()) else -99.0) for d, v in m.items()} for q, m in by_q.items()}
    # chỉ dùng câu đã chấm ĐỦ pool (đang chấm dở → câu cuối thiếu nhãn sẽ làm lệch F2)
    qids = sorted(q for q in by_q if all(d in by_q[q] for c in cfgs.values() for d in c[q][0]))
    allp = np.sort([p for q in qids for p in by_q[q].values() if p > -99])[::-1]
    # ngưỡng toàn cục sao cho TB số tài liệu "đúng" mỗi câu = G (đáp án thật: trung vị 60, TB 71 tài liệu/câu)
    thrs = {G: float(allp[min(len(allp) - 1, G * len(qids))]) for G in (50, 71, 100)} if qids else {}
    print(f"{len(qids)} câu chấm đủ ({len(by_q)} có nhãn), {len(labels):,} cặp | log-odds trung vị "
          f"{np.median(allp) if len(allp) else 0:.3f} | ngưỡng cho G=50/71/100: "
          + ", ".join(f"{t:.3f}" for t in thrs.values()))
    if args.docs:
        lists = load_lists(args.docs)
        for G, thr in thrs.items():
            s, unj = f2_of(lists, by_q, qids, thr)
            print(f"  G≈{G}: F2 giả {s:.4f} | tài liệu chưa có nhãn: {unj:,}")
        return
    rows = []
    for name, *_, lb, lb_doc in CONFIGS:
        if name not in cfgs:
            continue
        rows.append([name, lb, lb_doc] + [f2_of(cfgs[name], by_q, qids, t)[0] for t in thrs.values()])
    cols = [f"G{G}" for G in thrs]
    df = pd.DataFrame(rows, columns=["cấu hình", "LB", "LB_doc"] + cols).sort_values("LB")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    for t in cols:
        sp, pe = rank_corr(df["LB"], df[t])
        # cặp cấu hình chênh nhau ≥ 0,005 trên LB (nhỏ hơn thì cả LB lẫn bộ dò đều không phân biệt chắc chắn)
        pairs = [(i, j) for i in range(len(df)) for j in range(len(df))
                 if df["LB"].iloc[i] - df["LB"].iloc[j] >= 0.005]
        ok = np.mean([df[t].iloc[i] > df[t].iloc[j] for i, j in pairs]) if pairs else float("nan")
        print(f"  {t}: Pearson {pe:+.3f} | Spearman {sp:+.3f} | cặp chênh ≥0,005 xếp đúng {ok:.0%} ({len(pairs)} cặp)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "judge", "eval"])
    ap.add_argument("--n", type=int, default=300, help="Số câu hỏi mẫu (cố định theo seed; tăng n giữ nguyên câu cũ)")
    ap.add_argument("--model", default="qwen3:14b", help="judge: một mô hình; eval: có thể nhiều, cách nhau dấu phẩy")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--head-chars", type=int, default=600)
    ap.add_argument("--passage-chars", type=int, default=1400)
    ap.add_argument("--docs", default=None, help="eval: chấm một danh sách nộp (DC_*.jsonl)")
    ap.add_argument("--zh-shift", type=float, default=-1, help="eval: trừ vào log-odds tài liệu Trung (-1 = theo ZH_SHIFT từng giám khảo, 0 = tắt)")
    ap.add_argument("--dense-k", type=int, default=300, help="eval: chỉ tài liệu trong top-K dense mới có thể được tính đúng (0 = tắt)")
    args = ap.parse_args()
    {"build": lambda: build(), "judge": lambda: judge(args), "eval": lambda: evaluate(args)}[args.cmd]()


if __name__ == "__main__":
    main()
