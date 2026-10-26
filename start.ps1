# Windows: mở Claude Code đúng "agent tree": Opus phiên chính + Opus làm advisor.
#   $env:ADVISOR="fable"  dùng Fable làm advisor (đắt hơn)  |  $env:EFFORT="xhigh"  tăng effort phiên chính
#   $env:ADVISOR="opus"   đổi advisor     |  $env:TEAMS="1"    bật agent team
#   $env:HEADROOM="1"     chạy qua Headroom (kiểm tra advisor còn chạy không!)
$advisor = if ($env:ADVISOR) { $env:ADVISOR } else { "opus" }
$effort = if ($env:EFFORT) { $env:EFFORT } else { "high" }
$model = if ($env:MODEL) { $env:MODEL } else { "opus" }   # $env:MODEL="sonnet" cho /autoresearch qua đêm
if ($env:TEAMS -eq "1") { $env:CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1" }
$claudeArgs = @("--model", $model, "--effort", $effort, "--advisor", $advisor) + $args
if ($env:HEADROOM -eq "1") {
  if (-not $env:HEADROOM_BEACON) { $env:HEADROOM_BEACON = "off" }
  headroom wrap claude --code-memory none -- @claudeArgs
} else {
  claude @claudeArgs
}
