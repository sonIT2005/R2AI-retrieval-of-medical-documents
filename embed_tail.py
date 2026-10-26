"""
Mã hoá PHẦN SAU của tài liệu tiếng Việt dài bằng BGE-M3 → emb_tail/ (bổ sung cho emb/, vốn chỉ thấy 2.000 ký tự đầu).

    conda activate vibiomir
    python embed_tail.py              # tối đa 2 cửa sổ 2.000 ký tự, bắt đầu từ ký tự 1.800, bước 1.800

Đo trên top-100 bài nộp: 36,6% tài liệu Việt có đoạn khớp câu hỏi nhất nằm sau ký tự 2.000 (tiếng Trung chỉ 2%).
search_docs.py dùng emb_tail/ trong lượt dense_vi_vimax: điểm tài liệu = max(cos đầu bài, cos các cửa sổ sau).
Dừng bằng Ctrl+C, chạy lại sẽ bỏ qua các phần đã xong.
"""

import os
import glob
import argparse

import numpy as np
import pyarrow.parquet as pq
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from search_docs import load_meta

START, STEP, WIN = 1800, 1800, 2000


def windows(text, max_windows):
    out, a = [], START
    while a < len(text) and len(out) < max_windows:
        out.append(text[a:a + WIN])
        a += STEP
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-windows", type=int, default=2)
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args()

    out = "emb_tail"
    os.makedirs(out, exist_ok=True)
    doc_group, _ = load_meta()
    vi_ids = set(doc_group.index[doc_group.to_numpy() == "vi"].tolist())

    parts = sorted(glob.glob("clean/corpus/*.parquet"))
    todo = [p for p in parts if not os.path.exists(os.path.join(out, os.path.basename(p) + ".ids.npy"))]
    print(f"{len(parts)} phần, còn {len(todo)} phần cần mã hoá phần sau")
    if not todo:
        return

    model = SentenceTransformer("BAAI/bge-m3", device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = 512
    for p in tqdm(todo, desc="Phần corpus"):
        t = pq.read_table(p, columns=["doc_id", "text"])
        ids, texts = [], []
        for d, x in zip(t["doc_id"].to_pylist(), t["text"].to_pylist()):
            if d in vi_ids:
                for w in windows(x, args.max_windows):
                    ids.append(d)
                    texts.append(w)
        base = os.path.join(out, os.path.basename(p))
        vecs = (model.encode(texts, batch_size=args.batch_size, normalize_embeddings=True, convert_to_numpy=True,
                             show_progress_bar=False).astype(np.float16) if texts else np.zeros((0, 1024), np.float16))
        np.save(base + ".npy.tmp.npy", vecs)
        os.replace(base + ".npy.tmp.npy", base + ".npy")
        np.save(base + ".ids.npy", np.asarray(ids, dtype=np.int64))  # ghi ids SAU vector: có ids ⇔ phần này xong
    print(f"Xong → {out}/")


if __name__ == "__main__":
    main()
