#!/bin/sh
# usage: run_variants.sh CASES.json -> writes vres_<variant>_<cases>.json
set -e
C=$1
for v in $(ls variants); do
  docker run --rm --network none -e FAILS=/w/vfails_${v}_$(basename $C .json).json -v "$PWD/variants/$v:/app:ro" -v "$PWD:/w" -w /w pyed-task python3 score_ed.py $C | tail -1 | sed "s/^/$v: /"
done
