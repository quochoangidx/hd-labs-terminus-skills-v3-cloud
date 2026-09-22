#!/usr/bin/env bash
# preflight.sh — one-command mechanical gate over a Terminus task folder.
# Runs every packaging/hygiene check from AGENTS.md §8/§9/§10 that a machine
# can run, so returns for mechanical defects stop happening.
#
# Usage: scripts/preflight.sh <task-dir> [--no-docker] [--strict]
#        [--determinism] [--report-json <path>] [--evidence-dir <path>] [--emit-zip <path>]
#   <task-dir>   folder containing task.toml, instruction.md, environment/,
#                solution/, tests/
#   --no-docker  skip the docker build + oracle/nop + noexec-/tmp reruns
#   --strict     promote every WARN to FAIL (required for batch handover)
#   --determinism repeat the verifier and require identical results; deterministic_execution
#                blocks on Minor and nothing else here would notice a flaky suite
#   --report-json write a machine-readable evidence report
#   --evidence-dir retain raw build, solve, verifier, CTRF, and reward artifacts
#   --emit-zip   write the submission zip only after every check passes
#
# Exit 0 = no FAIL rows (WARNs allowed). Docker checks need a running daemon.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# All repository helpers share one version gate. This avoids silently selecting
# macOS /usr/bin/python3 (3.9) for scripts that require tomllib.
PYTHON_BIN="$REPO_ROOT/scripts/python3"

TASK_DIR=""
NO_DOCKER=0
STRICT=0
DETERMINISM=0
REPORT_JSON=""
EVIDENCE_DIR=""
EMIT_ZIP=""
usage() {
  echo "usage: preflight.sh <task-dir> [--no-docker] [--strict] [--determinism] [--report-json <path>] [--evidence-dir <path>] [--emit-zip <path>]"
}
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --no-docker) NO_DOCKER=1 ;;
    --strict) STRICT=1 ;;
    --determinism) DETERMINISM=1 ;;
    --report-json) shift; REPORT_JSON="${1:?--report-json needs a path}" ;;
    --evidence-dir) shift; EVIDENCE_DIR="${1:?--evidence-dir needs a path}" ;;
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
if [ -n "$EVIDENCE_DIR" ]; then
  mkdir -p "$EVIDENCE_DIR"
  EVIDENCE_DIR="$(cd "$EVIDENCE_DIR" && pwd)"
  for evidence_name in \
    docker-agent-build.log docker-verifier-build.log \
    oracle-solve.log oracle-verifier.log oracle-ctrf.json oracle-reward.txt \
    nop-verifier.log nop-ctrf.json nop-reward.txt \
    oracle-noexec-solve.log oracle-noexec-verifier.log \
    oracle-noexec-ctrf.json oracle-noexec-reward.txt; do
    rm -f "$EVIDENCE_DIR/$evidence_name"
  done
fi
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
for f in task.toml instruction.md environment/Dockerfile environment/.dockerignore tests/Dockerfile tests/test.sh; do
  if [ -e "$TASK_DIR/$f" ]; then report PASS "layout:$f" "present"
  else report FAIL "layout:$f" "missing"; fi
done
[ -d "$TASK_DIR/solution" ] && report PASS "layout:solution/" "present" || report FAIL "layout:solution/" "missing"

# 2. .dockerignore required entries (reviewer-return class: harbor-green but returned)
DI="$TASK_DIR/environment/.dockerignore"
if [ -f "$DI" ]; then
  # Match the pattern, not the exact line: `**/.pytest_cache/` ignores the same thing as
  # `.pytest_cache`, so strip the `**/` prefix and the trailing `/` before comparing.
  DI_NORM="$(sed -e 's:^\*\*/::' -e 's:/$::' -e 's/[[:space:]]*$//' "$DI")"
  for entry in .gitignore .pytest_cache .mypy_cache .ruff_cache node_modules .git; do
    if printf '%s\n' "$DI_NORM" | grep -qxF "$entry"; then report PASS "dockerignore:$entry" "present"
    else report FAIL "dockerignore:$entry" "missing (returned-by-reviewer class)"; fi
  done
  # The point is that no env/secret file reaches the image. Demanding the entry when no
  # such file exists anywhere in the context is noise, not safety.
  if printf '%s\n' "$DI_NORM" | grep -qxF ".env"; then
    report PASS "dockerignore:.env" "present"
  elif find "$TASK_DIR/environment" \( -name '.env' -o -name '.env.*' -o -name '*.env' \) -print -quit 2>/dev/null | grep -q .; then
    report FAIL "dockerignore:.env" "an env file exists in the build context and is not ignored"
  else
    report WARN "dockerignore:.env" "not listed; no env file exists in the build context, so add it only as future-proofing"
  fi
  # solution/ and tests/ only matter when they can actually enter the build context.
  # With the context at environment/ they are out of reach and requiring them is noise.
  if grep -qE '^[[:space:]]*context:' "$TASK_DIR/environment/"*.y*ml 2>/dev/null \
    || [ -f "$TASK_DIR/Dockerfile" ]; then
    for entry in solution tests; do
      if printf '%s\n' "$DI_NORM" | grep -qxF "$entry"; then report PASS "dockerignore:$entry/" "present"
      else report FAIL "dockerignore:$entry/" "reachable from the build context and not ignored"; fi
    done
  else
    report PASS "dockerignore:solution+tests" "outside the environment/ build context"
  fi
fi

# 3. Dockerfile hygiene
DF="$TASK_DIR/environment/Dockerfile"
if [ -f "$DF" ]; then
  grep -q '^# syntax=' "$DF" && report FAIL "dockerfile:syntax-line" "remove '# syntax=' (platform can't pull it)" \
    || report PASS "dockerfile:syntax-line" "absent"
  grep -q -- '--mount=type=bind' "$DF" && report FAIL "dockerfile:bind-mount" "convert to plain COPY + rm -rf" \
    || report PASS "dockerfile:bind-mount" "absent"
  grep -Eq '^FROM .*php:.*-cli' "$DF" && report FAIL "dockerfile:php-cli-base" "php:*-cli rejected; use debian bookworm-slim + apt php-cli"
fi

# 4. task.toml checks
TT="$TASK_DIR/task.toml"
if [ -f "$TT" ]; then
  grep -q 'author_name = "anonymous"' "$TT" && grep -q 'author_email = "anonymous"' "$TT" \
    && report PASS "toml:author" "anonymous" || report FAIL "toml:author" "must be literal anonymous/anonymous"
  grep -q '^artifacts = ' "$TT" && report PASS "toml:artifacts" "top-level declaration present" \
    || report FAIL "toml:artifacts" "top-level artifacts array is required"
  grep -q '^subcategory = ' "$TT" && report PASS "toml:subcategory" "present" \
    || report FAIL "toml:subcategory" "exact Terminus 3 subcategory is required"
  grep -q '^expert_time_estimate_hours' "$TT" \
    && report PASS "toml:expert-hours" "present" || report FAIL "toml:expert-hours" "required"
  grep -q '^environment_mode = "separate"' "$TT" \
    && report PASS "toml:separate-verifier" "enabled" || report FAIL "toml:separate-verifier" "required"
  if python3 - "$TT" <<'PYEOF'
import sys, tomllib
task = tomllib.load(open(sys.argv[1], "rb"))
assert task.get("environment", {}).get("network_mode") == "public"
assert task.get("agent", {}).get("network_mode") in {"public", "no-network"}
assert task.get("verifier", {}).get("network_mode") in {"public", "no-network"}
PYEOF
  then
    report PASS "toml:network-mode" "environment public; agent/verifier explicitly valid"
  else
    report FAIL "toml:network-mode" "environment must be public; agent/verifier must each declare public or no-network"
  fi
  OBSOLETE="$(grep -nE '^(version|codebase_size|number_of_milestones|subcategories|allow_internet|expert_time_estimate_min|junior_time_estimate_min)[[:space:]]*=' "$TT" || true)"
  [ -z "$OBSOLETE" ] && report PASS "toml:no-terminus2" "obsolete fields absent" \
    || report FAIL "toml:no-terminus2" "$OBSOLETE"
fi

POLICY_OUTPUT="$("$PYTHON_BIN" "$REPO_ROOT/scripts/task-policy.py" validate-task "$TASK_DIR" 2>&1)"
POLICY_RC=$?
if [ "$POLICY_RC" -eq 0 ]; then
  report PASS "policy:static" "metadata, all Docker stages, verifier, compose, and test runner pass"
else
  # Surface the sub-checker's own failing rows instead of flattening its whole
  # report into one unreadable detail column.
  printf '%s\n' "$POLICY_OUTPUT" | grep -E '^(FAIL|WARN)' | while IFS='|' read -r st name detail; do
    report "$(echo "$st" | tr -d ' ')" "policy:$(echo "$name" | tr -d ' ')" "$(echo "$detail" | sed 's/^ *//')"
  done
  report FAIL "policy:static" "$(printf '%s\n' "$POLICY_OUTPUT" | grep -cE '^FAIL') failing policy row(s) listed above"
fi

# 5. Leak sweep
LEAKS="$(grep -rlE 'CANARY-|CLAUDE\.md|AGENTS\.md' "$TASK_DIR/environment" "$TASK_DIR/tests" "$TASK_DIR/instruction.md" 2>/dev/null || true)"
[ -n "$LEAKS" ] && report FAIL "leak:canary/memory-refs" "$(echo "$LEAKS" | tr '\n' ' ')" || report PASS "leak:canary/memory-refs" "clean"
# A pyproject at environment/ is a task-packaging leak. A nested pyproject under
# environment/app belongs to an upstream Python project and may be required to
# build the submitted artifact.
STRAYS="$(find "$TASK_DIR/environment" \( -name '*.whl' -o -path "$TASK_DIR/environment/pyproject.toml" -o -name '.DS_Store' -o -path '*/.git/*' \) 2>/dev/null | head -5)"
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
PYOUT="$("$PYTHON_BIN" - "$TASK_DIR" "$ZIP_OUT" <<'PYEOF'
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

# 7b. Reward-channel permission is part of verifier isolation, not cosmetic.
TEST_SH="$TASK_DIR/tests/test.sh"
if [ -f "$TEST_SH" ]; then
  # The property is mode 0700 on /logs/verifier before candidate code runs. `install -d -m 700`
  # and `mkdir` + `chmod 700` are equivalent, and chmod may harden several paths at once.
  if grep -Eq '^[[:space:]]*install[[:space:]]+-d[[:space:]]+-m[[:space:]]+0?700[[:space:]]+.*/logs/verifier' "$TEST_SH" \
    || { grep -Eq '^[[:space:]]*mkdir[[:space:]]+(-p[[:space:]]+)?.*/logs/verifier' "$TEST_SH" \
      && grep -Eq '^[[:space:]]*chmod[[:space:]]+(-R[[:space:]]+)?0?700[[:space:]]+.*/logs/verifier' "$TEST_SH"; }; then
    report PASS "verifier:reward-dir-mode" "/logs/verifier is created with mode 0700"
  else
    report FAIL "verifier:reward-dir-mode" "create /logs/verifier with mode 0700 before reward/CTRF or candidate code"
  fi
fi

# 7c. Candidate-controlled build/runtime code must not share the verifier owner.
STATIC_VERIFIER_CHECK="$REPO_ROOT/.agent/skills/task-client-feedback-review/scripts/verifier_static_checks.py"
PRIVILEGE_OUTPUT="$(python3 "$STATIC_VERIFIER_CHECK" "$TASK_DIR" --check privilege 2>&1)"
PRIVILEGE_RC=$?
if [ "$PRIVILEGE_RC" -eq 0 ]; then
  report PASS "verifier:unprivileged-candidate" "candidate-controlled subprocesses are demoted"
else
  report FAIL "verifier:unprivileged-candidate" "$PRIVILEGE_OUTPUT"
fi
ALIGNMENT_OUTPUT="$(python3 "$STATIC_VERIFIER_CHECK" "$TASK_DIR" --check alignment 2>&1)"
ALIGNMENT_RC=$?
if [ "$ALIGNMENT_RC" -eq 0 ]; then
  report PASS "verifier:explicit-promise-alignment" "mechanical preservation-promise checks pass"
else
  report FAIL "verifier:explicit-promise-alignment" "$ALIGNMENT_OUTPUT"
fi
IDENTITY_OUTPUT="$(python3 "$STATIC_VERIFIER_CHECK" "$TASK_DIR" --check identity 2>&1)"
IDENTITY_RC=$?
if [ "$IDENTITY_RC" -eq 0 ]; then
  report PASS "verifier:test-identity" "no request.node.name leak detected"
else
  report FAIL "verifier:test-identity" "$IDENTITY_OUTPUT"
fi
INTERPRETER_OUTPUT="$(python3 "$STATIC_VERIFIER_CHECK" "$TASK_DIR" --check interpreter 2>&1)"
INTERPRETER_RC=$?
if [ "$INTERPRETER_RC" -eq 0 ]; then
  report PASS "verifier:interpreter-permissions" "no unsafe dual Bash-path restore pattern detected"
else
  report FAIL "verifier:interpreter-permissions" "$INTERPRETER_OUTPUT"
fi

# 8. Rubric format (workspace/submissions/SUBMISSION-<slug>.md, if present)
SUB_MD="$REPO_ROOT/workspace/submissions/SUBMISSION-$SLUG.md"
if [ -f "$SUB_MD" ]; then
  RUBOUT="$("$PYTHON_BIN" - "$SUB_MD" <<'PYEOF'
import re, sys
text = open(sys.argv[1]).read()
lines = [l.strip() for l in text.splitlines()]
crit = [l.lstrip("- ").strip() for l in lines
        if re.search(r'[,:]?\s*[+-]\d+\s*\.?\s*$', l) and not l.startswith("#")]
errors = []
total_pos = 0
negative_count = 0
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
    else:
        negative_count += 1
    m2 = re.search(r'(?<![+-])\b(\d+)\s*\.?\s*$', c)
if not crit:
    errors.append("no criteria lines detected")
elif not 10 <= total_pos <= 40:
    errors.append(f"positive sum {total_pos} outside 10-40")
if crit and negative_count < 1:
    errors.append("at least one negative criterion is required")
print("CRIT:%d" % len(crit))
print("ERR:" + ("; ".join(errors) if errors else "none"))
PYEOF
)"
  RERR="$(echo "$RUBOUT" | sed -n 's/^ERR://p')"
  [ "$RERR" = "none" ] && report PASS "rubric:format" "$(echo "$RUBOUT" | sed -n 's/^CRIT://p') criteria, closed-set + sum OK" \
    || report FAIL "rubric:format" "$RERR"
else
  report PASS "rubric:format" "submission rubric is deferred to the submission-only style and ZIP review gates"
fi

# 9. Docker: build both images, solve in the agent image, transfer only declared
# artifacts, then run the separate verifier image.
if [ "$NO_DOCKER" -eq 0 ]; then
  if "$PYTHON_BIN" - <<'PYEOF'
import subprocess
import sys

try:
    result = subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=15,
        check=False,
    )
except (OSError, subprocess.TimeoutExpired):
    sys.exit(1)
sys.exit(0 if result.returncode == 0 else 1)
PYEOF
  then
    report PASS "docker:daemon" "Docker daemon responded within 15 seconds"
  AGENT_IMG="preflight-agent-$SLUG"
  VERIFIER_IMG="preflight-verifier-$SLUG"
  ARTIFACT_LIST="$("$PYTHON_BIN" - "$TT" <<'PYEOF'
import sys, tomllib
task = tomllib.load(open(sys.argv[1], "rb"))
for path in task.get("artifacts", []):
    print(path)
PYEOF
)"
  read -r AGENT_NETWORK_MODE VERIFIER_NETWORK_MODE <<<"$("$PYTHON_BIN" - "$TT" <<'PYEOF'
import sys, tomllib
task = tomllib.load(open(sys.argv[1], "rb"))
print(task.get("agent", {}).get("network_mode", "no-network"), task.get("verifier", {}).get("network_mode", "no-network"))
PYEOF
)"
  AGENT_BUILD_LOG="${EVIDENCE_DIR:-$(mktemp -d)}/docker-agent-build.log"
  VERIFIER_BUILD_LOG="${EVIDENCE_DIR:-$(mktemp -d)}/docker-verifier-build.log"
  if docker build -q -t "$AGENT_IMG" "$TASK_DIR/environment" >"$AGENT_BUILD_LOG" 2>&1; then
    report PASS "docker:agent-build" "$AGENT_IMG"
  else
    report FAIL "docker:agent-build" "agent image build failed; log=$AGENT_BUILD_LOG: $(tail -n 4 "$AGENT_BUILD_LOG" | tr '\n' ' ')"
  fi
  if docker build -q -t "$VERIFIER_IMG" "$TASK_DIR/tests" >"$VERIFIER_BUILD_LOG" 2>&1; then
    report PASS "docker:verifier-build" "$VERIFIER_IMG"
  else
    report FAIL "docker:verifier-build" "verifier image build failed; log=$VERIFIER_BUILD_LOG: $(tail -n 4 "$VERIFIER_BUILD_LOG" | tr '\n' ' ')"
  fi

  if docker image inspect "$AGENT_IMG" >/dev/null 2>&1 && docker image inspect "$VERIFIER_IMG" >/dev/null 2>&1; then
    run_reward() { # run_reward <label> <solve:0|1> <noexec:0|1>
      LABEL="$1"
      DO_SOLVE="$2"
      USE_NOEXEC="$3"
      STAGE_DIR="$(mktemp -d)"
      AGENT_ARGS=(--mount "type=bind,src=$TASK_DIR/solution,dst=/solution,readonly")
      # Keep this non-empty: macOS ships Bash 3.2, where expanding an empty
      # array under `set -u` raises "unbound variable".
      VERIFIER_ARGS=(--label "terminus.preflight=$SLUG")
      [ "$AGENT_NETWORK_MODE" = "no-network" ] && AGENT_ARGS+=(--network none)
      [ "$VERIFIER_NETWORK_MODE" = "no-network" ] && VERIFIER_ARGS+=(--network none)
      if [ "$USE_NOEXEC" -eq 1 ]; then
        AGENT_ARGS+=(--tmpfs /tmp:noexec,nosuid,size=256m)
        VERIFIER_ARGS+=(--tmpfs /tmp:noexec,nosuid,size=256m)
      fi
      AGENT_C="$(docker create "${AGENT_ARGS[@]}" "$AGENT_IMG" sleep infinity)" || { rm -rf "$STAGE_DIR"; return 1; }
      docker start "$AGENT_C" >/dev/null || { docker rm -f "$AGENT_C" >/dev/null 2>&1; rm -rf "$STAGE_DIR"; return 1; }
      if [ "$DO_SOLVE" -eq 1 ]; then
        SOLVE_LOG="${EVIDENCE_DIR:-$STAGE_DIR}/$LABEL-solve.log"
        docker exec "$AGENT_C" bash /solution/solve.sh >"$SOLVE_LOG" 2>&1 || { docker rm -f "$AGENT_C" >/dev/null 2>&1; rm -rf "$STAGE_DIR"; return 1; }
      fi
      while IFS= read -r artifact; do
        [ -n "$artifact" ] || continue
        # A NOP container may legitimately omit a declared file. Let the
        # verifier observe the missing artifact and award 0 instead of
        # treating the transfer as a preflight infrastructure failure.
        docker exec "$AGENT_C" test -e "${artifact%/}" >/dev/null 2>&1 || continue
        mkdir -p "$STAGE_DIR$(dirname "$artifact")"
        case "$artifact" in
          */) mkdir -p "$STAGE_DIR${artifact%/}"; docker cp "$AGENT_C:${artifact%/}/." "$STAGE_DIR${artifact%/}" >/dev/null || { docker rm -f "$AGENT_C" >/dev/null 2>&1; rm -rf "$STAGE_DIR"; return 1; } ;;
          *) docker cp "$AGENT_C:$artifact" "$STAGE_DIR$artifact" >/dev/null || { docker rm -f "$AGENT_C" >/dev/null 2>&1; rm -rf "$STAGE_DIR"; return 1; } ;;
        esac
      done <<EOF
$ARTIFACT_LIST
EOF
      docker rm -f "$AGENT_C" >/dev/null 2>&1

      VERIFIER_C="$(docker create "${VERIFIER_ARGS[@]}" "$VERIFIER_IMG" bash -lc 'install -d -m 700 /logs/verifier; cd /tests; bash test.sh > /logs/verifier/test-output.log 2>&1 || true; cat /logs/verifier/reward.txt')" || { rm -rf "$STAGE_DIR"; return 1; }
      while IFS= read -r artifact; do
        [ -n "$artifact" ] || continue
        case "$artifact" in
          */) [ -d "$STAGE_DIR${artifact%/}" ] || continue; docker cp "$STAGE_DIR${artifact%/}/." "$VERIFIER_C:${artifact%/}" >/dev/null || { docker rm -f "$VERIFIER_C" >/dev/null 2>&1; rm -rf "$STAGE_DIR"; return 1; } ;;
          *) [ -e "$STAGE_DIR$artifact" ] || continue; docker cp "$STAGE_DIR$artifact" "$VERIFIER_C:$artifact" >/dev/null || { docker rm -f "$VERIFIER_C" >/dev/null 2>&1; rm -rf "$STAGE_DIR"; return 1; } ;;
        esac
      done <<EOF
$ARTIFACT_LIST
EOF
      RESULT="$(python3 - "$VERIFIER_C" <<'PYEOF'
import subprocess
import sys

container = sys.argv[1]
try:
    result = subprocess.run(
        ["docker", "start", "-a", container],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
except (OSError, subprocess.TimeoutExpired):
    sys.exit(124)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
sys.exit(result.returncode)
PYEOF
)" || { docker rm -f "$VERIFIER_C" >/dev/null 2>&1; rm -rf "$STAGE_DIR"; return 1; }
      if [ -n "$EVIDENCE_DIR" ]; then
        docker cp "$VERIFIER_C:/logs/verifier/test-output.log" "$EVIDENCE_DIR/$LABEL-verifier.log" >/dev/null 2>&1 || true
        docker cp "$VERIFIER_C:/logs/verifier/ctrf.json" "$EVIDENCE_DIR/$LABEL-ctrf.json" >/dev/null 2>&1 || true
        docker cp "$VERIFIER_C:/logs/verifier/reward.txt" "$EVIDENCE_DIR/$LABEL-reward.txt" >/dev/null 2>&1 || true
      fi
      docker rm "$VERIFIER_C" >/dev/null 2>&1
      rm -rf "$STAGE_DIR"
      printf '%s' "$RESULT"
    }

    R_ORACLE="$(run_reward oracle 1 0 || echo ERR)"
    [ "$R_ORACLE" = "1" ] && report PASS "docker:oracle" "separate-verifier reward 1" || report FAIL "docker:oracle" "reward '$R_ORACLE' (expected 1)"
    R_NOP="$(run_reward nop 0 0 || echo ERR)"
    [ "$R_NOP" = "0" ] && report PASS "docker:nop" "separate-verifier reward 0" || report FAIL "docker:nop" "reward '$R_NOP' (expected 0)"
    R_NOEXEC="$(run_reward oracle-noexec 1 1 || echo ERR)"
    [ "$R_NOEXEC" = "1" ] && report PASS "docker:noexec-tmp" "oracle reward 1 under noexec /tmp" || report FAIL "docker:noexec-tmp" "reward '$R_NOEXEC' — executable staged under bare /tmp?"

    # `deterministic_execution` blocks on Minor, and no other check here would notice a
    # suite that depends on the clock, an unseeded source of randomness, or the order it
    # happens to collect in. Repeating the Oracle is the cheapest way to see it.
    if [ "$DETERMINISM" -eq 1 ]; then
      DET_FAIL=0
      for attempt in 2 3; do
        R_REPEAT="$(run_reward oracle 1 0 || echo ERR)"
        [ "$R_REPEAT" = "$R_ORACLE" ] || { DET_FAIL=1; report FAIL "determinism:repeat-$attempt" "reward '$R_REPEAT' after '$R_ORACLE' on the same snapshot"; }
      done
      [ "$DET_FAIL" -eq 0 ] && report PASS "determinism:repeat" "three Oracle runs agree"
      if [ -f "$TASK_DIR/tests/test.sh" ]; then
        if grep -Eq '(-p no:randomly|PYTHONHASHSEED|--randomly-seed)' "$TASK_DIR/tests/test.sh"; then
          report PASS "determinism:ordering" "collection order is pinned or explicitly randomized"
        else
          report WARN "determinism:ordering" "collection order is neither pinned nor deliberately shuffled — an order-dependent suite passes here and fails on the platform"
        fi
      fi
    fi
  fi
  else
    report FAIL "docker:daemon" "Docker daemon did not respond within 15 seconds"
  fi
else
  report WARN "docker" "skipped (--no-docker)"
fi

echo "----"
if [ -n "$REPORT_JSON" ]; then
  mkdir -p "$(dirname "$REPORT_JSON")"
  "$PYTHON_BIN" - "$SLUG" "$STRICT" "$FAILS" "$REPORT_ROWS" "$REPORT_JSON" "$ZIP_OUT" "$EVIDENCE_DIR" "$TASK_DIR" <<'PYEOF'
import hashlib
import json
import sys
from pathlib import Path

slug, strict, fails, rows_path, output_path, zip_path, evidence_dir, task_dir = sys.argv[1:]


def tree_hash(root):
    digest = hashlib.sha256()
    volatile = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "reports", "submissions"}
    root = Path(root)
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in volatile for part in rel.parts):
            continue
        if path.is_dir() or path.is_symlink():
            continue
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
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
    "task_snapshot_sha256": tree_hash(task_dir),
    "artifact_sha256": hashlib.sha256(open(zip_path, "rb").read()).hexdigest(),
    "checks": checks,
    "evidence_files": {},
}
if evidence_dir:
    for path in sorted(Path(evidence_dir).iterdir()):
        if path.is_file():
            payload["evidence_files"][path.name] = {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
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
[ -n "$EVIDENCE_DIR" ] && echo "  evidence written: $EVIDENCE_DIR"
echo "RESULT: all mechanical checks passed; semantic/manual review remains required."
