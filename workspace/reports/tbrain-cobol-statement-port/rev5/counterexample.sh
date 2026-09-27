#!/bin/bash
# Finding 1: run the panel's reach input (headerless, 500 zero-usage C records,
# empty payments) through a task's GnuCOBOL 3.1.2 build stage and through the given ports.
# Usage: counterexample.sh <task dir> <out dir> <port.py>...
set -uo pipefail
task="$(cd "$1" && pwd)"; out="$2"; shift 2; mkdir -p "$out"; out="$(cd "$out" && pwd)"
docker build -q --target legacy -t cobol-legacy:rev5 "$task/tests" >/dev/null || { echo "build failed"; exit 2; }
python3 - "$out/reach.dat" <<'PY'
import sys
rows = ["C%08d%-24sD000000000000001+00000000000000" % (n, "") for n in range(1, 501)]
open(sys.argv[1], "w").write("".join(r.ljust(80) + "\n" for r in rows))
PY
: > "$out/reach.pay"
docker run --rm -v "$out:/w" cobol-legacy:rev5 sh -c 'cd /w && CUSTIN=reach.dat PAYIN=reach.pay STMTOUT=reach.cobol.stmt /legacy/WBILL'
echo "--- COBOL totals"; grep -E "ACCOUNTS BILLED|TOTAL CURRENT" "$out/reach.cobol.stmt"
for p in "$@"; do
  n=$(basename "$p" .py)
  python3 "$p" "$out/reach.dat" "$out/reach.pay" "$out/reach.$n.stmt"
  if cmp -s "$out/reach.cobol.stmt" "$out/reach.$n.stmt"; then echo "$n: identical"; else echo "$n: DIFFERS"; grep -E "ACCOUNTS BILLED|TOTAL CURRENT" "$out/reach.$n.stmt"; fi
done
