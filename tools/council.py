#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
council.py — "Hội đồng model": gửi 1 brief tới nhiều LLM (API kiểu OpenAI) để phản biện plan.
Mỗi model đóng 1 vai (red team, tìm nguyên nhân gốc, dân thi Kaggle, ...) để ý kiến không trùng nhau.
Chỉ dùng thư viện chuẩn Python 3.8+, không cần pip install.

  python3 tools/council.py --ping                 # kiểm tra key + tên model của từng provider
  python3 tools/council.py --models qwen          # liệt kê model của 1 provider (nếu provider hỗ trợ)
  python3 tools/council.py stuck --dry-run        # xem sẽ gọi ai, vai gì, brief dài bao nhiêu
  python3 tools/council.py stuck                  # gửi docs/council/brief.md tới preset "stuck"
  python3 tools/council.py all --rounds 3         # 3 vòng: độc lập → phản biện chéo ẩn danh → chốt
  python3 tools/council.py --only grok,gemini --brief docs/council/brief.md
  python3 tools/council.py stuck --no-search      # tắt tra cứu web (rẻ, nhanh)

Mặc định đi qua OpenRouter (1 key cho mọi model) + DeepSeek gọi thẳng:
  OpenRouter: tool "openrouter:web_search" (model tự quyết khi nào search) + "reasoning": {"effort": "high"}
  python3 tools/council.py --find grok            # tìm slug model đúng trên OpenRouter
  python3 tools/council.py stuck --research pro   # Perplexity tra cứu trước, rồi hội đồng bàn bạc
  python3 tools/council.py --ask "SOTA cho bài X?" --research deep   # chỉ tra cứu → docs/research/
Vẫn hỗ trợ gọi thẳng từng hãng (api: chat | responses | gemini) nếu bạn có key riêng:
  api=responses (OpenAI, xAI)  tool web_search phía server + reasoning.effort
  api=gemini                   Google Search grounding + thinkingConfig
  api=chat                     Qwen enable_search/enable_thinking · GLM tool web_search + thinking
                               · Kimi builtin $web_search · DeepSeek/MiniMax: chỉ suy nghĩ, không search
  Mặc định chỉ tra cứu ở VÒNG 1; vòng sau các model bàn bạc dựa trên nguồn đã tìm.

Cơ chế "nhiều model cùng suy nghĩ":
  Vòng 1  mỗi model trả lời ĐỘC LẬP theo vai riêng (không thấy nhau → tránh a dua).
  Vòng 2+ mỗi model đọc câu trả lời ẨN DANH (M1, M2…) của cả hội đồng, phản biện, đổi ý nếu
          người khác đúng hơn, viết lại đề xuất cuối và BỎ PHIẾU top 3 (không được bầu cho mình).
  Cuối    đếm phiếu kiểu Borda (3/2/1) → bảng xếp hạng đồng thuận trong combined.md.
Kết quả: docs/council/round_XX/{r1/, r2/, …, combined.md, votes.md, sources.md, status.json, brief.md}
"""
import argparse
import json
import os
import random
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG_PATH = HERE / "council_config.json"
ROLES_PATH = HERE / "council_roles.md"
ENV_PATH = HERE / ".env"
OUT_BASE = ROOT / "docs" / "council"
UA = "llm-council/1.0"

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


class ApiError(Exception):
    def __init__(self, code, body):
        super().__init__(f"HTTP {code}: {body[:400]}")
        self.code, self.body = code, body


def load_env(path):
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and not os.environ.get(k):
            os.environ[k] = v


def load_roles(path):
    """council_roles.md: mỗi vai bắt đầu bằng dòng '=== ten_vai ==='."""
    roles, name, buf = {}, None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^===\s*([A-Za-z0-9_\-]+)\s*===\s*$", line)
        if m:
            if name:
                roles[name] = "\n".join(buf).strip()
            name, buf = m.group(1), []
        elif name:
            buf.append(line)
    if name:
        roles[name] = "\n".join(buf).strip()
    return roles


def http_json(url, headers, payload=None, timeout=180):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="GET" if payload is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise ApiError(e.code, e.read().decode("utf-8", "replace")) from None


def extract_text(resp):
    try:
        msg = resp["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Phản hồi sai định dạng: " + json.dumps(resp, ensure_ascii=False)[:300])
    content = msg.get("content") or ""
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    # Một số model (vd MiniMax) trả phần suy nghĩ trong <think>...</think>
    return re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()


URL_RE = re.compile(r"https?://[^\s<>\]\)\"'`]+")
RETRYABLE = (408, 429, 500, 502, 503, 504)


def post_with_retry(url, headers, payload, timeout, optional_keys=()):
    """POST + thử lại khi lỗi tạm thời; khi HTTP 400 nhắc tới 1 tham số tuỳ chọn thì bỏ tham số đó rồi thử lại."""
    dropped = set()
    for attempt in range(5):
        try:
            return http_json(url, headers, payload, timeout)
        except ApiError as e:
            low = e.body.lower()
            if e.code == 400:
                bad = [k for k in optional_keys if k in payload and k not in dropped and k.lower() in low]
                if bad:
                    for k in bad:
                        payload.pop(k, None)
                        dropped.add(k)
                    continue
            if e.code in RETRYABLE and attempt < 3:
                time.sleep(4 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < 2:
                time.sleep(4 * (attempt + 1))
                continue
            raise RuntimeError(f"Lỗi mạng/timeout: {e}")
    raise RuntimeError("Thử lại quá số lần cho phép")


def _bearer(p):
    h = {"Content-Type": "application/json", "User-Agent": UA,
         "Authorization": f"Bearer {os.environ.get(p['api_key_env'], '')}"}
    h.update(p.get("extra_headers") or {})
    return h


def _timeout(p, cfg):
    return p.get("timeout_seconds") or cfg.get("timeout_seconds", 420)


def _max_tokens(p, cfg, override):
    return override or p.get("max_tokens") or cfg.get("default_max_tokens", 4000)


def call_chat(p, system, user, cfg, search=False, light=False, max_tokens=None):
    """Chat Completions kiểu OpenAI (OpenRouter, DeepSeek, Qwen, GLM, MiniMax, Kimi…)."""
    url = p["base_url"].rstrip("/") + "/chat/completions"
    token_param = p.get("token_param", "max_tokens")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    base = {"model": p["model"], token_param: _max_tokens(p, cfg, max_tokens)}
    if p.get("temperature") is not None:
        base["temperature"] = p["temperature"]
    if not light:
        base.update(p.get("thinking_body") or {})
    s = p.get("search") or {}
    if search:
        base.update(s.get("body") or {})
    kimi_loop = search and s.get("kimi_builtin")
    if kimi_loop:
        base["tools"] = [{"type": "builtin_function", "function": {"name": "$web_search"}}]
    usage_total, sources, searches = {"prompt_tokens": 0, "completion_tokens": 0}, [], 0
    for _ in range(int(s.get("max_tool_rounds", 6)) if kimi_loop else 1):
        payload = dict(base, messages=messages)
        resp = post_with_retry(url, _bearer(p), payload, _timeout(p, cfg),
                               optional_keys=("temperature", "reasoning_effort", "thinking", "reasoning"))
        u = resp.get("usage") or {}
        for k in usage_total:
            usage_total[k] += u.get(k) or 0
        searches += int((u.get("server_tool_use") or {}).get("web_search_requests") or 0)   # OpenRouter
        if resp.get("web_search"):                       # GLM trả nguồn ở đây
            searches += 1
        for r in resp.get("web_search") or []:
            if isinstance(r, dict) and r.get("link"):
                sources.append((r.get("title", ""), r["link"]))
        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        for a in msg.get("annotations") or []:            # OpenRouter: url_citation
            c = a.get("url_citation") or a
            if isinstance(c, dict) and c.get("url"):
                sources.append((c.get("title", ""), c["url"]))
        for c in resp.get("search_results") or []:          # Perplexity Sonar
            if isinstance(c, dict) and c.get("url"):
                sources.append((c.get("title", ""), c["url"]))
        for c in resp.get("citations") or []:
            if isinstance(c, str):
                sources.append(("", c))
        if kimi_loop and choice.get("finish_reason") == "tool_calls" and msg.get("tool_calls"):
            messages.append(msg)
            for tc in msg["tool_calls"]:
                fn = tc.get("function") or {}
                searches += 1 if fn.get("name") == "$web_search" else 0
                # $web_search do Kimi tự chạy: chỉ cần gửi trả nguyên arguments
                messages.append({"role": "tool", "tool_call_id": tc.get("id"), "name": fn.get("name"),
                                 "content": fn.get("arguments") if fn.get("name") == "$web_search"
                                 else json.dumps({"error": "unknown tool"})})
            continue
        return extract_text(resp), usage_total, sources, searches
    raise RuntimeError("Kimi gọi $web_search quá nhiều vòng mà chưa trả lời")


def call_responses(p, system, user, cfg, search=False, light=False, max_tokens=None):
    """Responses API (OpenAI, xAI): web_search là tool chạy phía server."""
    url = p["base_url"].rstrip("/") + "/responses"
    payload = {"model": p["model"], "instructions": system, "input": user,
               "max_output_tokens": _max_tokens(p, cfg, max_tokens)}
    if p.get("reasoning") and not light:
        payload["reasoning"] = p["reasoning"]
    if search and (p.get("search") or {}).get("tools"):
        payload["tools"] = p["search"]["tools"]
    resp = post_with_retry(url, _bearer(p), payload, _timeout(p, cfg), optional_keys=("reasoning",))
    texts, sources, searches = [], [], 0
    for item in resp.get("output") or []:
        t = item.get("type", "")
        if "search" in t and t.endswith("_call"):
            searches += 1
        if t == "message":
            for c in item.get("content") or []:
                if c.get("type") in ("output_text", "text"):
                    texts.append(c.get("text", ""))
                    for a in c.get("annotations") or []:
                        if a.get("url"):
                            sources.append((a.get("title", ""), a["url"]))
    for cit in resp.get("citations") or []:            # một số bản xAI trả citations riêng
        if isinstance(cit, str):
            sources.append(("", cit))
        elif isinstance(cit, dict) and cit.get("url"):
            sources.append((cit.get("title", ""), cit["url"]))
    text = "\n".join(texts) or resp.get("output_text") or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    u = resp.get("usage") or {}
    return text, {"prompt_tokens": u.get("input_tokens"), "completion_tokens": u.get("output_tokens")}, sources, searches


def call_gemini(p, system, user, cfg, search=False, light=False, max_tokens=None):
    """Gemini API gốc (generateContent): Google Search grounding + thinkingConfig."""
    url = f"{p['base_url'].rstrip('/')}/models/{p['model']}:generateContent"
    headers = {"Content-Type": "application/json", "User-Agent": UA,
               "x-goog-api-key": os.environ.get(p["api_key_env"], "")}
    gen = {"maxOutputTokens": _max_tokens(p, cfg, max_tokens)}
    if p.get("thinking_config") and not light:
        gen["thinkingConfig"] = p["thinking_config"]
    payload = {"systemInstruction": {"parts": [{"text": system}]},
               "contents": [{"role": "user", "parts": [{"text": user}]}], "generationConfig": gen}
    if search and (p.get("search") or {}).get("tools"):
        payload["tools"] = p["search"]["tools"]
    resp = post_with_retry(url, headers, payload, _timeout(p, cfg))
    cand = (resp.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(x.get("text", "") for x in parts if not x.get("thought")).strip()
    gm = cand.get("groundingMetadata") or {}
    sources = [((c.get("web") or {}).get("title", ""), (c.get("web") or {}).get("uri"))
               for c in gm.get("groundingChunks") or [] if (c.get("web") or {}).get("uri")]
    searches = len(gm.get("webSearchQueries") or [])
    u = resp.get("usageMetadata") or {}
    return text, {"prompt_tokens": u.get("promptTokenCount"), "completion_tokens": u.get("candidatesTokenCount")}, sources, searches


ADAPTERS = {"chat": call_chat, "responses": call_responses, "gemini": call_gemini}
_HEADROOM = {"checked": False, "fn": None, "saved": 0}


def maybe_compress(system, user, cfg):
    """Nén bằng Headroom nếu bật "headroom_compress" và đã `pip install headroom-ai`. Lỗi → giữ nguyên."""
    if not cfg.get("headroom_compress"):
        return system, user
    if not _HEADROOM["checked"]:
        _HEADROOM["checked"] = True
        try:
            from headroom import compress as _c   # type: ignore
            _HEADROOM["fn"] = _c
        except Exception:
            print("ℹ️  headroom_compress bật nhưng chưa cài headroom-ai → gửi nguyên văn.")
    fn = _HEADROOM["fn"]
    if not fn:
        return system, user
    try:
        r = fn([{"role": "system", "content": system}, {"role": "user", "content": user}],
               model=cfg.get("headroom_model", "gpt-4o"))
        msgs = list(r.messages)
        _HEADROOM["saved"] += int(getattr(r, "tokens_saved", 0) or 0)
        return msgs[0]["content"], msgs[1]["content"]
    except Exception:
        return system, user


def call_member(p, system, user, cfg, search=False, light=False, max_tokens=None, allow_empty=False):
    """Trả về (text, usage, sources[(title,url)], số lượt search)."""
    fn = ADAPTERS.get(p.get("api", "chat"))
    if not fn:
        raise RuntimeError(f"api '{p.get('api')}' không hỗ trợ (chat | responses | gemini)")
    if not light:
        system, user = maybe_compress(system, user, cfg)
    text, usage, sources, searches = fn(p, system, user, cfg, search=search, light=light, max_tokens=max_tokens)
    if not text and not allow_empty:
        raise RuntimeError("Model trả về rỗng (model reasoning hết token?) — tăng max_tokens trong config")
    seen, merged = set(), []
    for title, u in list(sources) + [("", m.rstrip(".,;:")) for m in URL_RE.findall(text or "")]:
        if u and u not in seen:
            seen.add(u)
            merged.append((title, u))
    return text, usage, merged, searches


def capabilities(p):
    s = p.get("search") or {}
    has_search = bool(s.get("tools") or s.get("body") or s.get("kimi_builtin"))
    thinking = bool(p.get("thinking_body") or p.get("reasoning") or p.get("thinking_config")
                    or p.get("thinking_builtin"))
    return has_search, thinking


def select(cfg, names_arg, preset):
    provs = cfg["providers"]
    if names_arg:
        names = [n.strip() for n in names_arg.split(",") if n.strip()]
    else:
        preset = preset or cfg.get("default_preset", "all")
        if preset not in cfg["presets"]:
            sys.exit(f"Không có preset '{preset}'. Có: {', '.join(cfg['presets'])}")
        names = cfg["presets"][preset]
    unknown = [n for n in names if n not in provs]
    if unknown:
        sys.exit(f"Provider không có trong config: {unknown}")
    chosen, skipped = [], []
    for n in names:
        p = provs[n]
        if p.get("enabled", True) is False:
            skipped.append((n, "enabled=false"))
        elif not os.environ.get(p["api_key_env"]):
            skipped.append((n, f"thiếu biến {p['api_key_env']} trong tools/.env"))
        else:
            chosen.append((n, p))
    return chosen, skipped


def cmd_ping(chosen, skipped, cfg):
    for n, why in skipped:
        print(f"⏭️  {n:<9} bỏ qua: {why}")

    def one(n, p):
        t0 = time.time()
        try:
            text, _, _, _ = call_member(p, "You are a connectivity test.", "Reply with exactly: OK", cfg,
                                        light=True, max_tokens=p.get("ping_max_tokens", 600), allow_empty=True)
            return n, True, f"{time.time() - t0:5.1f}s → {text[:40]!r}"
        except Exception as e:
            return n, False, str(e)[:300]

    with ThreadPoolExecutor(max_workers=8) as ex:
        for f in as_completed([ex.submit(one, n, p) for n, p in chosen]):
            n, ok, msg = f.result()
            print(f"{'✅' if ok else '❌'} {n:<9} {cfg['providers'][n]['model']:<26} {msg}")


def cmd_models(name, cfg):
    p = cfg["providers"].get(name)
    if not p:
        sys.exit(f"Không có provider '{name}'")
    key = os.environ.get(p["api_key_env"], "")
    headers = ({"x-goog-api-key": key} if p.get("api") == "gemini" else {"Authorization": f"Bearer {key}"})
    headers["User-Agent"] = UA
    try:
        resp = http_json(p["base_url"].rstrip("/") + "/models", headers, None, 60)
    except Exception as e:
        sys.exit(f"Không lấy được danh sách model ({e}). Xem trên dashboard của nhà cung cấp.")
    ids = sorted(str(m.get("id") or m.get("name", "?")).replace("models/", "")
                 for m in (resp.get("data") or resp.get("models") or []))
    print("\n".join(ids) if ids else "(trống)")


def cmd_find(keyword, cfg):
    """Tìm model trên OpenRouter theo từ khoá: in slug, ngữ cảnh, giá, có reasoning/tools không."""
    p = next((v for v in cfg["providers"].values() if "openrouter.ai" in v.get("base_url", "")), None)
    base = (p or {}).get("base_url", "https://openrouter.ai/api/v1")
    try:
        resp = http_json(base.rstrip("/") + "/models", {"User-Agent": UA}, None, 60)
    except Exception as e:
        sys.exit(f"Không lấy được danh sách model OpenRouter ({e})")
    kw = keyword.lower()
    rows = [m for m in resp.get("data", []) if kw in (m.get("id", "") + " " + m.get("name", "")).lower()]
    if not rows:
        sys.exit(f"Không thấy model nào khớp '{keyword}'")
    for m in sorted(rows, key=lambda m: m.get("created", 0), reverse=True)[:25]:
        pr = m.get("pricing") or {}
        sp = set(m.get("supported_parameters") or [])

        def per_m(x):
            try:
                return f"${float(x) * 1e6:.2f}"
            except (TypeError, ValueError):
                return "?"
        flags = ("reasoning " if "reasoning" in sp else "") + ("tools" if "tools" in sp else "")
        print(f"{m.get('id', '?'):<45} ctx {m.get('context_length', '?'):>8}  in {per_m(pr.get('prompt'))}/M"
              f"  out {per_m(pr.get('completion'))}/M  {flags}")


RESEARCH_SYSTEM = """You are the research scout for a student team in an AI competition (AI tools are allowed).
Search the web thoroughly and report what would most help them decide what to try next: recent papers, official
documentation, winning solutions / write-ups of similar competitions, strong open-source repos, known pitfalls.
Prefer primary sources. Every factual claim must carry an inline citation [n]. Never invent a URL.
Write in {lang}, using exactly these headings:
## Tóm tắt phát hiện
## Kỹ thuật / ý tưởng đáng thử (mỗi ý: là gì · bằng chứng · điều kiện áp dụng · nguồn)
## Bẫy và cảnh báo đã biết
## Nguồn (đánh số: tiêu đề — URL)"""


def perplexity_research(question, cfg, mode):
    """Tra cứu bằng Perplexity Sonar qua OpenRouter. mode: 'pro' (nhanh) | 'deep' (kỹ, chậm, đắt)."""
    p = (cfg.get("research") or {}).get(mode)
    if not p:
        raise RuntimeError(f"config thiếu research.{mode}")
    if not os.environ.get(p["api_key_env"]):
        raise RuntimeError(f"thiếu {p['api_key_env']} trong tools/.env")
    print(f"🔎 Perplexity ({p['model']}) đang tra cứu… (deep có thể mất vài phút)")
    t0 = time.time()
    system = RESEARCH_SYSTEM.format(lang=cfg.get("response_language", "Vietnamese"))
    text, usage, sources, _ = call_member(p, system, question, cfg)
    print(f"   xong sau {time.time() - t0:.0f}s · {len(sources)} nguồn · "
          f"in {usage.get('prompt_tokens', '?')} / out {usage.get('completion_tokens', '?')} token")
    return text, sources


def cmd_ask(question, cfg, mode):
    """Hỏi Perplexity một câu, lưu báo cáo vào docs/research/ (thay cho Perplexity MCP, không cần tài khoản riêng)."""
    text, sources = perplexity_research(question, cfg, mode)
    out_dir = ROOT / "docs" / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    import unicodedata
    plain = unicodedata.normalize("NFKD", question.lower().replace("đ", "d")).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", plain)[:50].strip("-") or "research"
    path = out_dir / f"{datetime.now():%Y%m%d-%H%M}-{mode}-{slug}.md"
    src = "".join(f"- {t or '(không tiêu đề)'} — {u}\n" for t, u in sources) or "_(không có)_\n"
    path.write_text(f"# {question}\n\n> Perplexity {mode} · {datetime.now():%Y-%m-%d %H:%M}. "
                    f"Kiểm chứng link quan trọng trước khi dựa vào.\n\n{text}\n\n## Nguồn trả về từ API\n{src}",
                    encoding="utf-8")
    print(f"📁 {path.relative_to(ROOT).as_posix()}")


def next_round_dir():
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    nums = []
    for d in OUT_BASE.iterdir():
        m = re.match(r"round_(\d+)$", d.name)
        if d.is_dir() and m:
            nums.append(int(m.group(1)))
    out = OUT_BASE / f"round_{(max(nums) + 1 if nums else 1):02d}"
    out.mkdir()
    return out


def build_system(roles, role, lang, phase, search=False):
    """phase = 'r1' (độc lập) hoặc 'deliberation' (phản biện chéo)."""
    tail = roles["format_r1"] if phase == "r1" else roles["deliberation"]
    web = roles.get("web_on" if search else "web_off", "")
    return (f"{roles.get('common', '')}\n\n{web}\n\nYOUR ROLE: {role}\n{roles[role]}\n\n{tail}\n\n"
            f"Write your entire answer in {lang}. Follow the output format exactly.")


PROPOSAL_RE = re.compile(r"^###\s*Đề xuất\s+([A-Ca-c])\b\s*[:：.\-–—]?\s*(.*)$", re.M)
H2_RE = re.compile(r"^##\s", re.M)


def extract_proposals(text):
    """{'A': (tiêu đề, đoạn văn)} từ một câu trả lời theo đúng format."""
    out = {}
    ms = list(PROPOSAL_RE.finditer(text))
    for i, m in enumerate(ms):
        ends = [len(text)]
        if i + 1 < len(ms):
            ends.append(ms[i + 1].start())
        h2 = H2_RE.search(text, m.end())
        if h2:
            ends.append(h2.start())
        out[m.group(1).upper()] = (m.group(2).strip() or "(không tên)", text[m.start():min(ends)].strip())
    return out


def parse_votes(text, me, valid_ids):
    m = re.search(r"VOTES\s*:\s*(.+)", text, re.I)
    if not m:
        return []
    picked = []
    for vid in re.findall(r"M\d+\s*-\s*[A-C]", m.group(1).upper()):
        vid = vid.replace(" ", "")
        if vid in valid_ids and not vid.startswith(me + "-") and vid not in picked:
            picked.append(vid)
    return picked[:3]


def deliberation_msg(brief, prev, me, max_chars):
    parts = ["BRIEF:\n\n" + brief, "\n\n=== CÂU TRẢ LỜI VÒNG TRƯỚC CỦA HỘI ĐỒNG (ẩn danh) ==="]
    for label in sorted(prev, key=lambda s: int(s[1:])):
        t = prev[label]
        if len(t) > max_chars:
            t = t[:max_chars] + "\n…(cắt bớt)"
        mine = "  ← ĐÂY LÀ CÂU TRẢ LỜI CỦA BẠN" if label == me else ""
        parts.append(f"\n\n--- Thành viên {label}{mine} ---\n{t}")
    parts.append(f"\n\nBạn là thành viên {me}. ID đề xuất có dạng <thành viên>-<chữ cái>, ví dụ M2-A. "
                 f"Không bỏ phiếu cho đề xuất của chính bạn ({me}-…).")
    return "".join(parts)


def run_round(members, system_for, user_for, search_for, cfg, rnd):
    """Gọi song song; trả về {provider: dict(ok, text, usage, seconds, sources, searches)}."""
    res = {}

    def one(n, p):
        t0 = time.time()
        try:
            text, usage, sources, searches = call_member(p, system_for(n), user_for(n), cfg, search=search_for(n))
            return n, True, text, usage, sources, searches, time.time() - t0
        except Exception as e:
            return n, False, str(e), {}, [], 0, time.time() - t0

    print(f"\n── Vòng {rnd}: gọi {len(members)} model song song…")
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(members)))) as ex:
        for f in as_completed([ex.submit(one, n, p) for n, p in members]):
            n, ok, text, usage, sources, searches, dt = f.result()
            res[n] = {"ok": ok, "text": text, "usage": usage, "seconds": round(dt, 1),
                      "sources": sources, "searches": searches}
            info = (f"in {usage.get('prompt_tokens', '?')} / out {usage.get('completion_tokens', '?')} token"
                    f" · {searches} lượt search · {len(sources)} nguồn" if ok else text[:200])
            print(f"{'✅' if ok else '❌'} {n:<9} {dt:6.1f}s  {info}")
    return res


def cmd_run(chosen, skipped, cfg, roles, args):
    brief_path = Path(args.brief)
    if not brief_path.is_absolute():
        brief_path = ROOT / brief_path
    if not brief_path.exists():
        sys.exit(f"Không thấy brief: {brief_path}\n→ Tạo từ docs/council/BRIEF_TEMPLATE.md")
    brief = brief_path.read_text(encoding="utf-8")
    lang = cfg.get("response_language", "Vietnamese")
    rounds = max(1, args.rounds or cfg.get("default_rounds", 2))
    max_chars = cfg.get("max_chars_per_answer", 6000)

    print(f"Brief: {brief_path.name} — {len(brief)} ký tự (~{int(len(brief) / 3.5)} token) · {rounds} vòng")
    if len(brief) > 15000:
        print("⚠️  Brief dài: nên rút gọn (≤ ~1500 từ) để đỡ tốn tiền và model tập trung hơn.")
    for n, why in skipped:
        print(f"⏭️  bỏ qua {n}: {why}")

    for key in ("format_r1", "deliberation"):
        if key not in roles:
            sys.exit(f"council_roles.md thiếu mục '=== {key} ==='")
    search_rounds = set() if args.no_search else (
        set(range(1, 100)) if args.search_all_rounds else set(cfg.get("search_in_rounds", [1])))
    role_of, can_search = {}, {}
    for n, p in chosen:
        role = args.role or p.get("role", "plan_critic")
        if role not in roles:
            sys.exit(f"Vai '{role}' không có trong council_roles.md")
        role_of[n] = role
        has_s, think = capabilities(p)
        can_search[n] = has_s
        web = (f"web: vòng {','.join(map(str, sorted(r for r in search_rounds if r <= rounds)))}"
               if has_s and search_rounds else "web: không")
        print(f"   • {n:<9} {p['model']:<22} vai: {role:<20} {web:<12} think: {'có' if think else 'mặc định'}")
    if rounds > 1 and len(chosen) < 2:
        print("ℹ️  Chỉ có 1 model → chạy 1 vòng (phản biện chéo cần ≥ 2 model).")
        rounds = 1
    if args.dry_run:
        return
    if not chosen:
        sys.exit("Không có provider nào để gọi (kiểm tra tools/.env).")

    out = next_round_dir()
    shutil.copy(brief_path, out / "brief.md")
    research_mode = args.research or cfg.get("default_research", "off")
    research_sources = []
    if research_mode != "off":
        try:
            rtext, research_sources = perplexity_research(
                "Research what would help answer the open questions in this brief.\n\n" + brief, cfg, research_mode)
            (out / "research.md").write_text(f"# Perplexity {research_mode}\n\n{rtext}\n", encoding="utf-8")
            cut = cfg.get("max_chars_research", 8000)
            brief = (brief + "\n\n## Tài liệu tra cứu trước bởi Perplexity (dùng làm bằng chứng, vẫn cần phản biện)\n"
                     + (rtext if len(rtext) <= cut else rtext[:cut] + "\n…(cắt bớt)"))
        except Exception as e:
            print(f"⚠️  Bỏ qua bước Perplexity: {str(e)[:200]}")
    names = [n for n, _ in chosen]
    shuffled = names[:]
    random.shuffle(shuffled)
    label_of = {n: f"M{i + 1}" for i, n in enumerate(shuffled)}
    prov = dict(chosen)
    status = {"round": out.name, "time": datetime.now().isoformat(timespec="seconds"), "rounds": rounds,
              "members": {n: {"label": label_of[n], "model": prov[n]["model"], "role": role_of[n]} for n in names},
              "calls": []}

    history = []            # mỗi phần tử: {provider: result}
    active = list(chosen)
    for rnd in range(1, rounds + 1):
        if rnd == 1:
            use = lambda n, r=rnd: can_search[n] and r in search_rounds
            res = run_round(active, lambda n, u=use: build_system(roles, role_of[n], lang, "r1", u(n)),
                            lambda n: "BRIEF:\n\n" + brief, use, cfg, rnd)
        else:
            prev = {label_of[n]: r["text"] for n, r in history[-1].items() if r["ok"]}
            use = lambda n, r=rnd: can_search[n] and r in search_rounds
            res = run_round(active, lambda n, u=use: build_system(roles, role_of[n], lang, "deliberation", u(n)),
                            lambda n: deliberation_msg(brief, prev, label_of[n], max_chars), use, cfg, rnd)
        history.append(res)
        rd = out / f"r{rnd}"
        rd.mkdir()
        for n, r in res.items():
            head = f"# {label_of[n]} = {n} ({prov[n]['model']}) — vai: {role_of[n]} — vòng {rnd}"
            (rd / f"{n}.md").write_text(f"{head}\n\n{r['text'] if r['ok'] else '❌ LỖI: ' + r['text']}\n",
                                        encoding="utf-8")
            status["calls"].append({"round": rnd, "provider": n, "ok": r["ok"], "seconds": r["seconds"],
                                    "usage": r["usage"], "searches": r.get("searches", 0),
                                    "sources": len(r.get("sources") or [])})
        active = [(n, prov[n]) for n in names if res.get(n, {}).get("ok")]
        if len(active) < 2 and rnd < rounds:
            print("⚠️  Còn < 2 model trả lời được → dừng phản biện chéo sớm.")
            break

    # ---- Đếm phiếu (phiếu của vòng cuối chấm các đề xuất của vòng liền trước)
    ranking, tally_md = [], ""
    if len(history) >= 2:
        prev_round = history[-2]
        proposals = {}
        for n, r in prev_round.items():
            if r["ok"]:
                for letter, (title, body) in extract_proposals(r["text"]).items():
                    proposals[f"{label_of[n]}-{letter}"] = (n, title, body)
        points, voters = {}, {}
        for n, r in history[-1].items():
            if not r["ok"]:
                continue
            for rank, vid in enumerate(parse_votes(r["text"], label_of[n], set(proposals))):
                points[vid] = points.get(vid, 0) + (3 - rank)
                voters.setdefault(vid, []).append(label_of[n])
        ranking = sorted(points, key=lambda k: (-points[k], -len(voters[k]), k))
        rows = ["| Hạng | ID | Đề xuất | Của | Điểm | Người bầu |", "|---|---|---|---|---|---|"]
        for i, vid in enumerate(ranking, 1):
            n, title, _ = proposals[vid]
            rows.append(f"| {i} | {vid} | {title} | {n} | {points[vid]} | {', '.join(voters[vid])} |")
        tally_md = "\n".join(rows) if ranking else "_(Không đọc được phiếu bầu nào — xem từng câu trả lời.)_"
        (out / "votes.md").write_text(f"# Bảng xếp hạng đồng thuận — {out.name}\n\n{tally_md}\n", encoding="utf-8")
        status["ranking"] = [{"id": v, "points": points[v], "voters": voters[v]} for v in ranking]

    # ---- sources.md: mọi nguồn các thành viên đã tra cứu (để researcher kiểm chứng bằng WebFetch)
    src_lines, total_src, total_search = [], 0, 0
    if research_sources:
        src_lines.append(f"\n### Perplexity ({research_mode}) — tra cứu trước vòng 1\n")
        for title, u in research_sources:
            src_lines.append(f"- {title or '(không tiêu đề)'} — {u}\n")
            total_src += 1
    for rnd_i, res_i in enumerate(history, 1):
        for n in sorted(res_i, key=lambda x: int(label_of[x][1:])):
            r = res_i[n]
            total_search += r.get("searches", 0)
            if r.get("sources"):
                src_lines.append(f"\n### {label_of[n]} = {n} — vòng {rnd_i} — {r.get('searches', 0)} lượt search\n")
                for title, u in r["sources"]:
                    src_lines.append(f"- {title or '(không tiêu đề)'} — {u}\n")
                    total_src += 1
    sources_md = ("".join(src_lines) if src_lines else "_(Không thành viên nào trả về nguồn.)_\n")
    (out / "sources.md").write_text(
        f"# Nguồn tra cứu — {out.name}\n\n> Link do model trả về có thể sai hoặc bịa (nhất là link chỉ nằm trong"
        f" văn bản). Mở bằng WebFetch trước khi dựa vào.\n{sources_md}", encoding="utf-8")
    status["searches_total"], status["sources_total"] = total_search, total_src

    # ---- combined.md: tất cả những gì researcher cần đọc
    last = history[-1]
    lines = [f"Hội đồng model — {out.name} — {datetime.now():%Y-%m-%d %H:%M} — {len(history)} vòng\n",
             "\n> Các model KHÔNG thấy code, chỉ thấy brief. Đồng thuận là tín hiệu, không phải bằng chứng — "
             "kiểm chứng với code/log thật trước khi đưa vào PLAN.\n",
             "\n## Thành viên\n"]
    for n in sorted(names, key=lambda x: int(label_of[x][1:])):
        lines.append(f"- {label_of[n]} = {n} ({prov[n]['model']}) — vai: {role_of[n]}\n")
    if len(history) >= 2:
        lines.append(f"\n## Bảng xếp hạng đồng thuận (phiếu vòng {len(history)} cho đề xuất vòng {len(history) - 1})\n\n"
                     f"{tally_md}\n")
        if ranking:
            lines.append(f"\n## Chi tiết top {min(5, len(ranking))} đề xuất được bầu\n")
            for vid in ranking[:5]:
                lines.append(f"\n**{vid}** ({proposals[vid][0]})\n\n{proposals[vid][2]}\n")
    lines.append(f"\n## Câu trả lời vòng cuối (vòng {len(history)})\n")
    for n in sorted(last, key=lambda x: int(label_of[x][1:])):
        r = last[n]
        body = r["text"] if r["ok"] else f"❌ LỖI: {r['text']}"
        lines.append(f"\n---\n\n# {label_of[n]} = {n} ({prov[n]['model']}) — vai: {role_of[n]}\n\n{body}\n")
    if len(history) >= 2:
        prev_dirs = "r1/" if len(history) == 2 else f"r1/ … r{len(history) - 1}/"
        lines.append(f"\n---\n\n_Câu trả lời các vòng trước: thư mục {prev_dirs}_\n")
    lines.append(f"\n_Nguồn tra cứu: {total_src} link từ {total_search} lượt search — xem sources.md_\n")
    (out / "combined.md").write_text("".join(lines), encoding="utf-8")
    (out / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_last = sum(1 for r in last.values() if r["ok"])
    print(f"\n{ok_last}/{len(last)} model trả lời ở vòng cuối · {total_search} lượt search · {total_src} nguồn.", end=" ")
    if ranking:
        print(f"Đề xuất được bầu cao nhất: {ranking[0]} ({proposals[ranking[0]][1]})")
    else:
        print()
    if _HEADROOM["saved"]:
        print(f"🗜️  Headroom tiết kiệm ~{_HEADROOM['saved']} token input.")
    print(f"📁 {out.relative_to(ROOT).as_posix()}/combined.md")


def main():
    ap = argparse.ArgumentParser(description="Hội đồng model phản biện plan")
    ap.add_argument("preset_pos", nargs="?", help="preset: all | stuck | plan | cheap")
    ap.add_argument("--preset", help="giống tham số vị trí")
    ap.add_argument("--only", help="danh sách provider, vd grok,deepseek")
    ap.add_argument("--role", help="ép mọi model dùng cùng 1 vai")
    ap.add_argument("--rounds", type=int, help="số vòng (1 = chỉ độc lập; mặc định theo config)")
    ap.add_argument("--no-search", action="store_true", help="tắt tra cứu web (rẻ hơn, nhanh hơn)")
    ap.add_argument("--search-all-rounds", action="store_true", help="cho tra cứu web ở mọi vòng")
    ap.add_argument("--brief", default="docs/council/brief.md")
    ap.add_argument("--ping", action="store_true", help="kiểm tra key + model")
    ap.add_argument("--models", metavar="PROVIDER", help="liệt kê model của provider")
    ap.add_argument("--find", metavar="TỪ_KHOÁ", help="tìm slug model trên OpenRouter, vd --find grok")
    ap.add_argument("--research", choices=["off", "pro", "deep"],
                    help="tra cứu bằng Perplexity trước vòng 1 (pro: nhanh · deep: kỹ, chậm, đắt)")
    ap.add_argument("--ask", metavar="CÂU_HỎI", help="chỉ hỏi Perplexity 1 câu, lưu vào docs/research/")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_env(ENV_PATH)
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if args.models:
        return cmd_models(args.models, cfg)
    if args.find:
        return cmd_find(args.find, cfg)
    if args.ask:
        return cmd_ask(args.ask, cfg, args.research if args.research in ("pro", "deep") else "pro")
    preset = args.preset or args.preset_pos
    chosen, skipped = select(cfg, args.only, "all" if (args.ping and not preset and not args.only) else preset)
    if args.ping:
        return cmd_ping(chosen, skipped, cfg)
    cmd_run(chosen, skipped, cfg, load_roles(ROLES_PATH), args)


if __name__ == "__main__":
    main()
