#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vòng lặp tự sửa của /orchestrate — phần "luật cứng bằng code" (giống StageOrchestrator của Agentic Data Scientist).

Hook Stop: mỗi lần Claude định dừng, script đọc docs/STAGES.md:
  - còn tiêu chí tổng chưa đạt  → CHẶN việc dừng, bảo Claude chạy tiếp vòng lặp (stage → kiểm → phản tư → sửa plan)
  - tất cả tiêu chí đã đạt       → chặn 1 lần để Claude làm PHA 3 (báo cáo), rồi đặt "Trạng thái: xong"
  - "Trạng thái: chờ người dùng" / "dừng" / "xong" → cho dừng
  - hết lượt (max_turns) hoặc 3 lần liên tiếp không có tiến triển (STAGES.md, git không đổi) → cho dừng + tắt vòng lặp
Chỉ hoạt động khi đã bật bằng:  python3 .claude/hooks/orchestrate_guard.py --start [max_turns]
Chỉ giữ PHIÊN đã chạy --start (nhận ra nhờ mã vòng lặp in vào transcript của phiên đó); phiên khác cùng project
dừng tự do, không bị tính lượt. Sau /clear (phiên mới):  --claim  để phiên hiện tại nhận vòng lặp.
Tắt:  --stop     Xem:  --status
"""
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
STATE = ROOT / ".claude" / "state" / "orchestrate.json"
STAGES = ROOT / "docs" / "STAGES.md"
STALL_LIMIT = 3


def load():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def parse_stages(text):
    m = re.search(r"^Trạng thái:\s*(.+)$", text, re.M)
    status = m.group(1).strip() if m else ""
    sec = re.search(r"^##\s*Tiêu chí tổng.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    body = sec.group(1) if sec else ""
    todo = [re.sub(r"\s+", " ", x).strip() for x in re.findall(r"^\s*-\s*\[ \]\s*(.+)$", body, re.M)]
    done = re.findall(r"^\s*-\s*\[[xX]\]", body, re.M)
    return status, todo, len(done)


def out(obj):
    print(json.dumps(obj, ensure_ascii=False))
    sys.exit(0)


def sha(code):
    return hashlib.sha256(code.encode() if isinstance(code, str) else code).hexdigest()


def new_code(st):
    # State chỉ lưu hash → phiên khác đọc file state cũng không "nhận" được vòng lặp.
    code = "orch-" + secrets.token_hex(6)
    st["run_hash"], st["session_id"] = sha(code), None
    return code


def owns(st, data):
    """Phiên đang dừng có phải phiên đã chạy --start / --claim không."""
    if not st.get("run_hash"):
        return True  # state cũ (chưa có mã) → giữ hành vi cũ
    sid = data.get("session_id")
    if sid and sid == st.get("session_id"):
        return True
    try:
        raw = Path(data["transcript_path"]).read_bytes()
    except Exception:
        raw = None
    if raw is None:
        found = not st.get("session_id")  # không đọc được transcript: phiên dừng đầu tiên nhận
    else:
        found = any(sha(m) == st["run_hash"] for m in set(re.findall(rb"orch-[0-9a-f]{12}", raw)))
    if found and sid:
        st["session_id"] = sid
        save(st)
    return found


def hook():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    st = load()
    if not st.get("active"):
        sys.exit(0)
    if not owns(st, data if isinstance(data, dict) else {}):
        sys.exit(0)  # phiên khác trong cùng project → cho dừng, không tính lượt
    if not STAGES.exists():
        sys.exit(0)
    text = STAGES.read_text(encoding="utf-8")
    status, todo, done = parse_stages(text)
    low = status.lower()
    if "|" not in status and any(k in low for k in ("chờ người dùng", "dừng", "xong")):
        if "xong" in low:
            st["active"] = False
            save(st)
        sys.exit(0)

    fp = hashlib.sha1((text + git("rev-parse", "HEAD") + git("status", "--porcelain")).encode()).hexdigest()
    st["stall"] = st.get("stall", 0) + 1 if fp == st.get("last_fp") else 0
    st["last_fp"] = fp
    st["turns"] = st.get("turns", 0) + 1
    max_turns = st.get("max_turns", 40)

    if st["stall"] >= STALL_LIMIT:
        st["active"] = False
        save(st)
        out({"systemMessage": f"[orchestrate] Dừng vòng lặp: {STALL_LIMIT} lượt liên tiếp không có tiến triển "
                              "(STAGES.md và code không đổi). Xem docs/STAGES.md rồi quyết định."})
    if st["turns"] > max_turns:
        st["active"] = False
        save(st)
        out({"systemMessage": f"[orchestrate] Dừng vòng lặp: đã dùng hết {max_turns} lượt. "
                              f"Còn {len(todo)} tiêu chí chưa đạt — xem docs/STAGES.md."})
    save(st)

    if not todo and done:
        reason = ("[orchestrate] Mọi tiêu chí tổng đã đạt. Làm PHA 3 của /orchestrate: hỏi advisor, viết báo cáo "
                  "docs/reports/, đề xuất mục PLAN; sau đó đặt dòng 'Trạng thái: xong' trong docs/STAGES.md.")
    else:
        listed = "; ".join(todo[:5]) + (" …" if len(todo) > 5 else "")
        reason = (f"[orchestrate] Lượt {st['turns']}/{max_turns}. Còn {len(todo)} tiêu chí tổng chưa đạt: {listed}. "
                  "Tiếp tục vòng lặp trong /orchestrate: stage kế tiếp → worker → review → criteria-checker → "
                  "stage-reflector → áp dụng quyết định (TIẾP TỤC / ĐIỀU CHỈNH / ĐỔI HƯỚNG / DỪNG-HỎI) → ghi Nhật ký "
                  "quyết định. Cần người dùng quyết định thì đặt 'Trạng thái: chờ người dùng — <câu hỏi>' rồi dừng.")
    out({"decision": "block", "reason": reason})


def cli(argv):
    st = load()
    if argv[0] == "--start":
        try:
            ar = json.loads((ROOT / ".claude" / "state" / "autoresearch.json").read_text(encoding="utf-8"))
        except Exception:
            ar = {}
        if ar.get("active"):
            sys.exit(f"Không bật được: /autoresearch '{ar.get('tag')}' đang chạy. Chạy /autoresearch-stop trước.")
        mt = int(argv[1]) if len(argv) > 1 else 40
        st = {"active": True, "turns": 0, "max_turns": mt, "stall": 0, "last_fp": ""}
        code = new_code(st)
        save(st)
        print(f"Bật vòng lặp orchestrate (tối đa {mt} lượt). Mã vòng lặp: {code} — hook chỉ giữ phiên này.")
    elif argv[0] == "--claim":
        if not st.get("active"):
            sys.exit("Vòng lặp orchestrate đang tắt — dùng --start.")
        code = new_code(st)  # đổi mã → phiên cũ không còn khớp
        save(st)
        print(f"Phiên này nhận vòng lặp orchestrate. Mã vòng lặp: {code}")
    elif argv[0] == "--stop":
        st["active"] = False
        save(st)
        print("Đã tắt vòng lặp orchestrate.")
    elif argv[0] == "--status":
        status, todo, done = parse_stages(STAGES.read_text(encoding="utf-8")) if STAGES.exists() else ("", [], 0)
        print(json.dumps({"active": st.get("active", False), "turns": st.get("turns", 0),
                          "max_turns": st.get("max_turns"), "stall": st.get("stall", 0),
                          "phiên_giữ": st.get("session_id"),
                          "trạng_thái": status, "tiêu_chí_chưa_đạt": len(todo), "đã_đạt": done},
                         ensure_ascii=False, indent=2))
    else:
        sys.exit("Dùng: --start [max_turns] | --claim | --stop | --status")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli(sys.argv[1:])
    else:
        hook()
