#!/bin/bash
# score.sh <task-variant-dir>: grade the variant's environment/app/triage.py (the deliverable) with the
# task's separate verifier image, exactly as the harness does (artifact copied to /app/triage.py,
# --network none, test.sh as root). Writes CTRF to $CTRF_OUT; exit 0 iff reward 1.
set -uo pipefail
V="$1"
IMG="${VERIFIER_IMAGE:-tbrain-linux-host-intrusion-triage:verifier-p2}"
C=$(docker create --network none "$IMG" bash -lc 'install -d -m 700 /logs/verifier; cd /tests; bash test.sh > /logs/verifier/out.log 2>&1; cat /logs/verifier/reward.txt')
if [ -f "$V/environment/app/triage.py" ]; then docker cp "$V/environment/app/triage.py" "$C:/app/triage.py" >/dev/null; fi
OUT=$(docker start -a "$C" | tail -1)
[ -n "${CTRF_OUT:-}" ] && docker cp "$C:/logs/verifier/ctrf.json" "$CTRF_OUT" >/dev/null 2>&1
docker rm -f "$C" >/dev/null 2>&1
echo "reward $OUT"
[ "$OUT" = "1" ]
