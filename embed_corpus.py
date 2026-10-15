"""
Mã hoá corpus sạch bằng BGE-M3 → mỗi tài liệu 1 vector 1024 chiều (fp16).

    conda activate vibiomir
    python embed_corpus.py --test     # đo tốc độ trên clean_test/
    python embed_corpus.py            # toàn bộ clean/corpus → emb/

Dừng bằng Ctrl+C, chạy lại sẽ bỏ qua các phần đã mã hoá xong.
"""

import os
import glob
import argparse

import numpy as np
import pyarrow.parquet as pq
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

MODEL = "BAAI/bge-m3"
MAX_TOKENS = 512
MAX_CHARS = 2000


def doc_input(title, text):
    s = text if (not title or text.startswith(title)) else f"{title}\n{text}"
    return s[:MAX_CHARS]


def up_to_date(part, out):
    base = os.path.join(out, os.path.basename(part))
    if not (os.path.exists(base + ".npy") and os.path.exists(base + ".ids.npy")):
        return False
    ids = pq.read_table(part, columns=["doc_id"])["doc_id"].to_numpy()
    return np.array_equal(np.load(base + ".ids.npy"), ids)


def try_reuse(part, out):
    """Phần corpus chỉ bị lọc bớt → lấy lại vector cũ, không cần mã hoá lại."""
    base = os.path.join(out, os.path.basename(part))
    if not (os.path.exists(base + ".npy") and os.path.exists(base + ".ids.npy")):
        return False
    pos = {d: i for i, d in enumerate(np.load(base + ".ids.npy").tolist())}
    ids = pq.read_table(part, columns=["doc_id"])["doc_id"].to_pylist()
    if not all(d in pos for d in ids):
        return False
    vecs = np.load(base + ".npy")[[pos[d] for d in ids]]
    np.save(base + ".npy.tmp.npy", vecs)
    os.replace(base + ".npy.tmp.npy", base + ".npy")
    np.save(base + ".ids.npy", np.asarray(ids, dtype=np.int64))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS, help="256 nhanh gấp đôi, 512 đủ ý hơn")
    args = ap.parse_args()

    src = "clean_test/corpus" if args.test else "clean/corpus"
    out = "emb_test" if args.test else "emb"
    os.makedirs(out, exist_ok=True)

    parts = sorted(glob.glob(f"{src}/*.parquet"))
    names = {os.path.basename(p) for p in parts}
    removed = 0
    for f in glob.glob(f"{out}/*.parquet.npy") + glob.glob(f"{out}/*.parquet.ids.npy"):
        if os.path.basename(f).split(".parquet")[0] + ".parquet" not in names:
            os.remove(f)
            removed += 1
    if removed:
        print(f"Đã xoá {removed} file vector của các phần không còn trong corpus")
    todo = [p for p in parts if not up_to_date(p, out)]
    reused = [p for p in tqdm(todo, desc="Dùng lại vector cũ") if try_reuse(p, out)] if todo else []
    if reused:
        print(f"Dùng lại vector cho {len(reused)} phần (chỉ bị lọc bớt tài liệu)")
    todo = [p for p in todo if p not in set(reused)]
    total = sum(pq.ParquetFile(p).metadata.num_rows for p in todo)
    print(f"{len(parts)} phần, còn {len(todo)} phần = {total:,} tài liệu cần mã hoá")
    if not todo:
        return

    model = SentenceTransformer(MODEL, device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = args.max_tokens

    pbar = tqdm(total=total, unit="bài", smoothing=0.05)
    for p in todo:
        t = pq.read_table(p, columns=["doc_id", "title", "text"])
        texts = [doc_input(a, b) for a, b in zip(t["title"].to_pylist(), t["text"].to_pylist())]
        vecs = model.encode(texts, batch_size=args.batch_size, normalize_embeddings=True,
                            convert_to_numpy=True, show_progress_bar=False).astype(np.float16)
        base = os.path.join(out, os.path.basename(p))
        np.save(base + ".npy.tmp.npy", vecs)
        os.replace(base + ".npy.tmp.npy", base + ".npy")
        # ghi ids SAU vector: ids khớp corpus ⇔ vector của phần này đã đúng
        np.save(base + ".ids.npy", np.asarray(t["doc_id"].to_pylist(), dtype=np.int64))
        pbar.update(len(texts))
    pbar.close()
    print(f"Xong → {out}/")


if __name__ == "__main__":
    main()
