#!/usr/bin/env bash
# Score one wrong-path variant: build its verifier image and run the suite against the
# tree the variant delivers under environment/app. Exit 0 only when the variant is
# accepted (reward 1), which is what wrong_path_runner.py reads as "it survived".
set -uo pipefail
VARIANT="${1:?usage: score_variant.sh <variant-dir>}"
OUT="${WRONGPATH_OUT:?WRONGPATH_OUT must name a directory for the logs and CTRF}"
rm -rf "$OUT"
mkdir -p "$OUT"
docker build -q -t ed-wrongpath-verifier -f "$VARIANT/tests/Dockerfile" "$VARIANT/tests" >/dev/null || exit 2
docker run --rm --network none -v "$VARIANT/environment/app:/app" -v "$OUT:/logs/verifier" \
    ed-wrongpath-verifier bash /tests/test.sh > "$OUT/run.log" 2>&1
[ "$(cat "$OUT/reward.txt" 2>/dev/null || echo 0)" = "1" ]
