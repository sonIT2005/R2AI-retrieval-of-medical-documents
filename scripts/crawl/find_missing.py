"""
So danh sách URL gốc của BTC với các trang đã có trong vibiomir_s3 (+ db_extra)
→ xuất missing_all.csv (id, url, host) gồm các trang chưa có nội dung.

    python find_missing.py
"""

import glob
import sqlite3
from urllib.parse import urlparse

import pandas as pd

DB_GLOBS = ["vibiomir_s3/db*/*.sqlite"]
CAPTCHA_HEX = "滑动拼图验证".encode().hex()

corpus = pd.read_parquet("btc_data_v2/links_corpus_vi_en_zh.parquet")
print(f"Corpus BTC: {len(corpus):,} URL")

have = set()
for path in sorted(p for g in DB_GLOBS for p in glob.glob(g)):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    query = "SELECT id FROM pages WHERE status = 200"
    if "db_extra" in path:
        # HTML trong db_extra không nén → lọc được trang CAPTCHA bằng SQL
        query += f" AND instr(html, X'{CAPTCHA_HEX}') = 0"
    try:
        ids = [r[0] for r in conn.execute(query)]
    except sqlite3.OperationalError as e:
        print(f"  bỏ qua {path}: {e}")
        ids = []
    conn.close()
    have.update(ids)
    print(f"  {len(ids):>9,}  {path}", flush=True)

missing = corpus[~corpus["id"].isin(have)].copy()
missing["host"] = missing["url"].map(lambda u: urlparse(u).netloc)
missing.to_csv("missing_all.csv", index=False)

print(f"\nĐã có: {len(corpus) - len(missing):,} ({(1 - len(missing) / len(corpus)) * 100:.1f}%)")
print(f"Còn thiếu: {len(missing):,} → missing_all.csv\n")
print(missing["host"].value_counts().head(30).to_string())
