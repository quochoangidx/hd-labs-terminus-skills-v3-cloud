#!/bin/sh
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/reports/grep-work
docker run --rm --network none -e FAILS=/w/vfails_$1.json -v "$PWD/variants/$1:/app:ro" -v "$PWD:/w" -w /w pygrep-task python3 score_grep.py all.json | tail -1 | sed "s/^/$1: /"
