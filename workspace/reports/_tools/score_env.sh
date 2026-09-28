#!/usr/bin/env bash
# score_env.sh <task-dir>: grade environment/app exactly as it stands (no solve.sh),
# in the task's separate verifier image. Writes CTRF to $SCORE_CTRF (default
# /tmp/score-ctrf.json) and exits 0 iff reward is 1.
set -uo pipefail
TASK="$(cd "$1" && pwd)"
SLUG="$(basename "$TASK")"
CTRF_OUT="${SCORE_CTRF:-/tmp/score-ctrf.json}"
VIMG="score-verifier-$SLUG"
docker build -q -t "$VIMG" "$TASK/tests" >/dev/null || { echo "verifier build failed"; exit 3; }
C="$(docker create --network none --tmpfs /tmp:noexec,nosuid,size=256m "$VIMG" bash -lc 'install -d -m 700 /logs/verifier; cd /tests; bash test.sh > /logs/verifier/test-output.log 2>&1 || true; cat /logs/verifier/reward.txt')"
docker cp "$TASK/environment/app/." "$C:/app" >/dev/null
R="$(docker start -a "$C" | tr -d '[:space:]')"
rm -f "$CTRF_OUT"
docker cp "$C:/logs/verifier/ctrf.json" "$CTRF_OUT" >/dev/null 2>&1 || true
docker cp "$C:/logs/verifier/test-output.log" "${CTRF_OUT%.json}.log" >/dev/null 2>&1 || true
docker rm "$C" >/dev/null
echo "reward=$R"
[ "$R" = "1" ]
