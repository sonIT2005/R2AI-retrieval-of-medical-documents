"""
Sắp lại danh sách tài liệu để N tài liệu ĐẦU (những tài liệu được make_submission kèm chunk) theo hạn mức ngôn ngữ riêng,
còn TẬP tài liệu nộp giữ nguyên.

Lý do (EXPERIMENTS exp-014…017): tập tài liệu tốt nhất ở ~210 Việt / 90 Trung, nhưng F2 chunk tăng khi top-100 có nhiều
tài liệu Việt hơn → tách hạn mức chunk khỏi hạn mức tài liệu.

    python chunk_quota.py --docs results/T_210-90.jsonl --chunk-quota 85,15 --out results/T_210-90_cq85-15.jsonl
    python make_submission.py --docs results/T_210-90_cq85-15.jsonl --chunk-chars 4000:100 --compress bzip2
"""

import json
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True)
    ap.add_argument("--chunk-quota", required=True, help="Số tài liệu Việt,Trung trong nhóm đầu (vd 85,15)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    qv, qz = map(int, args.chunk_quota.split(","))

    with open(args.docs, encoding="utf-8") as f, open(args.out, "w", encoding="utf-8") as g:
        for r in map(json.loads, f):
            pairs = list(zip(r["doc_ids"], r["langs"], r["scores"]))
            vi = [p for p in pairs if p[1] == "vi"]
            zh = [p for p in pairs if p[1] == "zh"]
            # nhóm đầu: xen kẽ theo tỉ lệ như search_docs.fuse; phần còn lại giữ thứ tự cũ
            head = sorted([((j + 1) / qv, 0, p) for j, p in enumerate(vi[:qv])] +
                          [((j + 1) / qz, 1, p) for j, p in enumerate(zh[:qz])], key=lambda x: (x[0], x[1]))
            head = [p for _, _, p in head]
            used = {p[0] for p in head}
            rest = [p for p in pairs if p[0] not in used]
            out = head + rest
            assert sorted(d for d, _, _ in out) == sorted(r["doc_ids"]), "tập tài liệu phải giữ nguyên"
            r["doc_ids"], r["langs"], r["scores"] = [p[0] for p in out], [p[1] for p in out], [p[2] for p in out]
            g.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
