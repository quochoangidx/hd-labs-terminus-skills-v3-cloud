#!/bin/sh
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/reports/dc-work
docker run --rm --network none -e FAILS=/w/vfails_$1.json -v "$PWD/variants/$1:/app:ro" -v "$PWD:/w" -w /w pydc-task python3 score_dc.py all_ok.json | tail -1 | sed "s/^/$1: /"
