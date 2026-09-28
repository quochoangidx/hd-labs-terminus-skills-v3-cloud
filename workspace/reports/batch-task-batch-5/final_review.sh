#!/bin/bash
# final_review.sh SLUG "task one-liner" — build the full-visibility packet and run final_review via stb codex.
set -uo pipefail
S=$1; DESC=$2
REPO=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3; R=$REPO/workspace/reports/$S; B=$REPO/workspace/reports/batch-task-batch-5
P=$R/final-review-work; rm -rf $P; mkdir -p $P/prior
rsync -a --exclude __pycache__ --exclude .DS_Store $REPO/workspace/tasks/$S/ $P/
for f in contract_review.md contract-review-adjudication.md adversarial_review.md adversarial-adjudication.md; do [ -f $R/$f ] && cp $R/$f $P/prior/; done
sed "s|__TASK__|$DESC|" $B/final_review_prompt.tmpl > $R/final_review_prompt.md
$REPO/.agent/skills/task-local-solve-probe/scripts/stb_codex.sh $P $R/final_review_prompt.md $R/final_review.md
tail -1 $R/final_review.md.log
