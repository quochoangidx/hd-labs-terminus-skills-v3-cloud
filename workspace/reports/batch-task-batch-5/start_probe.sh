#!/bin/bash
# start_probe.sh SLUG OUTDIR — prepare a fresh local probe pair and write fair prompts; prints the deadline.
set -euo pipefail
S=$1; O=$2; SUF=${3:-local}; REPO=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3; cd $REPO
D=workspace/local-solve-probes/$S-$SUF; rm -rf $D
python3 .agent/skills/task-local-solve-probe/scripts/probe.py prepare workspace/tasks/$S --exploratory --runs 2 --output $D >/dev/null 2>&1
find $D -name .DS_Store -delete
diff -rq $D/run_1/solve/environment workspace/tasks/$S/environment >/dev/null && cmp -s $D/run_1/solve/instruction.md workspace/tasks/$S/instruction.md || { echo "solve copy differs"; exit 2; }
[ -z "$(ls $D/run_1/solve | grep -vE '^(environment|instruction.md)$')" ] || { echo "extra files in solve copy"; exit 2; }
DL=$(date -v+95M +%H:%M)
for r in 1 2; do python3 -c "
import sys; t=open('workspace/reports/batch-task-batch-5/probe_prompt.tmpl').read()
t=t.replace('__SOLVE__', sys.argv[1]).replace('__OUT__', sys.argv[4]).replace('__IMAGE__','preflight-agent-'+sys.argv[5]+':latest').replace('__DEADLINE__', sys.argv[2]+' local time (check with the date command)')
open(sys.argv[3],'w').write(t)" "$REPO/$D/run_$r/solve" "$DL" $D/run_$r/solve_prompt_fair.md $O $S; done
python3 -c "import json,sys; json.dump({'slug':sys.argv[1],'deadline':sys.argv[2],'model':'claude terminus-probe agent (model: opus, effort: medium)','runtime':'Claude Code subagent','sandbox':'docker --cpus 2 --network none, agent image','stb':'unavailable: account not authorized for AI credentials'}, open(sys.argv[3],'w'), indent=1)" $S $DL $D/probe-meta.json
echo $DL
