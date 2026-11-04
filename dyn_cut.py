"""
Số tài liệu THEO TỪNG CÂU (council-r03 MiMo-A / GPT-A) thay vì cố định.

    python dyn_cut.py --docs results/D_wide.jsonl --mean 250 --vi-share 0.7 --lo 80 --hi 400 --out results/DC.jsonl

--docs: danh sách gộp RỘNG (vd 300 Việt + 130 Trung) có trường scores = điểm RRF trong từng ngôn ngữ.
Với mỗi câu và mỗi ngôn ngữ: giữ các tài liệu có điểm RRF ≥ tau_lang · điểm RRF cao nhất của câu đó (tỉ lệ tương đối,
vì độ lớn tuyệt đối khác nhau giữa các câu). tau được dò nhị phân để trung bình số tài liệu = mean · share.
Tổng mỗi câu bị kẹp trong [lo, hi]. Không dùng nhãn.
"""

import json
import argparse

import numpy as np


def cut(rows, lang, tau):
    out = []
    for r in rows:
        sc = [s for s, l in zip(r["scores"], r["langs"]) if l == lang]
        top = max(sc) if sc else 0
        out.append(sum(1 for s in sc if s >= tau * top))
    return np.array(out)


def find_tau(rows, lang, target, lo_n, hi_n):
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        n = np.clip(cut(rows, lang, mid), lo_n, hi_n).mean()
        lo, hi = (mid, hi) if n > target else (lo, mid)
    return (lo + hi) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True)
    ap.add_argument("--mean", type=float, default=250)
    ap.add_argument("--vi-share", type=float, default=0.7)
    ap.add_argument("--lo", type=int, default=80, help="Số tài liệu tối thiểu mỗi câu (tổng)")
    ap.add_argument("--hi", type=int, default=400, help="Số tài liệu tối đa mỗi câu (tổng)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.docs, encoding="utf-8")]
    share = {"vi": args.vi_share, "zh": 1 - args.vi_share}
    n = {}
    for lang in ("vi", "zh"):
        t = find_tau(rows, lang, args.mean * share[lang], args.lo * share[lang], args.hi * share[lang])
        n[lang] = np.clip(cut(rows, lang, t), int(args.lo * share[lang]), int(args.hi * share[lang]))
        print(f"{lang}: tau {t:.3f} | số tài liệu TB {n[lang].mean():.0f}, p10 {np.percentile(n[lang], 10):.0f}, "
              f"p90 {np.percentile(n[lang], 90):.0f}")
    with open(args.out, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows):
            keep = {"vi": int(n["vi"][i]), "zh": int(n["zh"][i])}
            seen = {"vi": 0, "zh": 0}
            ids, langs, scores = [], [], []
            for d, l, s in zip(r["doc_ids"], r["langs"], r["scores"]):
                if l in keep and seen[l] < keep[l]:
                    seen[l] += 1
                    ids.append(d); langs.append(l); scores.append(s)
            r["doc_ids"], r["langs"], r["scores"] = ids, langs, scores
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tot = n["vi"] + n["zh"]
    print(f"tổng: TB {tot.mean():.0f}, min {tot.min()}, max {tot.max()} → {args.out}")


if __name__ == "__main__":
    main()
