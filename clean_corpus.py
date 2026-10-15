"""
Làm sạch corpus: HTML trong SQLite → parquet (doc_id, url, host, src, title, text, lang, n_chars).

    python clean_corpus.py --test     # thử nhanh trên ít dữ liệu → clean_test/
    python clean_corpus.py            # chạy toàn bộ → clean/corpus/*.parquet

Chạy lại sẽ bỏ qua phần đã xong.
"""

import os
import re
import glob
import json
import random
import sqlite3
import logging
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import zstandard
import trafilatura
import lxml.html
from tqdm import tqdm

SRC_DIRS = ["db_extra", "db", "db_alt", "db_cc", "db_wayback"]
OK_FILTER = "status = 200 AND kind IN ('ok', 'raw')"
BOILER_SAMPLE = 1500
BOILER_MIN_FRAC = 0.03
MAX_HTML = 3_000_000
MIN_CHARS = 30
FALLBACK_BELOW = 100
CAPTCHA_MARKERS = ("滑动拼图验证".encode(),)
SCHEMA = pa.schema([
    ("doc_id", pa.int64()), ("url", pa.string()), ("host", pa.string()), ("src", pa.string()),
    ("title", pa.string()), ("text", pa.string()), ("lang", pa.string()), ("n_chars", pa.int64()),
])

CJK = re.compile(r"[一-鿿]")
VI = re.compile(r"[ăâđêôơưàảãáạằẳẵắặầẩẫấậèẻẽéẹềểễếệìỉĩíịòỏõóọồổỗốộờởỡớợùủũúụừửữứựỳỷỹýỵ]", re.I)
LATIN = re.compile(r"[A-Za-z]")

KEEP_IDS = "btc_data_v2/links_corpus_vi_en_zh.parquet"

_dz = None
KEEP = None  # mảng id đã sắp xếp của corpus BTC; None = giữ tất cả


def load_keep(path):
    return np.sort(pq.read_table(path, columns=["id"])["id"].to_numpy())


def init_worker(keep_path=None):
    global KEEP
    logging.disable(logging.WARNING)
    if keep_path and KEEP is None:
        KEEP = load_keep(keep_path)


def decompress(kind, blob):
    global _dz
    if kind == "raw":
        return blob
    if _dz is None:
        _dz = zstandard.ZstdDecompressor()
    return _dz.decompress(blob, max_output_size=64_000_000)


def norm_line(line):
    return " ".join(line.split())


CHARSET_RE = re.compile(rb"""charset\s*=\s*["']?\s*([\w-]+)""", re.I)
BLOB_RE = re.compile(r"[A-Za-z0-9+/=_-]{120,}")  # chuỗi base64/mã hoá, không phải văn bản
GB_FAMILY = {"gb2312", "gbk", "gb_2312-80", "x-gbk", "gb18030", "euc-cn"}


def decode_html(raw, ctype=""):
    """Tự giải mã theo bảng mã khai báo (trafilatura hay đoán sai trang GBK)."""
    raw = raw[:MAX_HTML]
    m = CHARSET_RE.search((ctype or "").encode()) or CHARSET_RE.search(raw[:4096])
    enc = m.group(1).decode("ascii", "ignore").lower() if m else ""
    if enc in GB_FAMILY:
        enc = "gb18030"
    if enc:
        try:
            return raw.decode(enc, errors="replace")
        except LookupError:
            pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("gb18030", errors="replace")


def body_lines(html):
    """Dự phòng: toàn bộ chữ trong thân trang, bỏ script/menu/header/footer."""
    try:
        root = lxml.html.fromstring(html)
    except Exception:
        return []
    for bad in root.xpath("//script|//style|//noscript|//nav|//header|//footer"):
        bad.drop_tree()
    body = root.find("body")
    lines = (norm_line(s) for s in (body if body is not None else root).itertext())
    return [l for l in lines if len(l) > 1]


def extract(html):
    """html: str. Trả về (title, list các dòng nội dung)."""
    title, text = "", ""
    try:
        doc = trafilatura.bare_extraction(
            html, favor_recall=True, include_tables=True, include_comments=False,
            deduplicate=False, with_metadata=True,
        )
        if doc is not None:
            title = getattr(doc, "title", None) or ""
            text = getattr(doc, "text", None) or ""
    except Exception:
        pass
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        title = m.group(1) if m else ""
    lines = [norm_line(l) for l in text.splitlines()]
    return norm_line(title), [l for l in lines if l]


def parse_pubmed(raw):
    """Bản ghi XML của API PubMed (efetch) → (tiêu đề bài, tóm tắt theo mục + từ khoá + MeSH)."""
    import lxml.etree as ET

    root = ET.fromstring(raw)
    txt = lambda el: norm_line("".join(el.itertext())) if el is not None else ""
    title = txt(root.find(".//ArticleTitle")) or txt(root.find(".//BookTitle"))
    lines = []
    for ab in root.iter("Abstract", "OtherAbstract"):
        for p in ab.findall("AbstractText"):
            body = txt(p)
            label = p.get("Label")
            if body:
                lines.append(f"{label}: {body}" if label else body)
    kws = [txt(k) for k in root.iter("Keyword") if txt(k)]
    if kws:
        lines.append("Keywords: " + "; ".join(kws))
    mesh = [txt(m) for m in root.iter("DescriptorName") if txt(m)]
    if mesh:
        lines.append("MeSH: " + "; ".join(mesh))
    return title, "\n".join(lines) if lines else title


def clean_record(raw, ctype, boiler):
    if raw.lstrip()[:20].startswith((b"<PubmedArticle", b"<PubmedBookArticle")):
        return parse_pubmed(raw)
    return clean_text(decode_html(raw, ctype), boiler)


def clean_text(html, boiler):
    """Trafilatura + lọc rác; nếu còn quá ít thì dùng chữ toàn trang (cũng lọc rác)."""
    title, lines = extract(html)
    kept = [l for l in lines if l not in boiler and not BLOB_RE.fullmatch(l)]
    if sum(map(len, kept)) < FALLBACK_BELOW:
        fb = [l for l in body_lines(html)
              if len(l) >= 6 and l not in boiler and not BLOB_RE.fullmatch(l)]
        if sum(map(len, fb)) > sum(map(len, kept)):
            kept = fb
    return title, "\n".join(kept)


def detect_lang(text):
    s = text[:3000]
    cjk, vi, latin = len(CJK.findall(s)), len(VI.findall(s)), len(LATIN.findall(s))
    if cjk and cjk >= 0.2 * (cjk + vi + latin):
        return "zh"
    if vi and vi >= 0.05 * (vi + latin):
        return "vi"
    return "en" if latin else "unk"


def db_tag(path):
    d, f = path.split(os.sep)[-2:]
    return f"{d}__{f[:-len('.sqlite')]}"


def invalidate_updated(dbs, out_dir):
    """File SQLite được tải lại sau lần làm sạch trước → xoá kết quả cũ của riêng file đó."""
    stale = []
    for p in dbs:
        tag = db_tag(p)
        boiler = os.path.join(out_dir, "boiler", f"{tag}.json")
        if os.path.exists(boiler) and os.path.getmtime(p) > os.path.getmtime(boiler):
            os.remove(boiler)
            for f in glob.glob(os.path.join(out_dir, "parts", f"{tag}__*.parquet")):
                os.remove(f)
            stale.append(tag)
    return stale


def plan_db(path, out_dir, rows_per_task, max_tasks):
    """Lấy danh sách id + học các dòng rác (boilerplate) của 1 file SQLite."""
    init_worker()
    tag = db_tag(path)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    ids = [r[0] for r in conn.execute(f"SELECT id FROM pages WHERE {OK_FILTER} ORDER BY id")]
    boiler_path = os.path.join(out_dir, "boiler", f"{tag}.json")
    if ids and not os.path.exists(boiler_path):
        sample = random.Random(0).sample(ids, min(BOILER_SAMPLE, len(ids)))
        counts = Counter()
        for i in range(0, len(sample), 500):
            batch = sample[i:i + 500]
            q = f"SELECT kind, ctype, html FROM pages WHERE id IN ({','.join('?' * len(batch))})"
            for kind, ctype, blob in conn.execute(q, batch):
                try:
                    raw = decompress(kind, blob)
                    if any(m in raw for m in CAPTCHA_MARKERS):
                        continue
                    if raw.lstrip()[:20].startswith((b"<PubmedArticle", b"<PubmedBookArticle")):
                        continue  # XML có cấu trúc, không có dòng rác giao diện để học
                    _, lines = extract(decode_html(raw, ctype))
                except Exception:
                    continue
                counts.update(set(lines))
        min_count = max(5, int(BOILER_MIN_FRAC * len(sample)))
        boiler = sorted(l for l, c in counts.items() if c >= min_count and len(l) < 400)
        with open(boiler_path, "w", encoding="utf-8") as f:
            json.dump(boiler, f, ensure_ascii=False)
    conn.close()
    tasks = [(path, ids[i:i + rows_per_task]) for i in range(0, len(ids), rows_per_task)]
    return tag, len(ids), tasks[:max_tasks] if max_tasks else tasks


def run_task(path, ids, out_dir):
    init_worker()
    tag = db_tag(path)
    out = os.path.join(out_dir, "parts", f"{tag}__{ids[0]}_{ids[-1]}.parquet")
    if os.path.exists(out):
        return 0
    with open(os.path.join(out_dir, "boiler", f"{tag}.json"), encoding="utf-8") as f:
        boiler = set(json.load(f))
    src = tag.split("__")[0]
    allowed = None if KEEP is None else set(np.intersect1d(np.asarray(ids), KEEP).tolist())
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    cols = defaultdict(list)
    q = f"SELECT id, url, kind, ctype, html FROM pages WHERE id BETWEEN ? AND ? AND {OK_FILTER}"
    for doc_id, url, kind, ctype, blob in conn.execute(q, (ids[0], ids[-1])):
        if allowed is not None and doc_id not in allowed:
            continue
        try:
            raw = decompress(kind, blob)
            if any(m in raw for m in CAPTCHA_MARKERS):
                continue
            title, text = clean_record(raw, ctype, boiler)
        except Exception:
            continue
        if len(text) < MIN_CHARS:
            continue
        cols["doc_id"].append(doc_id)
        cols["url"].append(url)
        cols["host"].append(tag.split("__")[1])
        cols["src"].append(src)
        cols["title"].append(title)
        cols["text"].append(text)
        cols["lang"].append(detect_lang(title + " " + text))
        cols["n_chars"].append(len(text))
    conn.close()
    tmp = out + ".tmp"
    pq.write_table(pa.table({f.name: cols[f.name] for f in SCHEMA}, schema=SCHEMA), tmp, compression="zstd")
    os.replace(tmp, out)
    return len(cols["doc_id"])


def finalize(out_dir, keep_path=None):
    """Bỏ trùng doc_id giữa các nguồn (giữ bản nhiều nội dung nhất) + chỉ giữ id thuộc corpus BTC."""
    keep = set(load_keep(keep_path).tolist()) if keep_path else None
    parts = sorted(glob.glob(os.path.join(out_dir, "parts", "*.parquet")))
    best = {}
    for i, p in enumerate(tqdm(parts, desc="Tìm bản tốt nhất")):
        t = pq.read_table(p, columns=["doc_id", "n_chars"])
        for d, n in zip(t["doc_id"].to_pylist(), t["n_chars"].to_pylist()):
            if keep is not None and d not in keep:
                continue
            if d not in best or n > best[d][1]:
                best[d] = (i, n)
    corpus_dir = os.path.join(out_dir, "corpus")
    os.makedirs(corpus_dir, exist_ok=True)
    for f in glob.glob(os.path.join(corpus_dir, "*.parquet")):
        os.remove(f)
    stats = Counter()
    chars = Counter()
    for i, p in enumerate(tqdm(parts, desc="Ghi corpus")):
        t = pq.read_table(p)
        mask = [d in best and best[d][0] == i for d in t["doc_id"].to_pylist()]
        t = t.filter(pa.array(mask, type=pa.bool_()))
        if t.num_rows:
            pq.write_table(t, os.path.join(corpus_dir, os.path.basename(p)), compression="zstd")
        for lang, n in zip(t["lang"].to_pylist(), t["n_chars"].to_pylist()):
            stats[lang] += 1
            chars[lang] += n
    total = sum(stats.values())
    print(f"\nCorpus sạch: {total:,} tài liệu → {corpus_dir}/")
    for lang, c in stats.most_common():
        print(f"  {lang:4s} {c:>10,} ({c / total * 100:5.1f}%)  TB {chars[lang] // max(c, 1):,} ký tự/bài")
    empty = sum(1 for _, n in best.values() if n < 50)
    print(f"  Bài gần như rỗng (<50 ký tự): {empty:,}")
    if keep is not None:
        print(f"  Độ phủ corpus BTC: {total:,} / {len(keep):,} ({total / len(keep) * 100:.1f}%)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="Thử trên 4 file, mỗi file 2 phần nhỏ")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--keep-ids", default=KEEP_IDS,
                    help="Parquet danh sách id của corpus BTC; truyền '' để giữ mọi tài liệu")
    args = ap.parse_args()
    keep_path = None if args.test or not args.keep_ids else args.keep_ids
    if keep_path:
        print(f"Chỉ giữ tài liệu thuộc {keep_path}")

    out_dir = "clean_test" if args.test else "clean"
    rows_per_task = 500 if args.test else 10000
    max_tasks = 2 if args.test else 0
    os.makedirs(os.path.join(out_dir, "boiler"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "parts"), exist_ok=True)

    dbs = [p for d in SRC_DIRS for p in sorted(glob.glob(f"vibiomir_s3/{d}/*.sqlite"))]
    if args.test:
        want = ("db/www.120ask.com", "db/www.cnkang.com", "db/suckhoedoisong.vn", "db/baophutho.vn")
        dbs = [p for p in dbs if any(w in p for w in want)][:4]
    stale = invalidate_updated(dbs, out_dir)
    if stale:
        print(f"{len(stale)} file SQLite mới cập nhật → làm sạch lại: {', '.join(stale[:6])}{' …' if len(stale) > 6 else ''}")
    print(f"{len(dbs)} file SQLite, {args.workers} tiến trình")

    tasks = []
    with ProcessPoolExecutor(args.workers, initializer=init_worker) as pool:
        futs = [pool.submit(plan_db, p, out_dir, rows_per_task, max_tasks) for p in dbs]
        for f in tqdm(as_completed(futs), total=len(futs), desc="Bước 1/3: lập kế hoạch + học dòng rác"):
            _, _, t = f.result()
            tasks.extend(t)
    tasks.sort(key=lambda t: -len(t[1]))

    # không dùng max_tasks_per_child: khi nhiều tác vụ xong rất nhanh, executor bị deadlock lúc đóng
    with ProcessPoolExecutor(args.workers, initializer=init_worker, initargs=(keep_path,)) as pool:
        futs = {pool.submit(run_task, p, ids, out_dir): len(ids) for p, ids in tasks}
        pbar = tqdm(total=sum(futs.values()), desc="Bước 2/3: tách nội dung", unit="trang")
        for f in as_completed(futs):
            f.result()
            pbar.update(futs[f])
        pbar.close()

    print("Bước 3/3: gộp và bỏ trùng")
    finalize(out_dir, keep_path)


if __name__ == "__main__":
    main()
