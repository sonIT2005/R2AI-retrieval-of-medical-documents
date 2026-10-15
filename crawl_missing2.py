"""
Crawl URL còn thiếu bằng curl_cffi (giả lập TLS fingerprint Chrome).

    python crawl_missing2.py --host nhathuoclongchau.com.vn
    python crawl_missing2.py --host nhathuoclongchau.com.vn --workers 2 --delay 2
    python crawl_missing2.py            # tất cả domain
"""

import os
import csv
import time
import random
import sqlite3
import argparse
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from curl_cffi import requests as cffi_requests
from tqdm import tqdm

BASE = "vibiomir_s3"
MISSING_CSV = os.path.join(BASE, "reports", "missing_pages.csv")
OUT_DIR = os.path.join(BASE, "db_extra")

RETRY_STATUSES = {429, 500, 502, 503, 504}
CAPTCHA_MARKERS = ("滑动拼图验证".encode(),)

_local = threading.local()


def get_session():
    # Mỗi thread 1 session: giữ kết nối, tránh tra DNS cho từng request
    if not hasattr(_local, "session"):
        _local.session = cffi_requests.Session(impersonate="chrome")
    return _local.session


def load_missing(host_filter, input_csv):
    urls = []
    with open(input_csv) as f:
        for row in csv.DictReader(f):
            if row.get("reason", "no_source") not in ("no_source", "no_source_not_archived"):
                continue
            if host_filter and row["host"] != host_filter:
                continue
            urls.append({"id": int(row["id"]), "url": row["url"], "host": row["host"]})
    return urls


def init_db(host):
    os.makedirs(OUT_DIR, exist_ok=True)
    conn = sqlite3.connect(os.path.join(OUT_DIR, f"{host}.sqlite"), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY, url TEXT, final_url TEXT, status INTEGER,
            kind TEXT, ctype TEXT, elapsed REAL, length INTEGER, html BLOB
        )
    """)
    conn.commit()
    return conn


def get_done_ids(host):
    path = os.path.join(OUT_DIR, f"{host}.sqlite")
    if not os.path.exists(path):
        return set()
    conn = sqlite3.connect(path)
    try:
        ids = {row[0] for row in conn.execute("SELECT id FROM pages")}
    except sqlite3.OperationalError:
        ids = set()
    conn.close()
    return ids


def error_kind(e):
    msg = str(e)
    if "resolve host" in msg:
        return "DNS"
    if "timed out" in msg:
        return "Timeout"
    if "connect" in msg:
        return "Connect"
    return msg[:60]


def fetch_one(item, delay, timeout, retries):
    last = None
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(min(60, 2 ** attempt) + random.random())
        try:
            start = time.time()
            resp = get_session().get(item["url"], timeout=timeout, allow_redirects=True)
            elapsed = time.time() - start
        except Exception as e:
            last = {"error": error_kind(e)}
            continue
        finally:
            if delay > 0:
                time.sleep(delay * random.uniform(0.5, 1.5))

        if resp.status_code in RETRY_STATUSES:
            last = {"error": f"HTTP {resp.status_code}"}
            continue
        if resp.status_code != 200:
            return {**item, "error": f"HTTP {resp.status_code}"}
        if any(m in resp.content for m in CAPTCHA_MARKERS):
            return {**item, "error": "CAPTCHA"}
        return {
            **item,
            "final_url": str(resp.url),
            "status": 200,
            "ctype": resp.headers.get("Content-Type", ""),
            "elapsed": elapsed,
            "html": resp.content,
        }
    return {**item, **last}


def main(args):
    urls = load_missing(args.host, args.input)
    print(f"URL thiếu{' (' + args.host + ')' if args.host else ''}: {len(urls):,}")

    done = set()
    for h in {u["host"] for u in urls}:
        done |= get_done_ids(h)
    urls = [u for u in urls if u["id"] not in done]
    print(f"Đã có trong db_extra: {len(done):,}  |  Còn lại: {len(urls):,}")
    if not urls:
        return

    random.shuffle(urls)
    db_conns, db_lock = {}, threading.Lock()
    errors = Counter()
    ok = 0
    pbar = tqdm(total=len(urls), desc="Crawling", unit="url", smoothing=0.1)
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch_one, u, args.delay, args.timeout, args.retries) for u in urls]
        for fut in as_completed(futures):
            r = fut.result()
            if "error" in r:
                errors[f"{r['host']}: {r['error']}"] += 1
            else:
                with db_lock:
                    conn = db_conns.get(r["host"]) or db_conns.setdefault(r["host"], init_db(r["host"]))
                    conn.execute(
                        "INSERT OR IGNORE INTO pages (id,url,final_url,status,kind,ctype,elapsed,length,html) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (r["id"], r["url"], r["final_url"], r["status"], "raw",
                         r["ctype"], r["elapsed"], len(r["html"]), r["html"]),
                    )
                    conn.commit()
                ok += 1
            pbar.set_postfix(ok=ok, err=sum(errors.values()))
            pbar.update(1)

    pbar.close()
    for conn in db_conns.values():
        conn.close()

    elapsed = time.time() - t0
    print(f"\n=== Kết quả ({elapsed:.0f}s) ===")
    print(f"  Thành công: {ok:,}")
    print(f"  Lỗi: {sum(errors.values()):,}")
    for k, c in errors.most_common(15):
        print(f"    {c:>7,}  {k}")
    print(f"  Lưu tại: {OUT_DIR}/")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=MISSING_CSV, help="CSV có cột id,url,host (vd missing_all.csv)")
    p.add_argument("--host", default=None, help="Chỉ crawl 1 domain, vd nhathuoclongchau.com.vn")
    p.add_argument("--workers", type=int, default=4, help="Số thread (default: 4)")
    p.add_argument("--delay", type=float, default=1.0, help="Delay sau mỗi request/thread (default: 1s)")
    p.add_argument("--timeout", type=int, default=20)
    p.add_argument("--retries", type=int, default=3, help="Số lần thử lại khi DNS/timeout/429 (default: 3)")
    main(p.parse_args())
