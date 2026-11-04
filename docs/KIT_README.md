# Bộ khung "agent tree": Opus + Opus advisor + subagents + hội đồng 8 model (OpenRouter)

```
Opus (advisor, on call) ──► Opus — phiên chính · effort high · lên kế hoạch + quyết định
                                 │
                       hooks: luật cứng chạy bằng code
                                 │
              giao việc cho subagents · effort medium (worker: Sonnet · còn lại: Opus)
        ┌────────────────────────┼─────────────────────────────┐
     worker                  explorer                     researcher
  sửa code + chạy test     đọc code, không sửa     hội đồng 8 model: độc lập →
                                                     phản biện chéo ẩn danh → bỏ phiếu
        └────────────────────────┼─────────────────────────────┘
                                 ▼
                 quay về phiên chính · effort high · review + verify
```

Giải quyết 5 vấn đề cụ thể:

| Vấn đề | Cách bộ khung xử lý |
|---|---|
| Claude không tìm ra nguyên nhân để cải thiện | Eval chuẩn xuất `predictions.csv` → subagent `error-analyst` gom lỗi thành "kiểu lỗi" có số liệu → giả thuyết dựa trên bằng chứng, không đoán mò |
| Phải copy prompt đi hỏi 8 trang web | Subagent `researcher` chạy `tools/council.py`: 8 model trả lời độc lập theo vai riêng → đọc câu trả lời ẩn danh của nhau, phản biện, đổi ý, bỏ phiếu → bảng xếp hạng đồng thuận → researcher **kiểm chứng với code thật** → phiên chính review |
| Claude sửa lan sang file không liên quan | Luật phạm vi trong `AGENTS.md` + hook chặn đường dẫn bảo vệ + subagent `scope-reviewer` + commit nhỏ để revert |
| Codebase lớn, Claude không đọc | `docs/CODEMAP.md` do subagent `code-mapper` duy trì; việc đọc rộng giao cho subagent để context chính gọn |
| Hết context là quên đang làm gì | `docs/PROGRESS.md` cập nhật sau mỗi bước + hook `SessionStart` tự nạp lại sau compact/clear + lệnh `/handoff` |

## Cấu trúc
```
AGENTS.md              luật chung cho MỌI agent (Claude, Antigravity, Codex…)
CLAUDE.md              import AGENTS.md + phần riêng cho Claude Code
.claude/
  settings.json        hooks + chặn đọc .env
  protected_paths.txt  danh sách đường dẫn cấm sửa
  hooks/               session_context.py (nạp trí nhớ), protect_paths.py (hàng rào),
                       orchestrate_guard.py (giữ vòng lặp tự sửa chạy đến khi đạt tiêu chí),
                       autoresearch_guard.py (giữ vòng thí nghiệm qua đêm chạy tới deadline)
  agents/              worker, explorer, researcher, criteria-checker, stage-reflector
                       (+ error-analyst, code-mapper, scope-reviewer)
  commands/            /iterate /orchestrate /orchestrate-stop /autoresearch /autoresearch-stop
                       /analyze /council /debate /handoff /map
docs/
  PROGRESS.md PLAN.md EXPERIMENTS.md CODEMAP.md STAGES.md
  reports/             báo cáo tổng kết của /orchestrate
  council/             BRIEF_TEMPLATE.md + các round_XX (kết quả hội đồng)
  analysis/            báo cáo phân tích lỗi, tranh luận
tools/
  council.py council_config.json council_roles.md .env.example
start.sh / start.ps1   mở Claude Code: Opus effort high + Opus advisor (HEADROOM=1 để nén context)
.mcp.json              Context7 — tài liệu thư viện đúng phiên bản
```

## Hội đồng "cùng suy nghĩ" hoạt động thế nào
1. **Vòng 1 — độc lập.** Mỗi model nhận cùng brief nhưng một vai khác nhau (red team, tìm nguyên nhân gốc, soi dữ liệu, kinh nghiệm thi, soát plan, đơn giản hoá, hướng khác, ROI). Không ai thấy ai → tránh a dua.
2. **Vòng 2+ — phản biện chéo.** Mỗi model đọc câu trả lời ẩn danh (M1…M8) của cả hội đồng, chỉ ra điểm mạnh/lỗ hổng, đổi ý nếu người khác đúng hơn, viết lại đề xuất cuối (có thể ghép ý của người khác) và bỏ phiếu top 3 — không được bầu cho mình. Ẩn danh để model không thiên vị theo thương hiệu.
3. **Đếm phiếu** kiểu Borda (3/2/1) → `votes.md` + bảng xếp hạng trong `combined.md`.
4. **Researcher (Opus)** kiểm chứng top đề xuất với code/log thật, giữ cả ý kiến thiểu số có lý → `SYNTHESIS.md`.
5. **Phiên chính** tự kiểm lại 1–2 khẳng định quan trọng, hỏi advisor nếu đổi hướng lớn, rồi mới cập nhật PLAN.

Chi phí: vòng 2 mỗi model phải đọc câu trả lời của cả hội đồng nên tốn input hơn vòng 1 vài lần; `max_chars_per_answer` trong config giới hạn độ dài mỗi câu trả lời được chuyển tiếp. Preset 4 model × 2 vòng là điểm cân bằng tốt; `--rounds 3` khi cần chốt một quyết định lớn.

## Hội đồng qua OpenRouter (1 key) + DeepSeek gọi thẳng
7 model (Grok, GPT, Qwen, GLM, MiniMax, Kimi, Gemini) đi qua OpenRouter bằng một key `OPENROUTER_API_KEY`; DeepSeek vẫn gọi thẳng bằng credit sẵn có.

- **Suy nghĩ sâu:** `"reasoning": {"effort": "high"}` — OpenRouter chuẩn hoá tham số này cho mọi model hỗ trợ.
- **Tra cứu web:** tool `openrouter:web_search` — model tự quyết khi nào search. Model có search gốc (GPT, Gemini, Grok) dùng search của hãng; model khác dùng Exa. Giới hạn chi phí bằng `max_uses`, `max_total_results`, `max_tool_calls` trong config.
- **DeepSeek gọi thẳng** không tra cứu web (API không có), nhận nguồn gián tiếp qua vòng phản biện. Muốn DeepSeek cũng tra cứu: bật `deepseek_or` trong config (đi qua OpenRouter).
- **Slug model** có thể đổi theo thời gian: `python3 tools/council.py --find grok` liệt kê slug, ngữ cảnh, giá, có hỗ trợ reasoning/tools không.
- Mặc định chỉ tra cứu ở vòng 1 (`search_in_rounds`); `--search-all-rounds` / `--no-search` để đổi.
- Mỗi round có `sources.md`; researcher mở lại link quan trọng bằng WebFetch trước khi tin.
- Mặc định `max_tokens` 32k mỗi model, `timeout_seconds` 1200, `max_chars_per_answer` 15k: model suy nghĩ sâu (DeepSeek, Qwen) hay hết token ở mức thấp hơn.
- Slot `minimax` hiện trỏ tới `xiaomi/mimo-v2.6-flash` (tên slot giữ nguyên để không phải sửa preset).

## Kết hợp 3 dự án
| Dự án | Lấy gì | Ở đâu trong bộ khung |
|---|---|---|
| **Agentic Data Scientist** (K-Dense) | Khả năng **tự sửa giữa chừng**: kiểm lại mọi tiêu chí sau mỗi stage, phản tư và sửa các stage còn lại, vòng lặp do code điều khiển chạy tới khi đạt tiêu chí; tra tài liệu thư viện qua Context7 | `/orchestrate` + criteria-checker + stage-reflector + hook `orchestrate_guard.py`, `docs/STAGES.md`, `.mcp.json`. Xem mục "Tự sửa giữa chừng" |
| **Ponytail** | Viết ít code nhất cần thiết nhưng không cắt validation/bảo mật; review kỹ cả ngoài diff; sổ nợ `shortcut:` | Cài plugin (bên dưới). Worker đã có sẵn "bậc thang" của Ponytail; `/iterate`, `/orchestrate` gọi `ponytail-review`; `/handoff` gọi `ponytail-debt` |
| **Headroom** | Nén output công cụ (log train, JSON, grep) trước khi vào context | `HEADROOM=1 ./start.sh`; tuỳ chọn `headroom_compress` trong council |

### Tự sửa giữa chừng (từ Agentic Data Scientist)
Bản gốc tự sửa nhờ 3 thứ, đều đã chuyển sang đây:
1. **Kiểm tiêu chí độc lập sau mỗi stage** — `criteria-checker` tự chạy lệnh, kiểm lại *tất cả* tiêu chí (kể cả cái đã đạt, vì có thể tụt), không tin báo cáo của worker.
2. **Phản tư và sửa plan** — `stage-reflector` chỉ sửa stage chưa làm, không đụng stage đã xong, thêm stage một cách bảo thủ.
3. **Vòng lặp do code điều khiển** — bản gốc có bộ điều phối lặp tới khi đạt hết tiêu chí (giới hạn an toàn). Ở đây là hook Stop `orchestrate_guard.py`: Claude định dừng mà còn tiêu chí chưa đạt thì bị chặn và nhắc chạy tiếp.

Mình làm chặt hơn bản gốc ở các điểm sau:
- **Sửa giữa stage, không đợi hết stage:** worker dừng ngay và báo `KẸT` / `GIẢ ĐỊNH SAI` / `VƯỢT NGÂN SÁCH` khi chạm dấu hiệu xấu; reflector chạy luôn.
- **Dấu hiệu hướng sai viết TRƯỚC khi làm** trong STAGES.md — chỉ chạm các dấu hiệu này (hoặc ≥ 2 bằng chứng độc lập) mới được đổi hướng. Tránh đổi hướng theo cảm tính và tránh ngụy biện "cố thêm chút nữa".
- **Phân biệt lỗi cài đặt với hướng sai:** trước khi kết luận hướng sai phải loại trừ bug (với ML: model phải overfit được một batch nhỏ, so với baseline đơn giản). Phần lớn "hướng không ổn" thực ra là bug.
- **Không dời cột gôn:** reflector không được sửa tiêu chí tổng; muốn đổi thì phải hỏi bạn.
- Đổi hướng lớn → hỏi advisor; không có phương án rõ → hội đồng `cheap` 1 vòng đề xuất hướng thay thế.

Hook tự dừng vòng lặp khi: đạt hết tiêu chí và đã viết báo cáo, `Trạng thái: chờ người dùng`, hết số lượt trong ngân sách, hoặc 3 lượt liên tiếp không có tiến triển. Muốn dừng tay: `/orchestrate-stop` (hoặc nhấn Esc rồi gõ lệnh này). Hook chỉ giữ phiên đã chạy `--start` (nhận ra nhờ mã vòng lặp trong transcript), nên các phiên Claude khác mở cùng project dừng bình thường và không ăn lượt của vòng lặp; sau `/clear` chạy `python3 .claude/hooks/orchestrate_guard.py --claim`. Mọi quyết định nằm trong bảng "Nhật ký quyết định" của STAGES.md.

### Perplexity (qua OpenRouter) — thay cho Perplexity MCP
Perplexity MCP chính thức cần `PERPLEXITY_API_KEY` từ tài khoản API Perplexity riêng. Bộ khung gọi cùng các model Sonar qua OpenRouter bằng key sẵn có:
- `python3 tools/council.py --ask "câu hỏi"` → Sonar Pro Search tra cứu, báo cáo có nguồn lưu ở `docs/research/`. Researcher dùng lệnh này như một "MCP Perplexity".
- `--ask "..." --research deep` → Sonar Deep Research: kỹ hơn nhưng chậm (vài phút) và đắt hơn hẳn vì chạy rất nhiều lượt search. Dành cho chủ đề rộng.
- `/council stuck` với `--research pro` → Perplexity tra cứu trước, kết quả được chèn vào brief để cả hội đồng bàn bạc trên cùng bằng chứng.
- Mặc định tắt (`default_research: "off"`) để không tốn tiền ngoài ý muốn.

### DeerFlow — chưa nên thêm lúc này
DeerFlow 2.0 là cả một "harness" riêng (agent chính, sub-agent, bộ nhớ, sandbox, skill) — trùng vai với Claude Code, cài đặt nặng (Docker, Node 22+, pnpm, uv, nginx) và cần thêm key công cụ tìm kiếm (Tavily hoặc InfoQuest). Không cấu hình DeerFlow dùng đăng nhập Claude Code (OAuth của gói Pro/Max) — dùng token gói Claude trong công cụ bên thứ ba có rủi ro vi phạm điều khoản. Nếu sau này cần báo cáo nghiên cứu dài chạy nền: cấu hình DeerFlow bằng OpenRouter/DeepSeek, cài skill `claude-to-deerflow` để Claude Code giao việc cho nó.

### Autoresearch (port từ karpathy/autoresearch) — thí nghiệm tự động qua đêm
Bản gốc là ~630 dòng huấn luyện LLM nhỏ (nanochat) cho một GPU NVIDIA, kèm `program.md` dạy agent tự sửa `train.py`, chạy 5 phút, giữ nếu tốt hơn, không thì hoàn tác, lặp mãi. Thứ đáng lấy là **vòng lặp trong program.md**, không phải code huấn luyện — nên bộ khung có lệnh `/autoresearch` áp dụng vòng lặp đó cho bài thi của bạn.

Khác bản gốc ở những chỗ quan trọng cho cuộc thi:
- **Code ép chạy tiếp, không dựa vào lời dặn:** hook `autoresearch_guard.py` chặn việc dừng cho tới deadline; kẹt 4 lượt không có thí nghiệm mới thì tự tắt.
- **Code giới hạn file được sửa:** khi bật, `protect_paths.py` chỉ cho sửa các file trong `--editable` (bản gốc chỉ dặn "chỉ sửa train.py").
- **Chống chọn nhầm nhiễu:** chỉ giữ khi tốt hơn ngưỡng nhiễu đo từ seed; cứ 5 lần giữ thì chạy lại best với seed khác. Bản gốc giữ mọi cải thiện vì metric của nó ổn định; tập val trong cuộc thi thường nhỏ và nhiễu hơn nhiều.
- **Chống overfit tập val:** trăm lần chọn giữ/bỏ trên cùng một tập val sẽ dần "học thuộc" nó. Vòng lặp không được nhìn holdout; holdout chỉ đo một lần lúc kết thúc để biết cải thiện có thật không.
- **Không tự merge:** kết quả nằm trên nhánh `autoresearch/<tag>` và SUMMARY.md; bạn quyết định giữ gì.

**Dùng cùng `/orchestrate` (từ Agentic Data Scientist):** hai thứ làm hai việc khác nhau, nối tiếp nhau chứ không thay nhau — `/orchestrate` dựng và sửa hướng (pipeline, eval, holdout, baseline); `/autoresearch` tối ưu trong hướng đã chốt. Không chạy cùng lúc: mỗi hook từ chối bật khi chế độ kia đang chạy, và `/autoresearch` đòi working tree sạch vì nó dùng `git reset --hard`. Trình tự gợi ý: `/orchestrate` → `/autoresearch` qua đêm → sáng `/analyze` + `/council` trên SUMMARY → kẹt ở mức cấu trúc thì quay lại `/orchestrate`.

Chạy qua đêm: `MODEL=sonnet ./start.sh`, rồi `/autoresearch oct12`. Phiên chính Sonnet + Opus advisor đỡ tốn giới hạn gói hơn Opus suốt đêm; hết giới hạn thì vòng lặp dừng giữa chừng. Cần GPU trên chính máy chạy Claude Code. Dừng tay: `/autoresearch-stop`.

### Cài Ponytail
Trong Claude Code, gõ lần lượt:
```
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```
Chỉ cài từ `DietrichGebert/ponytail`. Khi luật Ponytail khác AGENTS.md (phạm vi, eval, file bảo vệ), AGENTS.md thắng — đã ghi trong CLAUDE.md. Làm EDA/notebook khám phá thì `/ponytail lite` cho đỡ gò bó.

### Cài Headroom
```
uv tool install --python 3.13 "headroom-ai[all]"   # hoặc: pip install "headroom-ai[all]"
headroom doctor
HEADROOM=1 ./start.sh                               # Windows: $env:HEADROOM="1"; .\start.ps1
```
- Script tự đặt `HEADROOM_BEACON=off` (Headroom bật telemetry ẩn danh mặc định) và `--code-memory none` (không tự cài thêm Serena).
- **Kiểm tra advisor:** Headroom chạy Claude Code qua một proxy cục bộ; advisor là tool phía server của Anthropic nên có thể không qua được proxy. Sau khi bật, gõ "consult the advisor before continuing" — thấy `Advisor unavailable` thì chọn: bỏ Headroom (`./start.sh` thường) hoặc giữ Headroom và chấp nhận không có advisor.
- `headroom learn` đọc các phiên lỗi và ghi bài học vào `CLAUDE.local.md` — bổ sung cho mục "Bẫy đã biết" trong PROGRESS.

### Context7
`.mcp.json` đã khai báo sẵn. Lần đầu mở Claude Code trong project, chấp nhận server `context7`.

## Cài đặt (~10 phút)
1. Giải nén vào folder dự án (folder rỗng cũng được) → `git init` → commit đầu tiên.
2. `cp tools/.env.example tools/.env` rồi điền 2 key: `OPENROUTER_API_KEY` và `DEEPSEEK_API_KEY`.
3. Kiểm tra slug model: `python3 tools/council.py --find grok` (lặp cho qwen, glm, minimax, kimi, gemini, gpt), sửa `model` trong `tools/council_config.json`, rồi `python3 tools/council.py --ping` cho tới khi đủ ✅.
   - Lỗi 402: hết credit OpenRouter. Lỗi 404 / model not found: sửa slug.
   - Trả về rỗng: model reasoning hết token → tăng `max_tokens` của provider đó.
4. Điền mục **1. Bài toán** trong `AGENTS.md` (metric, lệnh chạy, hạn nộp).
5. Hook trong `.claude/settings.json` gọi `python` (hợp Windows). macOS/Linux không có lệnh `python`: sửa `python` → `python3`. Gõ `/hooks` trong Claude Code để kiểm tra hook đã nhận.
6. Mở bằng `./start.sh` (Windows: `.\start.ps1`) — chạy `claude --model opus --effort high --advisor opus`. Gõ `/model` kiểm tra đang là Opus 5.5.
   - Muốn advisor mạnh hơn cho một phiên quan trọng: `ADVISOR=fable ./start.sh` (cần `/model fable` một lần để đồng ý tính phí vào usage credits).
   - Muốn phiên chính suy nghĩ kỹ hơn: `EFFORT=xhigh ./start.sh`.

## Prompt khởi động (folder rỗng)
Bật plan mode (Shift+Tab) rồi dán:
> Đọc AGENTS.md và docs/. Đề xuất plan cho mốc M1: cấu trúc thư mục, eval chuẩn theo "Hợp đồng eval", baseline đơn giản nhất. Chưa code, chờ tôi duyệt. Sau khi duyệt, cập nhật PLAN.md và PROGRESS.md.

## Vòng lặp hằng ngày
```
/iterate            1 thí nghiệm: giả thuyết → sửa tối thiểu → eval → log → commit/revert
   │  (3 lần liên tiếp không tăng)
   ▼
/analyze            error-analyst: kiểu lỗi + số liệu → mục mới trong PLAN
/council stuck      researcher: 4 model × 2 vòng (độc lập → phản biện chéo → bỏ phiếu) → SYNTHESIS → phiên chính verify → PLAN
/debate             (tuỳ chọn) agent team tranh luận giả thuyết, cố bác bỏ lẫn nhau
   │
   ▼
/iterate …          quay lại vòng lặp
/handoff            trước khi hết context, trước /clear, trước khi chuyển sang Antigravity
```
Preset hội đồng: `stuck` (root cause, red team, data, kinh nghiệm thi), `plan` (soát plan, đơn giản hoá, hướng khác, ROI), `cheap`, `all`. Dùng `plan` trước khi bắt tay vào việc lớn (vd. dựng web), `stuck` khi điểm kẹt.

## Khi nào dùng gì
| Công cụ | Dùng khi | Chi phí |
|---|---|---|
| Phiên chính (Opus, high) | Lên kế hoạch, quyết định, review + verify | vừa |
| Advisor (Opus) | Trước khi chốt plan, lỗi lặp lại, trước khi báo xong | theo lượt gọi |
| Subagent worker (Sonnet, medium) / explorer (Opus, medium) | Sửa code theo spec / đọc code thay phiên chính | thấp–vừa |
| Subagent code-mapper (Haiku) | Quét repo, cập nhật CODEMAP.md | thấp |
| Subagent researcher + hội đồng | Cần góc nhìn nhiều model, khi kẹt, trước plan lớn | vừa + vài cent API/vòng |
| Agent team | Tranh luận giả thuyết; feature lớn chia rõ thư mục (FE/BE/test) | **cao** (mỗi teammate là 1 phiên Claude riêng) |
| Antigravity / tool khác | Claude bế tắc một việc cụ thể; cần "đôi mắt thứ hai" để code | — |

### Bật agent team (thử nghiệm)
Cần Claude Code ≥ v2.1.32. Chạy: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude` (chỉ bật khi cần — khi đã bật, subagent mà Claude đặt tên có thể chạy thành teammate và tốn token hơn). Bắt đầu với 3–4 teammate. Teammate không thừa hưởng lịch sử chat của lead, nên prompt giao việc phải đủ ngữ cảnh (lệnh `/debate` đã làm sẵn).

### Dùng Antigravity / tool khác cùng repo
1. Chạy `/handoff` trong Claude (commit + PROGRESS đầy đủ + prompt bàn giao).
2. Dán prompt bàn giao vào tool kia, kèm: "Đọc AGENTS.md và docs/PROGRESS.md trước. Tuân thủ luật phạm vi. Xong việc thì cập nhật PROGRESS.md và commit."
3. Không để 2 agent sửa cùng lúc trên cùng branch — dùng branch hoặc git worktree riêng.
4. Quay lại Claude: hook tự nạp PROGRESS mới; bảo Claude chạy scope-reviewer trên các commit của tool kia.

## Khi làm web
- Chạy `/council plan` với brief mô tả tính năng + stack trước khi code.
- Ghi cấu trúc thư mục cố định (`frontend/`, `backend/`, `tests/`) và lệnh `dev/test/build/lint` vào AGENTS.md mục 1.
- Viết hợp đồng API (`docs/API.md`) TRƯỚC khi tách việc FE/BE — để agent team mỗi người giữ 1 thư mục mà không giẫm chân nhau.
- Mỗi feature = 1 `/iterate`, "eval" thay bằng: test + build + lint + kiểm thử tay 1 luồng.
- Chạy `/map` mỗi khi thêm module; thêm `package-lock.json`, `migrations/**` đã chạy vào `protected_paths.txt` nếu cần.

## Mẹo dùng Claude hiệu quả
- Một việc một phiên. Xong việc → `/handoff` → `/clear`, đừng kéo phiên tới lúc auto-compact.
- Yêu cầu có tiêu chí đo được ("tăng macro-F1 trên val cố định") thay vì "làm tốt hơn".
- Khi Claude đề xuất, hỏi: "Bằng chứng nào trong predictions.csv ủng hộ điều này?"
- Kết quả tốt bất thường → chạy `/council` với preset chỉ có red team: `python3 tools/council.py --only grok --role red_team`.
- Hook protect_paths là hàng rào phụ (best-effort với lệnh shell); lưới an toàn thật là git — commit thường xuyên.
