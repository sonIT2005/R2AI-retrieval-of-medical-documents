#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chế độ /autoresearch (port từ karpathy/autoresearch) — phần "luật cứng bằng code".

Hook Stop: khi đang bật, Claude định dừng thì bị CHẶN và nhắc chạy thí nghiệm tiếp (thay cho câu "NEVER STOP"
trong program.md gốc — ở đây code ép, không phụ thuộc model tự giác). Cho dừng khi:
  - tới deadline hoặc đủ số thí nghiệm → chặn 1 lần để viết SUMMARY.md, lần sau cho dừng và tắt
  - 4 lần dừng liên tiếp mà results.tsv không thêm dòng nào → coi là kẹt, cho dừng và tắt
Ngoài ra protect_paths.py đọc file trạng thái này để CHỈ cho sửa các file trong danh sách "editable".

CLI:
  --start --tag oct12 --editable src/train.py[,configs/x.yaml] --direction max|min
          (--hours 8 | --until 07:00) [--max 200] [--noise 0.002]
  --stop | --status
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

for _s in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
STATE = ROOT / ".claude" / "state" / "autoresearch.json"
STALL_LIMIT = 4


def load():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def read_rows(st):
    path = ROOT / st["results"]
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def summary(st, rows):
    keeps = []
    for r in rows:
        try:
            if r.get("status") == "keep":
                keeps.append(float(r.get("metric", "nan")))
        except ValueError:
            pass
    best = (max(keeps) if st["direction"] == "max" else min(keeps)) if keeps else None
    crashes = sum(1 for r in rows if r.get("status") == "crash")
    return best, len(keeps), crashes


def out(obj):
    print(json.dumps(obj, ensure_ascii=False))
    sys.exit(0)


def hook():
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    st = load()
    if not st.get("active"):
        sys.exit(0)
    rows = read_rows(st)
    n = len(rows)
    best, keeps, crashes = summary(st, rows)
    now = time.time()

    if st.get("finishing"):
        st["active"] = False
        save(st)
        sys.exit(0)

    done_reason = None
    if now >= st["deadline"]:
        done_reason = "đã tới deadline"
    elif st.get("max_experiments") and n >= st["max_experiments"]:
        done_reason = f"đã đủ {n} thí nghiệm"
    if done_reason:
        st["finishing"] = True
        save(st)
        out({"decision": "block", "reason":
             f"[autoresearch] {done_reason}. Dừng thí nghiệm mới. Viết docs/autoresearch/{st['tag']}/SUMMARY.md theo "
             "mục KẾT THÚC trong /autoresearch (best vs baseline, thay đổi giữ lại, kết quả holdout, cái nào có thể "
             "là nhiễu, ý tưởng tiếp theo), cập nhật EXPERIMENTS.md, PLAN.md, PROGRESS.md rồi dừng."})

    st["stall"] = st.get("stall", 0) + 1 if n == st.get("last_rows", -1) else 0
    st["last_rows"] = n
    if st["stall"] >= STALL_LIMIT:
        st["active"] = False
        save(st)
        out({"systemMessage": f"[autoresearch] Dừng: {STALL_LIMIT} lượt liên tiếp không có thí nghiệm mới "
                              f"trong {st['results']}. Xem log để biết vì sao kẹt."})
    save(st)
    left = timedelta(seconds=int(st["deadline"] - now))
    best_s = f"{best:.6f}" if best is not None else "chưa có"
    out({"decision": "block", "reason":
         f"[autoresearch:{st['tag']}] {n} thí nghiệm ({keeps} giữ, {crashes} crash), best {st['direction']} = {best_s}, "
         f"còn {left}. KHÔNG hỏi người dùng có chạy tiếp không. Tiếp vòng lặp trong /autoresearch: chọn ý tưởng → "
         f"chỉ sửa {', '.join(st['editable'])} → commit → chạy → ghi results.tsv → giữ nếu tốt hơn ngưỡng nhiễu, "
         "không thì git reset. Hết ý tưởng thì đọc lại EXPERIMENTS.md, docs/research/, thử kết hợp các lần suýt thắng "
         "hoặc thay đổi mạnh hơn."})


def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--tag")
    ap.add_argument("--editable", help="danh sách file được sửa, cách nhau bởi dấu phẩy")
    ap.add_argument("--direction", choices=["min", "max"], default="max")
    ap.add_argument("--hours", type=float)
    ap.add_argument("--until", help="HH:MM (giờ máy)")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--noise", type=float, default=0.0)
    a = ap.parse_args()
    st = load()
    if a.start:
        if not (a.tag and a.editable and (a.hours or a.until)):
            sys.exit("Cần --tag, --editable và --hours hoặc --until")
        try:
            orch = json.loads((ROOT / ".claude" / "state" / "orchestrate.json").read_text(encoding="utf-8"))
        except Exception:
            orch = {}
        if orch.get("active"):
            sys.exit("Không bật được: /orchestrate đang chạy. Chờ nó xong hoặc chạy /orchestrate-stop trước.")
        import subprocess
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        if dirty:
            sys.exit("Không bật được: còn thay đổi chưa commit (vòng lặp dùng `git reset --hard`, sẽ xoá mất). "
                     "Commit hoặc stash trước:\n" + dirty)
        if a.until:
            hh, mm = map(int, a.until.split(":"))
            dl = datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)
            if dl <= datetime.now():
                dl += timedelta(days=1)
            deadline = dl.timestamp()
        else:
            deadline = time.time() + a.hours * 3600
        res = f"docs/autoresearch/{a.tag}/results.tsv"
        p = ROOT / res
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("commit\tmetric\tmemory_gb\tstatus\tdescription\n", encoding="utf-8")
        save({"active": True, "tag": a.tag, "editable": [e.strip() for e in a.editable.split(",") if e.strip()],
              "direction": a.direction, "deadline": deadline, "max_experiments": a.max, "noise": a.noise,
              "results": res, "stall": 0, "last_rows": -1, "finishing": False})
        print(f"Bật autoresearch '{a.tag}' tới {datetime.fromtimestamp(deadline):%Y-%m-%d %H:%M}. "
              f"Chỉ được sửa: {a.editable}. Kết quả: {res}")
    elif a.stop:
        st["active"] = False
        save(st)
        print("Đã tắt autoresearch.")
    elif a.status:
        if not st:
            print("Chưa từng bật.")
            return
        rows = read_rows(st)
        best, keeps, crashes = summary(st, rows)
        print(json.dumps({"active": st.get("active"), "tag": st.get("tag"), "experiments": len(rows), "keeps": keeps,
                          "crashes": crashes, "best": best, "direction": st.get("direction"),
                          "deadline": datetime.fromtimestamp(st["deadline"]).isoformat(timespec="minutes"),
                          "editable": st.get("editable")}, ensure_ascii=False, indent=2))
    else:
        sys.exit("Dùng: --start … | --stop | --status")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli()
    else:
        hook()
