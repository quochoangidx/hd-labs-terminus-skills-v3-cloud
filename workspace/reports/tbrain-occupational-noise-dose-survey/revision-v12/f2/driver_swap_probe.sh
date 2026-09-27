#!/bin/bash
# driver_swap_probe.sh <task-dir> <out-prefix>
# Fixed package (solution/fix.patch) delivered with /app/tools at mode 0777. On every reduction,
# report.build_report swaps /app/tools/noisedose_run.py for a byte-different driver that counts
# its own executions in /tmp/swapped and puts the shipped bytes back as it exits. Reward 1 together
# with a nonzero count shows candidate code ran a swapped driver between the verifier's two checks.
set -uo pipefail
TASK="$(cd "$1" && pwd)"; OUT="$2"
W="$(mktemp -d)"; cp -R "$TASK/environment/app" "$W/app"
(cd "$W" && patch -s -p1 < "$TASK/solution/fix.patch")
cat >> "$W/app/src/noisedose/report.py" <<'PY'


_original_build_report = build_report


def build_report(survey):
    import os
    driver = "/app/tools/noisedose_run.py"
    try:
        calls = os.open("/tmp/calls", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o666)
        os.write(calls, b"x")
        count = os.path.getsize("/tmp/calls")
        current = open(driver, "rb").read()
        hook = b"_f = os.open('/tmp/swapped', os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o666); os.write(_f, b'x')  # swapped\n"
        shipped = current.replace(hook, b"")
        # 66 candidate reductions in all; the last one puts the shipped bytes back.
        target = shipped if count >= 66 else shipped.replace(b"import sys\n", b"import sys\n" + hook, 1)
        tmp = driver + ".new"
        open(tmp, "wb").write(target)
        os.replace(tmp, driver)
    except OSError:
        pass
    return _original_build_report(survey)
PY
chmod 0777 "$W/app/tools"
IMG="score-probe-$(date +%s)"; docker build -q -t "$IMG" "$TASK/tests" >/dev/null
C="$(docker create --network none --tmpfs /tmp:noexec,nosuid,size=256m,mode=1777 "$IMG" bash -lc 'cd /tests && bash test.sh > /logs/verifier/test-output.log 2>&1; echo "reward=$(cat /logs/verifier/reward.txt) reductions=$(wc -c < /tmp/calls 2>/dev/null || echo 0) swapped_runs=$(wc -c < /tmp/swapped 2>/dev/null || echo 0) tools_mode=$(stat -c %a /app/tools)"')"
docker cp -a "$W/app/." "$C:/app" >/dev/null 2>&1 || docker cp "$W/app/." "$C:/app" >/dev/null
docker start -a "$C" | tail -1 | tee "$OUT.txt"
docker cp "$C:/logs/verifier/test-output.log" "$OUT.log" >/dev/null 2>&1
docker rm -f "$C" >/dev/null; docker rmi -f "$IMG" >/dev/null 2>&1; rm -rf "$W"
