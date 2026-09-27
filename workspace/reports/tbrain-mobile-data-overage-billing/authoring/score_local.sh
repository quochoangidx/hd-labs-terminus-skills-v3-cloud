#!/bin/bash
# score_local.sh <task-dir>: grade <task-dir>/environment/app with the local verifier image (tbrain-mu:verifier,
# built from tests/ by run_verifier.py build) the way score.sh does: /app copied into a fresh no-network container
# with a noexec /tmp. Writes CTRF to $CTRF_OUT; exit 0 iff reward 1.
set -uo pipefail
TASK="$(cd "$1" && pwd)"
APP="$TASK/environment/app"
CTRF_OUT="${CTRF_OUT:?}"
C="$(docker create --network none --tmpfs /tmp:noexec,nosuid,size=256m tbrain-mu:verifier bash -lc 'cd /tests && bash test.sh > /logs/verifier/test-output.log 2>&1; cat /logs/verifier/reward.txt')"
docker cp "$APP/." "$C:/app" >/dev/null
R="$(docker start -a "$C" 2>/dev/null | tail -1)"
docker cp "$C:/logs/verifier/ctrf.json" "$CTRF_OUT" >/dev/null 2>&1 || true
docker cp "$C:/logs/verifier/test-output.log" "${CTRF_OUT%.json}.log" >/dev/null 2>&1 || true
docker rm -f "$C" >/dev/null 2>&1
echo "reward=$R"
[ "$R" = "1" ]
