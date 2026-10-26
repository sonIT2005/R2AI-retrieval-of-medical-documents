"""
Mở rộng câu hỏi bằng phản hồi giả (Rocchio trên vector BGE-M3) — council-r03/Kimi-A.

    python prf.py --seeds results/D_A9_n250.jsonl --m 5 --beta 0.5

Với mỗi câu: q' = chuẩn hoá(q + beta · trung bình vector của m tài liệu ĐẦU mỗi ngôn ngữ trong --seeds)
rồi tìm lại top-300 trong nhóm Việt và nhóm Trung → results/run_dense_vi_viprf.jsonl, run_dense_vi_zhprf.jsonl
(dùng như các lượt khác trong search_docs.py --only-fuse, vd --weights dense_vi_vi=0,dense_vi_viprf=1).
"""

import json
import argparse

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

import search_docs as s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="Danh sách gộp đã có (lấy m tài liệu đầu mỗi ngôn ngữ làm phản hồi)")
    ap.add_argument("--m", type=int, default=5)
    ap.add_argument("--beta", type=float, default=0.5)
    ap.add_argument("--suffix", default="prf")
    args = ap.parse_args()

    seeds = {r["query_id"]: r for r in map(json.loads, open(args.seeds, encoding="utf-8"))}
    q = pd.read_parquet(s.QUERIES)
    qids = [int(i) for i in q["id"]]
    model = SentenceTransformer("BAAI/bge-m3", device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = 512
    qv = model.encode(list(q["query"]), batch_size=64, normalize_embeddings=True, convert_to_tensor=True).float()
    del model
    torch.cuda.empty_cache()

    files = sorted(__import__("glob").glob(f"{s.EMB}/*.parquet.npy"))
    E = torch.from_numpy(np.concatenate([np.load(f) for f in files])).to("cuda")
    ids = np.concatenate([np.load(f[:-4] + ".ids.npy") for f in files])
    row_of = {d: i for i, d in enumerate(ids.tolist())}
    doc_group, _ = s.load_meta()
    grp = doc_group.reindex(ids).to_numpy()

    for lang in ("vi", "zh"):
        rows = np.where(grp == lang)[0]
        Eg = E.index_select(0, torch.from_numpy(rows).to("cuda"))
        Q = qv.clone()
        for i, qid in enumerate(qids):
            r = seeds.get(qid, {"doc_ids": [], "langs": []})
            top = [row_of[d] for d, l in zip(r["doc_ids"], r["langs"]) if l == lang and d in row_of][:args.m]
            if top:
                Q[i] = Q[i] + args.beta * E[top].float().mean(0)
        Q = torch.nn.functional.normalize(Q, dim=1).half()
        all_ids, all_scores = [], []
        for i in tqdm(range(0, len(qids), 64), desc=f"PRF {lang}"):
            sc, top = torch.topk(Q[i:i + 64] @ Eg.T, s.POOL, dim=1)
            for srow, irow in zip(sc.float().cpu().numpy(), top.cpu().numpy()):
                all_ids.append(ids[rows[irow]])
                all_scores.append(srow)
        name = f"dense_vi_{lang}{args.suffix}"
        s.save_run(name, [(i, "") for i in qids], all_ids, all_scores)
        print(f"  → results/run_{name}.jsonl")
        del Eg
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
