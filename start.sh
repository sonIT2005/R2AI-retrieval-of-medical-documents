#!/usr/bin/env bash
# Mở Claude Code đúng "agent tree": Opus phiên chính + Opus làm advisor.
#   ADVISOR=fable ./start.sh  dùng Fable làm advisor (mạnh hơn, đắt hơn — tính vào usage credits)
#   EFFORT=xhigh ./start.sh   tăng effort phiên chính (mặc định high)
#   MODEL=sonnet ./start.sh   phiên chính Sonnet — nên dùng cho /autoresearch chạy qua đêm (đỡ tốn giới hạn)
#   TEAMS=1 ./start.sh        bật agent team cho /debate
#   HEADROOM=1 ./start.sh     chạy qua Headroom (nén output công cụ). Kiểm tra advisor còn chạy không!
ADVISOR="${ADVISOR:-opus}"
EFFORT="${EFFORT:-high}"
MODEL="${MODEL:-opus}"
if [ "${TEAMS:-0}" = "1" ]; then export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1; fi
ARGS=(--model "$MODEL" --effort "$EFFORT" --advisor "$ADVISOR" "$@")
if [ "${HEADROOM:-0}" = "1" ]; then
  export HEADROOM_BEACON="${HEADROOM_BEACON:-off}"     # tắt telemetry ẩn danh của Headroom
  exec headroom wrap claude --code-memory none -- "${ARGS[@]}"
fi
exec claude "${ARGS[@]}"
