#!/bin/bash
# score.sh <task-dir> [app-dir]
# Grade an /app tree with the task's separate verifier image, offline, the way the
# platform does: the declared /app artifact is copied into a fresh verifier container.
# app-dir defaults to <task-dir>/environment/app (i.e. the tree as it stands).
# Writes CTRF to $CTRF_OUT (default <task-dir>/../.score-ctrf.json); exit 0 iff reward 1.
set -uo pipefail
TASK="$(cd "$1" && pwd)"
APP="${2:-$TASK/environment/app}"
SLUG="$(basename "$TASK")"
CTRF_OUT="${CTRF_OUT:-$TASK/../.score-ctrf.json}"
IMG="score-$(echo "$SLUG" | tr 'A-Z' 'a-z'):$(cd "$TASK/tests" && find . -type f -not -path '*/__pycache__/*' | sort | xargs shasum -a 256 | shasum -a 256 | cut -c1-16)"
docker image inspect "$IMG" >/dev/null 2>&1 || docker build -q -t "$IMG" "$TASK/tests" >/dev/null || exit 3
C="$(docker create --network none --tmpfs /tmp:noexec,nosuid,size=256m "$IMG" bash -lc 'cd /tests && bash test.sh > /logs/verifier/test-output.log 2>&1; cat /logs/verifier/reward.txt')"
docker cp "$APP/." "$C:/app" >/dev/null
R="$(docker start -a "$C" 2>/dev/null | tail -1)"
docker cp "$C:/logs/verifier/ctrf.json" "$CTRF_OUT" >/dev/null 2>&1 || true
docker cp "$C:/logs/verifier/test-output.log" "${CTRF_OUT%.json}.log" >/dev/null 2>&1 || true
docker rm -f "$C" >/dev/null 2>&1
echo "reward=$R"
[ "$R" = "1" ]
