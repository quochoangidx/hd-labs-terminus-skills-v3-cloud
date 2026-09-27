#!/bin/bash
# usage: run.sh cases.json [pysed_dir]  (default: task solution)
D=${2:-/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/tasks/tbrain-gnu-sed-reimplementation/solution/pysed}
docker run --rm -v "$D":/ref:ro -v "$PWD":/w -w /w preflight-verifier-tbrain-gnu-sed-reimplementation python3 cmp.py "$1" /ref/sed.py $3
