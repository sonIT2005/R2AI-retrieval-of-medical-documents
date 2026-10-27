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


KEEP = None  # tập doc_id thuộc --group (None = mọi tài liệu)


def part_ids(part):
    ids = pq.read_table(part, columns=["doc_id"])["doc_id"].to_pylist()
    return ids if KEEP is None else [d for d in ids if d in KEEP]


def up_to_date(part, out):
    base = os.path.join(out, os.path.basename(part))
    if not (os.path.exists(base + ".npy") and os.path.exists(base + ".ids.npy")):
        return False
    return np.array_equal(np.load(base + ".ids.npy"), np.asarray(part_ids(part), dtype=np.int64))


def try_reuse(part, out):
    """Phần corpus chỉ bị lọc bớt → lấy lại vector cũ, không cần mã hoá lại."""
    base = os.path.join(out, os.path.basename(part))
    if not (os.path.exists(base + ".npy") and os.path.exists(base + ".ids.npy")):
        return False
    pos = {d: i for i, d in enumerate(np.load(base + ".ids.npy").tolist())}
    ids = part_ids(part)
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
    ap.add_argument("--model", default=MODEL, help="Mô hình embedding (mặc định BGE-M3)")
    ap.add_argument("--out", default=None, help="Thư mục vector (mặc định emb/; mô hình khác nên dùng thư mục khác)")
    ap.add_argument("--group", choices=["vi", "zh", "en"], default=None,
                    help="Chỉ mã hoá tài liệu thuộc một nhóm ngôn ngữ (nhóm theo website như search_docs.py)")
    args = ap.parse_args()

    src = "clean_test/corpus" if args.test else "clean/corpus"
    out = args.out or ("emb_test" if args.test else "emb")
    os.makedirs(out, exist_ok=True)
    global KEEP
    if args.group:
        from search_docs import load_meta
        doc_group, _ = load_meta()
        KEEP = set(doc_group.index[doc_group.to_numpy() == args.group].tolist())
        print(f"Chỉ mã hoá nhóm {args.group}: {len(KEEP):,} tài liệu")

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
    total = sum(len(part_ids(p)) for p in todo)
    print(f"{len(parts)} phần, còn {len(todo)} phần = {total:,} tài liệu cần mã hoá")
    if not todo:
        return

    model = SentenceTransformer(args.model, device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = args.max_tokens

    pbar = tqdm(total=total, unit="bài", smoothing=0.05)
    for p in todo:
        t = pq.read_table(p, columns=["doc_id", "title", "text"]).to_pandas()
        if KEEP is not None:
            t = t[t["doc_id"].isin(KEEP)]
        texts = [doc_input(a, b) for a, b in zip(t["title"], t["text"])]
        vecs = (model.encode(texts, batch_size=args.batch_size, normalize_embeddings=True, convert_to_numpy=True,
                             show_progress_bar=False).astype(np.float16) if texts
                else np.zeros((0, model.get_sentence_embedding_dimension()), np.float16))
        base = os.path.join(out, os.path.basename(p))
        np.save(base + ".npy.tmp.npy", vecs)
        os.replace(base + ".npy.tmp.npy", base + ".npy")
        # ghi ids SAU vector: ids khớp corpus ⇔ vector của phần này đã đúng
        np.save(base + ".ids.npy", np.asarray(t["doc_id"].tolist(), dtype=np.int64))
        pbar.update(len(texts))
    pbar.close()
    print(f"Xong → {out}/")


if __name__ == "__main__":
    main()
