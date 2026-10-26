"""
HyDE — sinh đoạn trả lời giả định cho từng câu hỏi bằng Qwen3-8B (Ollama), rồi tìm bằng vector của đoạn đó.

    python hyde.py --generate          # → results/queries_hyde.jsonl {id, vi, zh} (chạy lại sẽ bỏ qua câu đã có)
    python hyde.py --search            # → results/run_dense_hyde_vi.jsonl, run_dense_hyde_zh.jsonl

Câu hỏi ngắn (trung vị 18 từ) còn bài đích là bài viết / câu trả lời dài: vector của một đoạn "giống bài đích"
nằm gần bài đích hơn vector câu hỏi. Vector tìm = chuẩn hoá(câu hỏi cùng ngôn ngữ + đoạn giả định).
Dùng khi gộp như các lượt khác: search_docs.py --only-fuse --weights ...,dense_hyde_vi=1,dense_hyde_zh=1
"""

import os
import json
import glob
import argparse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
from tqdm import tqdm

import search_docs as s

OUT = "results/queries_hyde.jsonl"
OLLAMA = "http://localhost:11434/api/chat"
SYSTEM = (
    "You are an experienced physician. For the Vietnamese patient question, write two short answer passages "
    "the way a doctor answers on a medical website:\n"
    "1. vi: Vietnamese, about 120 words, like an answer on a Vietnamese health website.\n"
    "2. zh: Simplified Chinese, about 200 characters, like a doctor's answer on a Chinese medical Q&A site.\n"
    "Name the likely conditions, causes, tests and treatments with standard medical terms. "
    "Keep every number, drug name and abbreviation from the question. No disclaimers, no greetings."
)
SCHEMA = {
    "type": "object",
    "properties": {"vi": {"type": "string"}, "zh": {"type": "string"}},
    "required": ["vi", "zh"],
}


def ask(query, model):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": query}],
        "stream": False,
        "think": False,
        "format": SCHEMA,
        "options": {"temperature": 0, "num_predict": 900},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.loads(json.loads(r.read())["message"]["content"])
    return out["vi"].strip(), out["zh"].strip()


def generate(model, workers):
    q = pd.read_parquet(s.QUERIES)
    done = set()
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            done = {json.loads(l)["id"] for l in f}
    todo = [(int(i), t) for i, t in zip(q["id"], q["query"]) if int(i) not in done]
    print(f"{len(q)} câu, đã có {len(done)}, còn {len(todo)}")
    errors = 0
    with open(OUT, "a", encoding="utf-8") as fout, ThreadPoolExecutor(workers) as pool:
        futs = {pool.submit(ask, t, model): i for i, t in todo}
        for f in tqdm(as_completed(futs), total=len(futs), unit="câu"):
            try:
                vi, zh = f.result()
            except Exception as e:
                errors += 1
                tqdm.write(f"  lỗi câu {futs[f]}: {str(e)[:100]}")
                continue
            fout.write(json.dumps({"id": futs[f], "vi": vi, "zh": zh}, ensure_ascii=False) + "\n")
            fout.flush()
    print(f"Xong → {OUT}" + (f" ({errors} câu lỗi — chạy lại để sinh nốt)" if errors else ""))


def search():
    import torch
    from sentence_transformers import SentenceTransformer

    with open(OUT, encoding="utf-8") as f:
        hy = {r["id"]: r for r in map(json.loads, f)}
    qs = s.load_queries()
    qids = [i for i, _ in qs["vi"]]
    missing = [i for i in qids if i not in hy]
    assert not missing, f"thiếu đoạn giả định cho {len(missing)} câu — chạy --generate"
    model = SentenceTransformer("BAAI/bge-m3", device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = 512
    enc = lambda xs: model.encode(xs, batch_size=32, normalize_embeddings=True, convert_to_tensor=True).float()
    # câu hỏi cùng ngôn ngữ với nhóm tài liệu: Việt gốc / bản dịch Trung
    qv = {"vi": enc([t for _, t in qs["vi"]]) + enc([hy[i]["vi"] for i in qids]),
          "zh": enc([t for _, t in qs["zh"]]) + enc([hy[i]["zh"] for i in qids])}
    qv = {l: torch.nn.functional.normalize(v, dim=1).half() for l, v in qv.items()}
    del model
    torch.cuda.empty_cache()

    files = sorted(glob.glob(f"{s.EMB}/*.parquet.npy"))
    E = torch.from_numpy(np.concatenate([np.load(f) for f in files])).to("cuda")
    ids = np.concatenate([np.load(f[:-4] + ".ids.npy") for f in files])
    doc_group, _ = s.load_meta()
    grp = doc_group.reindex(ids).to_numpy()
    for lang in ("vi", "zh"):
        rows = np.where(grp == lang)[0]
        Eg = E.index_select(0, torch.from_numpy(rows).to("cuda"))
        all_ids, all_scores = [], []
        for i in tqdm(range(0, len(qids), 64), desc=f"HyDE {lang}"):
            sc, top = torch.topk(qv[lang][i:i + 64] @ Eg.T, s.POOL, dim=1)
            for srow, irow in zip(sc.float().cpu().numpy(), top.cpu().numpy()):
                all_ids.append(ids[rows[irow]])
                all_scores.append(srow)
        name = f"dense_hyde_{lang}"
        s.save_run(name, qs["vi"], all_ids, all_scores)
        print(f"  → results/run_{name}.jsonl")
        del Eg
        torch.cuda.empty_cache()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--workers", type=int, default=4, help="Số câu gửi Ollama cùng lúc")
    args = ap.parse_args()
    if args.generate:
        generate(args.model, args.workers)
    if args.search:
        search()


if __name__ == "__main__":
    main()
