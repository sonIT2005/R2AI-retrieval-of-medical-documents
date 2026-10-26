#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook SessionStart: nạp ảnh chụp trạng thái dự án vào context của Claude.
Chạy khi mở phiên mới, resume, /clear và SAU KHI COMPACT -> Claude không bao giờ "quên" đang làm gì.
Claude Code thêm stdout (plain text) của hook này vào context; giới hạn 10.000 ký tự.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

LIMIT = 9000

for s in (sys.stdout, sys.stdin):
    try:
        s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def read(path, n):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    return text if len(text) <= n else text[:n] + "\n…(đã cắt bớt — mở file để xem đầy đủ)"


def git(args, root):
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True,
                           text=True, encoding="utf-8", timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    source = data.get("source", "startup")
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")

    parts = [f"[Ảnh chụp trạng thái dự án do hook SessionStart nạp tự động — nguồn: {source}]"]

    progress = read(root / "docs" / "PROGRESS.md", 5500)
    parts.append("## docs/PROGRESS.md\n" + (progress or "(chưa có file này)"))

    plan = read(root / "docs" / "PLAN.md", 1800)
    if plan:
        parts.append("## docs/PLAN.md (phần đầu)\n" + plan)

    log = git(["log", "--oneline", "-8"], root)
    if log:
        parts.append("## 8 commit gần nhất\n" + log)

    status = git(["status", "--short"], root)
    if status:
        lines = status.splitlines()
        more = f"\n… và {len(lines) - 20} file khác" if len(lines) > 20 else ""
        parts.append(f"## File chưa commit ({len(lines)})\n" + "\n".join(lines[:20]) + more)

    if source == "compact":
        parts.append("Phiên vừa được compact. docs/PROGRESS.md ở trên là nguồn sự thật về tiến độ.")

    print("\n\n".join(parts)[:LIMIT])


if __name__ == "__main__":
    main()
