#!/bin/bash
# Build a task's verifier image and grade one port with it.
# Usage: run_verifier.sh <task-dir> <tag> <port.py> <out-dir>
# Writes <out-dir>/ctrf.json, reward.txt and verifier.log.
set -uo pipefail
task="$1"; tag="$2"; port="$3"; out="$4"
mkdir -p "$out"
docker build -q -t "cobol-verifier:$tag" "$task/tests" >/dev/null || { echo "build failed"; exit 2; }
cid=$(docker create --network none "cobol-verifier:$tag" bash /tests/test.sh)
docker cp "$port" "$cid:/app/port/wbill.py" >/dev/null
docker start -a "$cid" >"$out/verifier.log" 2>&1
docker cp "$cid:/logs/verifier/ctrf.json" "$out/ctrf.json" >/dev/null 2>&1
docker cp "$cid:/logs/verifier/reward.txt" "$out/reward.txt" >/dev/null 2>&1
docker rm "$cid" >/dev/null
python3 - "$out" <<'EOF'
import json, sys, os
out = sys.argv[1]
reward = open(os.path.join(out, "reward.txt")).read().strip() if os.path.exists(os.path.join(out, "reward.txt")) else "missing"
try:
    tests = json.load(open(os.path.join(out, "ctrf.json")))["results"]["tests"]
except Exception:
    tests = []
failed = [t["name"] for t in tests if t["status"] != "passed"]
print(f"reward={reward} tests={len(tests)} failed={len(failed)} {failed[:12]}")
EOF
