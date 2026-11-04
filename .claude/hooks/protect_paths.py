#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook PreToolUse: chặn Claude sửa/xoá các đường dẫn trong .claude/protected_paths.txt.
- Edit/Write/MultiEdit/NotebookEdit: kiểm tra file_path / notebook_path.
- Bash/PowerShell: kiểm tra (best-effort) đích của >, >>, rm, mv, cp, tee, sed -i, truncate, git checkout/restore.
Exit code 2 + stderr => Claude Code chặn tool call và cho Claude biết lý do.
Đây là hàng rào phụ; lưới an toàn thật sự vẫn là git.
"""
import fnmatch
import json
import os
import re
import shlex
import sys
from pathlib import Path

for s in (sys.stdin, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8")
    except Exception:
        pass

WIN = os.name == "nt"


def norm(p):
    p = str(p).replace("\\", "/")
    return p.lower() if WIN else p


def load_patterns(root):
    f = root / ".claude" / "protected_paths.txt"
    if not f.exists():
        return []
    pats = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("./"):
            line = line[2:]
        pats.append(norm(line))
    return pats


def to_rel(path, root, cwd):
    p = Path(path)
    if not p.is_absolute():
        p = Path(cwd) / p
    p_s, r_s = norm(os.path.normpath(str(p))), norm(os.path.normpath(str(root)))
    if p_s == r_s or not p_s.startswith(r_s.rstrip("/") + "/"):
        return None  # ngoài project -> không quản
    return p_s[len(r_s.rstrip("/")) + 1:]


def match(rel, pats):
    base = rel.rsplit("/", 1)[-1]
    for pat in pats:
        if fnmatch.fnmatchcase(rel, pat):
            return pat
        if "/" not in pat and fnmatch.fnmatchcase(base, pat):
            return pat
        if pat.endswith("/**") and rel == pat[:-3]:
            return pat
    return None


def shell_targets(cmd):
    """Đoán các file mà lệnh shell sẽ ghi/xoá (best-effort)."""
    targets = [m.group(1) for m in re.finditer(r"(?<![0-9&<>=-])>>?\s*([^\s;&|<>()]+)", cmd)]
    for seg in re.split(r"&&|\|\||[;|&\n]", cmd):
        try:
            toks = shlex.split(seg)
        except ValueError:
            toks = seg.split()
        while toks and (re.match(r"^\w+=", toks[0]) or toks[0] == "sudo"):
            toks = toks[1:]
        if not toks:
            continue
        c, rest = toks[0].lower(), toks[1:]
        args = [t for t in rest if not t.startswith("-")]
        if c in ("rm", "rmdir", "unlink", "truncate", "shred", "mv", "tee",
                 "remove-item", "set-content", "out-file", "move-item"):
            targets += args
        elif c in ("cp", "copy-item", "install", "ln") and args:
            targets.append(args[-1])
        elif c == "sed" and any(t.startswith("-i") for t in rest):
            targets += args[1:]
        elif c == "git" and rest and rest[0] in ("checkout", "restore", "rm", "mv", "clean"):
            targets += [t for t in rest[1:] if not t.startswith("-") and t != "--"]
    return [t.strip("'\"") for t in targets if t and t != "/dev/null"]


def autoresearch_allow(root):
    """Khi /autoresearch đang bật: trả về danh sách mẫu ĐƯỢC sửa; None nếu không bật."""
    f = root / ".claude" / "state" / "autoresearch.json"
    try:
        st = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not st.get("active"):
        return None
    allow = [norm(e.lstrip("./")) for e in st.get("editable", [])]
    allow += [norm(x) for x in ("docs/autoresearch/**", "results/**", "docs/PROGRESS.md",
                                "docs/EXPERIMENTS.md", "docs/PLAN.md")]
    return allow


def block(rel, pat):
    sys.stderr.write(
        f"Bị chặn bởi hook protect_paths: '{rel}' khớp mẫu '{pat}' trong .claude/protected_paths.txt. "
        "Đây là đường dẫn được bảo vệ (dữ liệu gốc / split / eval đã chốt / khoá API). "
        "Không tìm cách khác để sửa nó; nếu thật sự cần thay đổi, hãy dừng và hỏi người dùng.\n"
    )
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
    cwd = data.get("cwd") or str(root)
    pats = load_patterns(root)
    allow = autoresearch_allow(root)
    if not pats and allow is None:
        sys.exit(0)

    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    candidates = []
    if tool in ("Bash", "PowerShell"):
        candidates = shell_targets(ti.get("command", ""))
    else:
        for key in ("file_path", "notebook_path", "path"):
            if ti.get(key):
                candidates.append(ti[key])

    for c in candidates:
        rel = to_rel(c, root, cwd)
        if rel is None:
            continue
        pat = match(rel, pats)
        if pat:
            block(rel, pat)
        if allow is not None and not match(rel, allow):
            sys.stderr.write(
                f"Bị chặn: /autoresearch đang chạy và '{rel}' không nằm trong danh sách file được sửa "
                f"({', '.join(allow[:-5])}). Chỉ thử ý tưởng bằng các file đó; cần sửa file khác thì ghi ý tưởng "
                "vào docs/PLAN.md cho người dùng xem sau.\n")
            sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
