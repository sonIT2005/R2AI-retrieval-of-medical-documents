"""
Chấm lại danh sách ứng viên bằng Qwen3-Reranker-4B (06/2025, Apache-2.0) — bước đem lại BEST 0,3606 (exp-066/073).

    python qwen_rerank.py --docs results/D_bi02.jsonl --pool 150,50 --quota 0,0 \
        --model Qwen/Qwen3-Reranker-4B --text passage --passage-chars 1200 --tokens-per-batch 12000

Mỗi cặp: câu hỏi ĐẦY ĐỦ (tài liệu Trung dùng bản dịch Trung) + tiêu đề + đoạn khớp nhất theo BGE-M3 (≤ --passage-chars).
Điểm = P("yes"). --pool: chỉ chấm N tài liệu Việt,Trung đầu; phần còn lại giữ thứ tự cũ, xếp sau (điểm -1).
Kết quả (--quota 0,0 = giữ mọi ứng viên để dyn_cut.py cắt theo điểm):
    results/<tên>_q3r4Bprr_all.jsonl    thứ tự theo điểm reranker  ← dùng bản này (prrf kém hơn, exp-066)
    results/<tên>_q3r4Bprrf_all.jsonl   RRF(k=60) giữa thứ tự cũ và thứ tự reranker
Điểm lưu đệm sau mỗi khối --shard cặp ở results/qwen_rerank_cache_q3r4B_passage.pkl → chạy lại chỉ chấm cặp mới.
Bộ nhớ: 4B fp16 ~8 GB VRAM; --tokens-per-batch 24000 bị OOM trên 16 GB → 12000.
"""

import os
import glob
import json
import time
import pickle
import argparse

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from tqdm import tqdm

from make_submission import chunk_doc, MAX_CHARS, CHUNK_CACHE

CORPUS = "clean/corpus"
QUERIES = "btc_data_v2/query.parquet"
TRANSLATED = "results/queries_translated.jsonl"
RRF_K = 60

MODEL = "Qwen/Qwen3-Reranker-4B"
CACHE = "results/qwen_rerank_cache.pkl"  # chỉ cho MODEL + --text head (giữ khoá cũ)
INSTRUCT = "Given a Vietnamese patient's medical question, judge whether the document is relevant to it"
PREFIX = ("<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct "
          "provided. Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n<|im_start|>user\n")
SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def interleave(by_lang, quota):
    """Xen kẽ các danh sách theo tỉ lệ hạn mức như search_docs.fuse."""
    merged = []
    for gi, (lang, docs) in enumerate(by_lang.items()):
        merged += [((j + 1) / quota[lang], gi, d, lang) for j, d in enumerate(docs)]
    merged.sort()
    return [m[2] for m in merged], [m[3] for m in merged]


def best_passages(rows, docs, qtext):
    """(câu, tài liệu) → đoạn khớp nhất theo BGE-M3, chọn đúng như make_submission.py (dùng chung chunk_cache.pkl).
    36,6% bài Việt có đoạn khớp nhất nằm sau ký tự 2.000 (embed_tail.py) → reranker đọc đầu bài sẽ bỏ lỡ."""
    import torch
    from sentence_transformers import SentenceTransformer

    lang_of = {d: l for r in rows for d, l in zip(r["doc_ids"], r["langs"])}
    chunks = {d: chunk_doc(docs[d][1], MAX_CHARS.get(l, 1000)) for d, l in lang_of.items() if d in docs}
    cache = pickle.load(open(CHUNK_CACHE, "rb")) if os.path.exists(CHUNK_CACHE) else {}
    todo = [d for d in chunks if d not in cache or cache[d][0] != chunks[d]]
    flat = [(d, i) for d in todo for i in range(len(chunks[d]))]
    print(f"Đoạn văn: {len(chunks):,} tài liệu | có sẵn vector {len(chunks) - len(todo):,} | "
          f"mã hoá mới {len(todo):,} tài liệu = {len(flat):,} đoạn")
    model = SentenceTransformer("BAAI/bge-m3", device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = 512
    enc = lambda xs: model.encode(xs, batch_size=64, normalize_embeddings=True, convert_to_numpy=True,
                                  show_progress_bar=len(xs) > 2000).astype(np.float32)
    if flat:
        new = enc([f"{docs[d][0]}\n{chunks[d][i]}" for d, i in flat]).astype(np.float16)
        o = 0
        for d in todo:
            cache[d] = (chunks[d], new[o:o + len(chunks[d])])
            o += len(chunks[d])
        pickle.dump(cache, open(CHUNK_CACHE + ".tmp", "wb"), protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(CHUNK_CACHE + ".tmp", CHUNK_CACHE)
    qids = [r["query_id"] for r in rows]
    qv = {l: dict(zip(qids, enc([qtext[l].get(q, qtext["vi"][q]) for q in qids]))) for l in qtext}
    del model
    torch.cuda.empty_cache()
    out = {}
    for r in rows:
        q = r["query_id"]
        for d, l in zip(r["doc_ids"], r["langs"]):
            if chunks.get(d):
                cv = cache[d][1].astype(np.float32)
                s = cv @ qv["vi"][q]
                if l in qv:
                    s = np.maximum(s, cv @ qv[l][q])
                out[(q, d)] = chunks[d][int(np.argmax(s))]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True, help="Danh sách gộp rộng (vd D_wide.jsonl: 300 Việt + 130 Trung)")
    ap.add_argument("--quota", default="175,75", help="Số tài liệu Việt,Trung giữ lại mỗi câu")
    ap.add_argument("--pool", default="0,0", help="Chỉ chấm N tài liệu Việt,Trung đầu của --docs (0 = tất cả)")
    ap.add_argument("--head-vi", type=int, default=800)
    ap.add_argument("--head-zh", type=int, default=500)
    ap.add_argument("--limit", type=int, default=0,
                    help="Chỉ chấm N câu đầu; câu chưa chấm giữ thứ tự cũ trong file kết quả")
    ap.add_argument("--tokens-per-batch", type=int, default=24000)
    ap.add_argument("--model", default=MODEL, help="vd Qwen/Qwen3-Reranker-0.6B (nhanh hơn 4B ~5 lần)")
    ap.add_argument("--text", choices=["head", "passage"], default="head",
                    help="head = tiêu đề + đầu bài; passage = tiêu đề + đoạn khớp nhất (như chunk được nộp)")
    ap.add_argument("--passage-chars", type=int, default=2000, help="Cắt đoạn văn tối đa N ký tự")
    ap.add_argument("--tag", default=None, help="Tiền tố tên file kết quả (mặc định q3rr/q3rrf)")
    ap.add_argument("--load-8bit", action="store_true", help="Nạp trọng số 8-bit (cần bitsandbytes) — cho Qwen3-Reranker-8B")
    ap.add_argument("--shard", type=int, default=40000, help="Số cặp mỗi khối tách token + chấm (giới hạn RAM)")
    args = ap.parse_args()
    if args.model == MODEL and args.text == "head":
        cache_path, tag_rr = CACHE, args.tag or "q3"
    else:
        slug = args.model.split("/")[-1].replace("Qwen3-Reranker-", "q3r").replace(".", "")
        cache_path, tag_rr = f"results/qwen_rerank_cache_{slug}_{args.text}.pkl", args.tag or f"{slug}{args.text[0]}"
    quota = dict(zip(("vi", "zh"), map(int, args.quota.split(","))))
    pool = dict(zip(("vi", "zh"), map(int, args.pool.split(","))))
    head = {"vi": args.head_vi, "zh": args.head_zh}

    res = [json.loads(l) for l in open(args.docs, encoding="utf-8")]
    for r in res:  # cắt pool theo từng ngôn ngữ, giữ thứ tự cũ
        r["_full"] = list(zip(r["doc_ids"], r["langs"]))  # ngoài pool: không chấm, xếp sau theo thứ tự cũ
        seen = {"vi": 0, "zh": 0}
        keep = []
        for d, l in zip(r["doc_ids"], r["langs"]):
            seen[l] = seen.get(l, 0) + 1
            if l in pool and (not pool[l] or seen[l] <= pool[l]):
                keep.append((d, l))
        r["doc_ids"], r["langs"] = [d for d, _ in keep], [l for _, l in keep]
    q = pd.read_parquet(QUERIES)
    qtext = {"vi": dict(zip(q["id"].astype(int), q["query"]))}
    tr = {r["id"]: r for r in map(json.loads, open(TRANSLATED, encoding="utf-8"))}
    qtext["zh"] = {i: tr[i]["zh"] for i in tr}

    need = {d for r in res for d, _ in r["_full"]}
    docs = {}
    for p in tqdm(sorted(glob.glob(f"{CORPUS}/*.parquet")), desc="Đọc tài liệu"):
        t = pq.read_table(p, columns=["doc_id", "title", "text"]).to_pandas()
        t = t[t["doc_id"].isin(need)]
        docs.update({d: (ti or "", tx) for d, ti, tx in zip(t["doc_id"], t["title"], t["text"])})

    CACHE_PATH = cache_path
    cache = pickle.load(open(CACHE_PATH, "rb")) if os.path.exists(CACHE_PATH) else {}
    key = (lambda qid, d, l: (qid, d, head[l])) if args.text == "head" else (lambda qid, d, l: (qid, d))
    rows = res[:args.limit or None]
    passages = {}
    if args.text == "passage":
        qtext["en"] = {i: tr[i]["en"] for i in tr}
        need_rows = [{**r, "doc_ids": [d for d, l in zip(r["doc_ids"], r["langs"]) if key(r["query_id"], d, l) not in cache],
                      "langs": [l for d, l in zip(r["doc_ids"], r["langs"]) if key(r["query_id"], d, l) not in cache]}
                     for r in rows]
        if any(r["doc_ids"] for r in need_rows):
            passages = best_passages(need_rows, docs, qtext)
            __import__("gc").collect()  # nhả bộ nhớ đệm vector đoạn (~4 GB) trước khi nạp reranker
    texts, keys = [], []
    for r in rows:
        for d, lang in zip(r["doc_ids"], r["langs"]):
            if key(r["query_id"], d, lang) in cache or d not in docs:
                continue
            ti, tx = docs[d]
            if args.text == "passage":
                p = passages.get((r["query_id"], d))
                if p is None:
                    continue
                body = (p if p.startswith(ti) else f"{ti}\n{p}")[:args.passage_chars]
            else:
                body = (tx if tx.startswith(ti) else f"{ti}\n{tx}")[:head[lang]]
            query = qtext[lang].get(r["query_id"], qtext["vi"][r["query_id"]])
            texts.append(f"{PREFIX}<Instruct>: {INSTRUCT}\n<Query>: {query}\n<Document>: {body}{SUFFIX}")
            keys.append(key(r["query_id"], d, lang))
    print(f"{len(res[:args.limit or None])} câu | {len(texts):,} cặp cần chấm | đã có sẵn {len(cache):,}")

    if texts:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        tok = AutoTokenizer.from_pretrained(args.model, padding_side="left")
        if args.load_8bit:  # 8B fp16 ≈ 16 GB không vừa thẻ 16 GB → trọng số 8-bit (bitsandbytes), lm_head giữ fp16
            from transformers import BitsAndBytesConfig
            model = AutoModelForCausalLM.from_pretrained(
                args.model, dtype=torch.float16, attn_implementation="sdpa", device_map="cuda",
                quantization_config=BitsAndBytesConfig(load_in_8bit=True)).eval()
        else:
            model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.float16, attn_implementation="sdpa")
            model = model.cuda().eval()
        yes, no = tok.convert_tokens_to_ids("yes"), tok.convert_tokens_to_ids("no")
        # chỉ 2 hàng của lm_head ở token cuối — logits đủ từ vựng ở mọi vị trí tốn ~7 GB mỗi lô
        head_w = model.get_output_embeddings().weight[[no, yes]]
        # Tách token + chấm THEO KHỐI: tách token 420K cặp một lần ≈ 170 triệu số nguyên Python → hết 29 GB RAM (26/10)
        t0, n_tok = time.time(), 0
        pbar = tqdm(total=len(texts), desc="Chấm", unit="cặp", smoothing=0.05)
        for s0 in range(0, len(texts), args.shard):
            ids = tok(texts[s0:s0 + args.shard], add_special_tokens=False)["input_ids"]
            n_tok += sum(map(len, ids))
            order = np.argsort([len(x) for x in ids])  # gom cặp cùng độ dài → ít padding
            batches, cur = [], []
            for i in order:
                if cur and (len(cur) + 1) * len(ids[i]) > args.tokens_per_batch:
                    batches.append(cur)
                    cur = []
                cur.append(i)
            batches.append(cur)
            for b in batches[::-1]:  # lô dài nhất trước → lỗi thiếu VRAM lộ sớm
                enc = tok.pad({"input_ids": [ids[i] for i in b]}, padding=True, return_tensors="pt").to("cuda")
                with torch.no_grad():
                    logits = model.model(**enc).last_hidden_state[:, -1, :] @ head_w.T
                p = torch.log_softmax(logits.float(), 1)[:, 1].exp()
                for i, s in zip(b, p.cpu().numpy()):
                    cache[keys[s0 + i]] = float(s)
                pbar.update(len(b))
            del ids, batches
            pickle.dump(cache, open(CACHE_PATH + ".tmp", "wb"), protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(CACHE_PATH + ".tmp", CACHE_PATH)  # lưu sau mỗi khối → dừng giữa chừng mất tối đa 1 khối
        pbar.close()
        dt = time.time() - t0
        print(f"  {len(texts):,} cặp trong {dt / 60:.1f} phút = {len(texts) / dt:.1f} cặp/giây, "
              f"TB {n_tok / len(texts):.0f} token/cặp")

    base = os.path.basename(args.docs).replace(".jsonl", "")
    keep_all = not any(quota.values())  # --quota 0,0: giữ mọi ứng viên, chỉ đổi thứ tự (để dyn_cut.py cắt sau)
    tag = "all" if keep_all else f"{quota['vi']}-{quota['zh']}"
    outs = {f"{tag_rr}rr": [], f"{tag_rr}rrf": []}
    for r in res:
        old = {l: [d for d, x in r["_full"] if x == l and d in docs] for l in quota}
        q = {l: len(old[l]) for l in old} if keep_all else quota
        sc = {l: {d: cache.get(key(r["query_id"], d, l), -1.0) for d in old[l]} for l in quota}
        rr = {l: sorted(old[l], key=lambda d: -sc[l][d]) for l in quota}  # chưa chấm = -1 → cuối, giữ thứ tự cũ
        rrf, fsc = {}, {}
        for l in quota:
            f = {}
            for ranking in (old[l], rr[l]):
                for k, d in enumerate(ranking):
                    f[d] = f.get(d, 0.0) + 1 / (RRF_K + k + 1)
            rrf[l], fsc[l] = sorted(old[l], key=lambda d: -f[d]), f
        # scores phải khớp thứ tự của từng bản (dyn_cut.py cắt theo scores)
        for name, by_lang, score in ((f"{tag_rr}rr", rr, sc), (f"{tag_rr}rrf", rrf, fsc)):
            by_lang = {l: v[:q[l]] for l, v in by_lang.items() if q[l]}
            ids_, ls = interleave(by_lang, {l: q[l] for l in by_lang})
            outs[name].append({"query_id": r["query_id"], "query": r.get("query", ""), "doc_ids": ids_,
                               "scores": [score[l][d] for d, l in zip(ids_, ls)], "langs": ls})
    for name, rows in outs.items():
        path = f"results/{base}_{name}_{tag}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  → {path}")


if __name__ == "__main__":
    main()
