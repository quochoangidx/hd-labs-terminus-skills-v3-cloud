#!/bin/bash
# grade_run.sh SLUG OUTDIR RUN SRC — grade a probe run's output files (SRC = solve|at-deadline) with the task verifier.
set -uo pipefail
S=$1; O=$2; R=$3; SRC=$4; cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
D=workspace/local-solve-probes/$S-${5:-local}/run_$R; T=workspace/tasks/$S
F=$D/solve/environment/app/$O; [ "$SRC" = at-deadline ] && F=$D/at-deadline/$O
A=$(mktemp -d)/app; cp -R $T/environment/app $A; mkdir -p $A/$O; cp $F/*.json $A/$O/ 2>/dev/null
CTRF_OUT=$PWD/$D/graded-ctrf.json workspace/reports/batch-task-batch-5/score_app.sh $T $A
python3 -c "
import json; d=json.load(open('$D/graded-ctrf.json'))
print('passed', d['results']['summary']['passed'], 'of', d['results']['summary']['tests']); print('failed:', [t['name'].split('::')[1] for t in d['results']['tests'] if t['status']!='passed'])"
