#!/usr/bin/env bash
# preflight.sh — one-command mechanical gate over a Terminus task folder.
# Runs every packaging/hygiene check from AGENTS.md §8/§9/§10 that a machine
# can run, so returns for mechanical defects stop happening.
#
# Usage: scripts/preflight.sh <task-dir> [--no-docker] [--strict]
#        [--report-json <path>] [--emit-zip <path>]
#   <task-dir>   folder containing task.toml, instruction.md, environment/,
#                solution/, tests/
#   --no-docker  skip the docker build + oracle/nop + noexec-/tmp reruns
#   --strict     promote every WARN to FAIL (required for batch handover)
#   --report-json write a machine-readable evidence report
#   --emit-zip   write the submission zip only after every check passes
#
# Exit 0 = no FAIL rows (WARNs allowed). Docker checks need a running daemon.
set -uo pipefail

TASK_DIR=""
NO_DOCKER=0
STRICT=0
REPORT_JSON=""
EMIT_ZIP=""
usage() {
  echo "usage: preflight.sh <task-dir> [--no-docker] [--strict] [--report-json <path>] [--emit-zip <path>]"
}
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --no-docker) NO_DOCKER=1 ;;
    --strict) STRICT=1 ;;
    --report-json) shift; REPORT_JSON="${1:?--report-json needs a path}" ;;
    --emit-zip) shift; EMIT_ZIP="${1:?--emit-zip needs a path}" ;;
    --*) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    *)
      [ -z "$TASK_DIR" ] || { echo "only one task directory may be provided" >&2; usage >&2; exit 2; }
      TASK_DIR="$1"
      ;;
  esac
  shift
done
[ -n "$TASK_DIR" ] || { usage >&2; exit 2; }
TASK_DIR="$(cd "$TASK_DIR" && pwd)" || exit 2
SLUG="$(basename "$TASK_DIR")"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_ROWS="$(mktemp)"
trap 'rm -f "$REPORT_ROWS"' EXIT

FAILS=0
report() { # report <PASS|WARN|FAIL> <check> <detail>
  STATUS="$1"
  DETAIL="$(printf '%s' "$3" | tr '\t\r\n' '   ')"
  if [ "$STRICT" -eq 1 ] && [ "$STATUS" = "WARN" ]; then
    STATUS="FAIL"
    DETAIL="strict mode: $DETAIL"
  fi
  printf '%-4s | %-28s | %s\n' "$STATUS" "$2" "$DETAIL"
  printf '%s\t%s\t%s\n' "$STATUS" "$2" "$DETAIL" >> "$REPORT_ROWS"
  if [ "$STATUS" = "FAIL" ]; then FAILS=$((FAILS + 1)); fi
  return 0
}
echo "== preflight: $SLUG =="
printf '%-4s | %-28s | %s\n' "----" "----------------------------" "------"

# 1. Layout
for f in task.toml instruction.md environment/Dockerfile environment/.dockerignore tests/test.sh; do
  if [ -e "$TASK_DIR/$f" ]; then report PASS "layout:$f" "present"
  else report FAIL "layout:$f" "missing"; fi
done
[ -d "$TASK_DIR/solution" ] && report PASS "layout:solution/" "present" || report FAIL "layout:solution/" "missing"

# 2. .dockerignore required entries (reviewer-return class: harbor-green but returned)
DI="$TASK_DIR/environment/.dockerignore"
if [ -f "$DI" ]; then
  for entry in .gitignore .pytest_cache .mypy_cache .ruff_cache node_modules "solution/" "tests/" .env "**/.git"; do
    if grep -qxF "$entry" "$DI"; then report PASS "dockerignore:$entry" "present"
    else report FAIL "dockerignore:$entry" "missing (returned-by-reviewer class)"; fi
  done
fi

# 3. Dockerfile hygiene
DF="$TASK_DIR/environment/Dockerfile"
if [ -f "$DF" ]; then
  grep -q '^# syntax=' "$DF" && report FAIL "dockerfile:syntax-line" "remove '# syntax=' (platform can't pull it)" \
    || report PASS "dockerfile:syntax-line" "absent"
  grep -q -- '--mount=type=bind' "$DF" && report FAIL "dockerfile:bind-mount" "convert to plain COPY + rm -rf" \
    || report PASS "dockerfile:bind-mount" "absent"
  FROM_LINE="$(grep -m1 '^FROM ' "$DF" || true)"
  case "$FROM_LINE" in
    *public.ecr.aws/docker/library/*@sha256:*)
      case "$FROM_LINE" in
        *TODO_RESOLVE*) report FAIL "dockerfile:base-image" "digest placeholder unresolved" ;;
        *) report PASS "dockerfile:base-image" "${FROM_LINE#FROM }" ;;
      esac ;;
    *) report FAIL "dockerfile:base-image" "not canonical digest-pinned public.ecr.aws/docker/library/* : '$FROM_LINE'" ;;
  esac
  grep -Eq '^FROM .*php:.*-cli' "$DF" && report FAIL "dockerfile:php-cli-base" "php:*-cli rejected; use debian bookworm-slim + apt php-cli"
fi

# 4. task.toml checks
TT="$TASK_DIR/task.toml"
if [ -f "$TT" ]; then
  grep -q 'author_name = "anonymous"' "$TT" && grep -q 'author_email = "anonymous"' "$TT" \
    && report PASS "toml:author" "anonymous" || report FAIL "toml:author" "must be literal anonymous/anonymous"
  grep -q '^subcategories = ' "$TT" && report PASS "toml:subcategories" "line present" \
    || report FAIL "toml:subcategories" "line must exist (empty [] is fine; deleting it fails CI)"
  grep -q '^expert_time_estimate_min' "$TT" && grep -q '^junior_time_estimate_min' "$TT" \
    && report PASS "toml:time-estimates" "present" || report FAIL "toml:time-estimates" "both CI-required"
fi

POLICY_OUTPUT="$(python3 "$REPO_ROOT/scripts/task-policy.py" validate-task "$TASK_DIR" 2>&1)"
POLICY_RC=$?
if [ "$POLICY_RC" -eq 0 ]; then
  report PASS "policy:static" "category, languages, and canonical test runner pass"
else
  report FAIL "policy:static" "$POLICY_OUTPUT"
fi

# 5. Leak sweep
LEAKS="$(grep -rlE 'CANARY-|CLAUDE\.md|AGENTS\.md' "$TASK_DIR/environment" "$TASK_DIR/tests" "$TASK_DIR/instruction.md" 2>/dev/null || true)"
[ -n "$LEAKS" ] && report FAIL "leak:canary/memory-refs" "$(echo "$LEAKS" | tr '\n' ' ')" || report PASS "leak:canary/memory-refs" "clean"
STRAYS="$(find "$TASK_DIR/environment" \( -name '*.whl' -o -name 'pyproject.toml' -o -name '.DS_Store' -o -path '*/.git/*' \) 2>/dev/null | head -5)"
[ -n "$STRAYS" ] && report WARN "leak:stray-files" "$(echo "$STRAYS" | tr '\n' ' ')" || report PASS "leak:stray-files" "clean"
grep -qE 'https?://' "$TASK_DIR/instruction.md" 2>/dev/null \
  && report WARN "instruction:external-url" "instruction must be self-contained; verify each URL is not a doc crutch" \
  || report PASS "instruction:external-url" "none"

# 6. Binary-name consistency (heuristic)
BIN_NAME="$(sed -nE 's/^ *BIN(_NAME)? *= *["'\'']([^"'\'' ]+)["'\''].*/\2/p' "$TASK_DIR"/tests/test_outputs.py 2>/dev/null | head -1)"
if [ -n "$BIN_NAME" ]; then
  BASE_BIN="$(basename "$BIN_NAME")"
  MISS=""
  for f in instruction.md solution/solve.sh environment/app/README.md; do
    [ -f "$TASK_DIR/$f" ] && ! grep -q "$BASE_BIN" "$TASK_DIR/$f" && MISS="$MISS $f"
  done
  [ -n "$MISS" ] && report WARN "binary-name:$BASE_BIN" "not mentioned in:$MISS (verify consistency)" \
    || report PASS "binary-name:$BASE_BIN" "consistent"
else
  report PASS "binary-name" "not applicable (no BIN= declaration)"
fi

# 7. Zip build + arcname verification (python zipfile — never Compress-Archive/Explorer)
ZIP_OUT="$(mktemp -d)/$SLUG.zip"
PYOUT="$(python3 - "$TASK_DIR" "$ZIP_OUT" <<'PYEOF'
import os, sys, zipfile
task_dir, zip_out = sys.argv[1], sys.argv[2]
roots = ["task.toml", "instruction.md", "environment", "solution", "tests"]
with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as z:
    for root in roots:
        p = os.path.join(task_dir, root)
        if os.path.isfile(p):
            z.write(p, root)
        elif os.path.isdir(p):
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "target", ".pytest_cache")]
                for fn in filenames:
                    if fn == ".DS_Store" or fn.startswith("._"):
                        continue
                    full = os.path.join(dirpath, fn)
                    arc = os.path.relpath(full, task_dir).replace(os.sep, "/")
                    info = zipfile.ZipInfo.from_file(full, arc)
                    info.external_attr = (0o755 if os.access(full, os.X_OK) else 0o644) << 16
                    with open(full, "rb") as f:
                        z.writestr(info, f.read())
names = zipfile.ZipFile(zip_out).namelist()
bad = [n for n in names if "\\" in n or n.startswith("/") or ".." in n]
wrapper = not any(n == "task.toml" for n in names)
crlf = []
for n in names:
    if n.endswith((".sh", ".patch")):
        if b"\r\n" in zipfile.ZipFile(zip_out).read(n):
            crlf.append(n)
print("BAD:" + (";".join(bad) or "none"))
print("WRAPPER:" + ("yes" if wrapper else "no"))
print("CRLF:" + (";".join(crlf) or "none"))
print("COUNT:%d" % len(names))
PYEOF
)"
BAD="$(echo "$PYOUT" | sed -n 's/^BAD://p')"; WRAP="$(echo "$PYOUT" | sed -n 's/^WRAPPER://p')"
CRLF="$(echo "$PYOUT" | sed -n 's/^CRLF://p')"; COUNT="$(echo "$PYOUT" | sed -n 's/^COUNT://p')"
[ "$BAD" = "none" ] && report PASS "zip:arcnames" "$COUNT entries, forward-slash clean" || report FAIL "zip:arcnames" "$BAD"
[ "$WRAP" = "no" ] && report PASS "zip:no-wrapper-dir" "task.toml at root" || report FAIL "zip:no-wrapper-dir" "no root task.toml — wrapper dir?"
[ "$CRLF" = "none" ] && report PASS "zip:crlf" "clean" || report FAIL "zip:crlf" "CRLF in: $CRLF (breaks git apply)"
[ -n "$EMIT_ZIP" ] && echo "  zip staged pending all checks: $ZIP_OUT"

# 8. Rubric format (submissions/SUBMISSION-<slug>.md, if present)
SUB_MD="$(dirname "$TASK_DIR")/../submissions/SUBMISSION-$SLUG.md"
[ -f "$SUB_MD" ] || SUB_MD="$TASK_DIR/../submissions/SUBMISSION-$SLUG.md"
if [ -f "$SUB_MD" ]; then
  RUBOUT="$(python3 - "$SUB_MD" <<'PYEOF'
import re, sys
text = open(sys.argv[1]).read()
lines = [l.strip() for l in text.splitlines()]
crit = [l.lstrip("- ").strip() for l in lines
        if re.search(r'[,:]?\s*[+-]\d+\s*\.?\s*$', l) and not l.startswith("#")]
errors = []
total_pos = 0
allowed = {1, 2, 3, 5}
for c in crit:
    if not c.startswith("Agent"):
        errors.append("not-Agent-prefixed: " + c[:60])
    m = re.search(r'([+-])(\d+)\s*\.?\s*$', c)
    if not m:
        errors.append("no-score: " + c[:60]); continue
    sign, val = m.group(1), int(m.group(2))
    if val not in allowed:
        errors.append("score-outside-closed-set: " + c[:60])
    if sign == "+":
        total_pos += val
    m2 = re.search(r'(?<![+-])\b(\d+)\s*\.?\s*$', c)
if not crit:
    errors.append("no criteria lines detected")
elif not 10 <= total_pos <= 40:
    errors.append(f"positive sum {total_pos} outside 10-40")
print("CRIT:%d" % len(crit))
print("ERR:" + ("; ".join(errors) if errors else "none"))
PYEOF
)"
  RERR="$(echo "$RUBOUT" | sed -n 's/^ERR://p')"
  [ "$RERR" = "none" ] && report PASS "rubric:format" "$(echo "$RUBOUT" | sed -n 's/^CRIT://p') criteria, closed-set + sum OK" \
    || report FAIL "rubric:format" "$RERR"
else
  report WARN "rubric:format" "no SUBMISSION-$SLUG.md found; rubric unchecked"
fi

# 9. Docker: build, oracle=1, nop=0, oracle-under-noexec-/tmp=1
if [ "$NO_DOCKER" -eq 0 ]; then
  IMG="preflight-$SLUG"
  if docker build -q -t "$IMG" "$TASK_DIR/environment" >/dev/null 2>&1; then
    report PASS "docker:build" "$IMG"
    run_reward() { # run_reward <extra docker args...> ; DO_SOLVE=1|0
      docker run --rm "$@" \
        -v "$TASK_DIR/solution":/solution:ro -v "$TASK_DIR/tests":/tests-src:ro "$IMG" \
        bash -c 'set -e; rm -rf /tests && cp -r /tests-src /tests && chmod -R u+w /tests; \
                 if [ "${DO_SOLVE:-1}" = 1 ]; then cd /app && bash /solution/solve.sh >/tmp/s.log 2>&1 || { echo SOLVE_FAIL; exit 9; }; fi; \
                 mkdir -p /logs/verifier; cd /tests && bash test.sh >/dev/null 2>&1 || true; cat /logs/verifier/reward.txt' 2>/dev/null
    }
    R_ORACLE="$(run_reward -e DO_SOLVE=1 || echo ERR)"
    [ "$R_ORACLE" = "1" ] && report PASS "docker:oracle" "reward 1" || report FAIL "docker:oracle" "reward '$R_ORACLE' (expected 1)"
    R_NOP="$(run_reward -e DO_SOLVE=0 || echo ERR)"
    [ "$R_NOP" = "0" ] && report PASS "docker:nop" "reward 0" || report FAIL "docker:nop" "reward '$R_NOP' (expected 0)"
    R_NOEXEC="$(run_reward -e DO_SOLVE=1 --tmpfs /tmp:noexec,nosuid,size=256m || echo ERR)"
    [ "$R_NOEXEC" = "1" ] && report PASS "docker:noexec-tmp" "oracle reward 1 under noexec /tmp" \
      || report FAIL "docker:noexec-tmp" "reward '$R_NOEXEC' — verifier execs from bare /tmp? (use _find_exec_base)"
  else
    report FAIL "docker:build" "image build failed (run manually for the log)"
  fi
else
  report WARN "docker" "skipped (--no-docker)"
fi

echo "----"
if [ -n "$REPORT_JSON" ]; then
  mkdir -p "$(dirname "$REPORT_JSON")"
  python3 - "$SLUG" "$STRICT" "$FAILS" "$REPORT_ROWS" "$REPORT_JSON" "$ZIP_OUT" <<'PYEOF'
import hashlib
import json
import sys

slug, strict, fails, rows_path, output_path, zip_path = sys.argv[1:]
checks = []
with open(rows_path) as rows:
    for line in rows:
        status, check, detail = line.rstrip("\n").split("\t", 2)
        checks.append({"status": status.lower(), "check": check, "detail": detail})
payload = {
    "task_slug": slug,
    "status": "pass" if int(fails) == 0 else "fail",
    "strict": strict == "1",
    "fail_count": int(fails),
    "artifact_sha256": hashlib.sha256(open(zip_path, "rb").read()).hexdigest(),
    "checks": checks,
}
with open(output_path, "w") as output:
    json.dump(payload, output, indent=2, sort_keys=True)
    output.write("\n")
PYEOF
  echo "  report written: $REPORT_JSON"
fi
if [ "$FAILS" -gt 0 ]; then
  echo "RESULT: $FAILS FAIL row(s) — fix before zipping/submitting."
  exit 1
fi
if [ -n "$EMIT_ZIP" ]; then
  mkdir -p "$(dirname "$EMIT_ZIP")"
  cp "$ZIP_OUT" "$EMIT_ZIP"
  echo "  zip written: $EMIT_ZIP"
fi
echo "RESULT: all checks passed."
