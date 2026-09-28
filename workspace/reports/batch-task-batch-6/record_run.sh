#!/bin/bash
# record_run.sh DIR RUN AGENTID RESULT TYPE REWARD NOTES
set -euo pipefail
D=$1; R=$2; A=$3; RES=$4; TY=$5; RW=$6; N=$7
J=~/.claude/projects/-Users-quochoangdev-HDTechLS-hd-labs-terminus-skills-v3/c6a90440-123b-4024-adea-b69b8d5742a6/subagents/agent-$A.jsonl
cp "$J" "$D/run_$R/agent-transcript.jsonl"
EC=1; [ "$RW" = 1 ] && EC=0
python3 .agent/skills/task-local-solve-probe/scripts/probe.py record "$D/run_$R" --result "$RES" --type "$TY" --notes "$N" \
  --runner claude-agent --runtime claude-code --model claude-opus-5 --reasoning-effort medium --agent-session-id "$A" \
  --launch-command "Agent(subagent_type=terminus-probe, no model argument)" --agent-transcript "$D/run_$R/agent-transcript.jsonl" \
  --agent-jsonl "$J" --verifier-log "$D/run_$R/verification-ctrf.log" --verification-ctrf "$D/run_$R/verification-ctrf.json" \
  --verification-command "score_app.sh: separate verifier image, --network none" --verification-exit-code $EC --reward "$RW"
