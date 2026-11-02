"""
Gộp điểm hai reranker: trung bình P("yes") của Qwen3-Reranker-4B và 8B cho từng (câu, tài liệu) trong pool.

    python ensemble_rerank.py --a results/D_bi02_q3r4Bprr_all.jsonl --b results/D_bi02_q3r8Bprr_all.jsonl \
        --out results/D_bi02_q3rEnsprr_all.jsonl
    → dyn_cut.py --docs results/D_bi02_q3rEnsprr_all.jsonl --mean 140 --vi-share 0.75 --lo 80 --hi 400

Bộ dò (300 câu, Qwen3-14B + Gemma 3 12B): gộp hơn 4B +0,0048 (KTC95% +0,0026…+0,0071), hơn 8B riêng (exp-078).
Tài liệu ngoài pool (điểm -1 ở cả hai) giữ -1 và thứ tự cũ → dyn_cut không bao giờ giữ chúng, như bản 4B/8B.
"""

import json
import argparse

from qwen_rerank import interleave


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="Bản *_prr_all.jsonl của reranker thứ nhất")
    ap.add_argument("--b", required=True, help="Bản *_prr_all.jsonl của reranker thứ hai (cùng danh sách ứng viên)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    A = {r["query_id"]: r for r in map(json.loads, open(args.a, encoding="utf-8"))}
    B = {r["query_id"]: r for r in map(json.loads, open(args.b, encoding="utf-8"))}
    assert A.keys() == B.keys(), "hai file phải cùng tập câu hỏi"
    with open(args.out, "w", encoding="utf-8") as f:
        for q, a in A.items():
            sa, sb = dict(zip(a["doc_ids"], a["scores"])), dict(zip(B[q]["doc_ids"], B[q]["scores"]))
            assert sa.keys() == sb.keys(), f"câu {q}: hai file khác tập ứng viên"
            by = {}
            for d, lang in zip(a["doc_ids"], a["langs"]):
                s = (sa[d] + sb[d]) / 2 if sa[d] >= 0 and sb[d] >= 0 else -1.0
                by.setdefault(lang, []).append((d, s))
            by = {l: sorted(v, key=lambda x: -x[1]) for l, v in by.items()}  # sort ổn định: ngoài pool giữ thứ tự cũ
            ids, ls = interleave({l: [d for d, _ in v] for l, v in by.items()}, {l: len(v) for l, v in by.items()})
            sc = {d: s for v in by.values() for d, s in v}
            f.write(json.dumps({"query_id": q, "query": a.get("query", ""), "doc_ids": ids, "langs": ls,
                                "scores": [sc[d] for d in ids]}, ensure_ascii=False) + "\n")
    print(f"→ {args.out} ({len(A)} câu)")


if __name__ == "__main__":
    main()
