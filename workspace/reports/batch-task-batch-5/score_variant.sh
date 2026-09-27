#!/bin/bash
# score_variant.sh <task-dir>
# Verifier command for wrong_path_runner.py on the optimisation tasks of this batch.
# solve.sh in these tasks only copies solution/<out>/*.json into /app/<out>/ and runs
# the checker, so this builds that /app (environment/app plus the variant's
# solution files) and grades it offline with the variant's own separate verifier
# (task-local-solve-probe/scripts/score_app.sh). CTRF goes to $WP_CTRF.
set -uo pipefail
TASK="$(cd "$1" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
SCORE="$HERE/score_app.sh"
OUT="$(sed -n 's#^artifacts = \["/app/\([a-z]*\)/"\]#\1#p' "$TASK/task.toml")"
[ -n "$OUT" ] || { echo "no artifact dir"; exit 2; }
APP="$(mktemp -d)/app"
cp -R "$TASK/environment/app" "$APP"
mkdir -p "$APP/$OUT"
cp "$TASK/solution/$OUT/"*.json "$APP/$OUT/" 2>/dev/null
CTRF_OUT="${WP_CTRF:?set WP_CTRF}" "$SCORE" "$TASK" "$APP"
