---
name: terminus-hard-python-verifier
description: Use when writing pytest verifier suites and oracle solutions for Python-implemented Terminus 3 tasks. Focuses on isolated artifact-based behavioral tests, anti-cheating coverage, edge cases, and empirical difficulty evidence across all four Terminus 3 tiers.
---

# Terminus 3 Python Verifier

The filename is retained for compatibility, but Python has no special difficulty
rule in Terminus 3. Choose the exact category/subcategory from the task's domain,
not from the fact that the agent edits Python.

This skill is a gate, not just a test-writing checklist. It should reject broken,
ambiguous, trivial, or shortcut-prone tasks while preserving valid Base, Core,
Advanced, and Frontier results.

## When To Stop

Stop and return a redesign recommendation instead of writing verifier code if
any of these are true:

- the expected oracle patch is probably a single obvious branch or <=10
  meaningful LOC in one obvious file
- the prompt keywords point directly to the exact function/class to edit
- all verifier tests exercise the same condition with only renamed inputs
- the task has reached 100% across the four-run platform iteration sample
- the core bug is message-only, typo-only, docs-only, dependency-only, or config
  plumbing without cross-behavior interaction
- the verifier needs credentials, a mutable external service, GPU, or
  long/flaky sleeps

Timeouts never establish a tier. Difficulty evidence must come from semantic
failures tied to the stated crux.

## Difficulty-signal target

Prefer tasks where the correct fix requires coordinating at least two concepts:

- parser state plus error recovery
- cache invalidation plus file system changes
- import/package discovery plus metadata/config parsing
- CLI option interaction plus lifecycle cleanup
- async cancellation plus cleanup/reporting
- serialization schema plus backward compatibility
- dependency resolution plus environment markers
- editable/build backend behavior plus legacy fallback preservation
- stateful idempotency (e.g., executing a command multiple times to verify state transitions)
- complex environment topologies (e.g., symlinks, read-only dirs, conflicting dependencies)

Avoid repeating the same ecosystem or behavior contract. Terminus 3 rejects
variations and reskins even when the implementation language changes.

## Test Design

Write verifier tests that exercise the system from the outside:

- CLI: run `subprocess.run([...], capture_output=True, text=True)`.
- Library: import only public APIs unless the task is explicitly internal.
- Framework: create temporary user projects and invoke the framework command.
- File outputs: parse JSON/XML/CSV with real parsers.

Avoid reading source to assert implementation choices.

Do not assert exact internal helper names, exact source layout, or code shape.
Only assert observable behavior, structured outputs, process status, generated
files, and public API results.

## Coverage Shape

For substantive tasks, include:

- one direct regression reproducer
- one boundary condition
- one normal-behavior preservation test
- one anti-shortcut test
- one test proving the failure mode is recoverable, not just hidden

For stronger Advanced/Frontier calibration, prefer several focused behavior
clusters rather than one monolithic test:

- 2 regression variants using different names/layouts/options
- 1 edge or boundary case
- 1 preservation test for normal or legacy behavior
- 1 strong anti-shortcut test using dynamically randomized inputs (e.g., `random` choices, random lengths) rather than static hardcoded variants
- 1 stateful test running the tool multiple times to verify side-effects, idempotency, or cache correctness
- 1 crash-resistance or structured-output test when relevant

Do not inflate difficulty with many near-duplicate tests. If two tests fail for
the same shallow reason, merge or redesign.

Corpus-graded verifiers (case tables, conformance vectors) add three design
rules on top of the list above:

- **Per-case risk:** a predicted low-pass case is a statistical 0/N risk. Audit
  the oracle, explicit interface, evidence support, and test resolution before
  changing it. Do not automatically disclose an evidence-derived rule or drop
  a valid held-out case from a small local sample.
- **Soft-representative rule and trimming direction:** every feature cluster
  keeps ≥1 "soft" case a majority of runs pass; never build or trim toward a
  hard-cases-only corpus. When cutting, cut data-driven from the per-case pass
  table — easy cases are the coverage that keeps the 0/N flag from firing.
- **Soft size cap and semantic breadth:** ~≤100 curated cases is a useful
  default for conformance corpora. Prefer independently meaningful families
  and hidden generalization under one inferable model over hundreds of
  correlated rows. A single arbitrary hidden convention is invalid; a deep
  evidence-supported inference is not invalid merely because it is difficult.

Count semantic breadth by implementation decisions, not rows. One keyword
tested through eight values, or one numeric stability branch tested at fourteen
scales, remains one mechanism. Before a counted solve probe, write the
mechanism/interaction map and execute one plausible partial-fix mutant for each
node as required by
`terminus-regular-task-authoring/references/semantic-coverage-gate.md`.

## Terminus 3 Contract/Evidence/Test Symmetry

Map every prompt requirement to at least one test. Map each tested behavior
either to the explicit success surface or to an inference family supported by
agent-visible evidence. Do not force every derived semantic rule into
`instruction.md`.

Quality checks often fail when a verifier tests preserved behavior that the
instruction never mentions. Preservation tests are not exempt.

Before finalizing, audit:

- every public CLI flag, output path, and required schema element appears
  naturally in `instruction.md` or a realistic visible format source
- public preservation scope is mentioned, while held-out values/layouts may
  remain hidden when they follow the same inferable invariant
- representation-specific ordering is explicit only when the consumer requires
  it; otherwise parse semantically and accept equivalent outputs
- every required output file/path is named in the instruction
- no test depends on an oracle-only policy, unreachable authority, or arbitrary
  value absent from all visible sources
- every public entry point promised by the instruction has a discriminating
  platform-visible test; no test pins undocumented keyword spelling, internal
  object shape, or exact diagnostic text when equivalent behavior is valid

Example fix:

```text
Fix the `--import-mode=importlib` collection case. Keep the existing `prepend`
and `append` import modes working for the same shadowed-layout projects, and
preserve assertion rewriting for nested package tests.
```

If a test exercises a new instance or combination of the same evidence-backed
model, keep it hidden. If it introduces a new policy, add authentic evidence,
make the interface fact explicit, relax the assertion, or remove the test.

## Verifier Integrity

Keep the end-to-end solution in `solution/`, never in `tests/`. A verifier may
run the candidate, parse output, use golden fixtures/hashes, check
spec-derived invariants, or consume sealed held-out truth; it may not turn task
inputs into the complete expected artifact itself.

If the instruction requires a variable config/input file, read it at runtime
and include a mutation re-run with a changed meaningful value. The original
hardcoded parameter must no longer pass. This does not prohibit hardcoded
expected results, tolerances, or format constants that are not claimed config
values.

Keep goldens and held-out fixtures in the separate verifier image; never derive
expected truth from `/app`, mutable corpora, or agent-delivered trees. Declare
specific top-level artifacts and let the harness transfer them instead of
copying agent-controlled directories where symlinks can expose verifier data.
If tests rebuild or execute agent-supplied code, demote before exec with
`--no-new-privs` or equivalent, keep goldens outside every input tree readable
by that process, and probe that it cannot read protected fixtures or
`/logs/verifier`. Separate mode alone does not create that in-verifier boundary.

Every domain rule explicitly named by the contract needs an isolating fixture
whose result changes when only that rule is inverted. A single multi-rule mutant
or mixed held-out corpus does not establish this, and held-out inputs must not
be the sole enforcement of a stated rule.

When Python verifier code changes interpreter modes, resolve and deduplicate
targets before recording modes and chmod; `/bin/bash` and `/usr/bin/bash` may
resolve to the same file. Restore each saved mode once from `finally`, attempt
all restorations, and confirm Oracle reward/log collection completes. The
platform-only `verifier_interpreter_permissions` preflight blocks the unsafe
dual-path pattern.

Use exact matching when the instruction pins an exact format or byte artifact,
and semantic matching when it does not. A stated numeric tolerance must equal
the verifier tolerance. For optimization/order tasks, include a case where a
merely feasible answer or the wrong tie-break loses, and independently
spot-check the Oracle against a second feasible plan.

## Building stronger Python task signals

Prefer bugs involving interactions:

- datetime/timezone plus deduplication
- Decimal rounding plus aggregation order
- parser state plus error recovery
- cache invalidation plus file system changes
- pytest collection plus fixture teardown/reporting
- async cancellation plus cleanup

Avoid tasks where the fix is a single obvious if-statement unless the surrounding framework behavior is subtle.

## Anti-Shortcut Rules

Use verifier inputs that make hardcoding practically impossible for AI agents:

- generate temp projects under `tmp_path` and use complex topologies (symlinks, nested folders)
- use dynamically varied inputs (for example `uuid`-based names) for package names, strings, and data structures so agents cannot guess expected outputs from test traces; compute expectations from the generated values so tests stay deterministic and non-flaky
- use at least one unseen variant that the oracle patch must generalize to
- parse structured output instead of matching a whole file
- assert both positive and negative behavior where possible (e.g., asserting that unintended files were NOT created, processes did NOT leak)
- verify statefulness by running commands sequentially and ensuring state mutations are handled correctly (e.g., run -> modify -> run again)
- avoid leaking upstream issue URLs, PR numbers, commit hashes, upstream test
  names, or private helper names through test names or instruction text

The verifier can use descriptive local test names, but they should describe
behavior, not expose the upstream implementation strategy.

## Subprocess Test Pattern

```python
def run_cmd(args, cwd, timeout=20):
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
```

On failure, include stderr/stdout in assertion messages. For generated files, assert both existence and parsed content.

Recommended helper:

```python
def combined_output(result):
    return result.stdout + "\n" + result.stderr
```

Use short timeouts for each subprocess. A verifier that regularly approaches
the task timeout is a bad verifier, even if it is semantically correct.

## XML/JSON Output Checks

Use parsers:

```python
import json
import xml.etree.ElementTree as ET

data = json.loads(path.read_text())
tree = ET.parse(path)
```

Check semantic fields rather than full formatting unless sorted key order or exact serialization is a prompt requirement.

If XML/JSON schema details are asserted, `instruction.md` must explicitly state
those fields/tags and whether ordering or multiplicity matters.

## Verifier Quality Gate

Before accepting the verifier, answer these questions:

- Does `nop` fail for the intended behavioral reason only?
- Does `oracle` pass every test deterministically?
- Does each test have a docstring naming the behavior it validates?
- Would a source-grep patch or prompt-keyword search lead directly to the fix?
- Are there at least two independent failure modes for incomplete fixes?
- Has a dedicated executable mutant for every mechanism and interaction been
  killed while retaining both passing and failing tests?
- Are preservation tests explicitly described in `instruction.md`?
- Are verifier dependencies available before `tests/test.sh` starts?
- Does `tests/test.sh` avoid runtime setup and network access?

If any answer is no, repair the task before running real agents.

Before handoff, write a compact requirement-to-test map for the reviewer-facing
Verification Explanation. For each behavioral group, record:

- the observable requirement
- the direct, boundary, preservation, anti-shortcut, or recoverability role
- why the case fails on the buggy state or a plausible partial fix
- whether oracle/nop validation actually ran

Keep this map in external reports, not in `instruction.md`, `environment/`, or
the submission ZIP. The final explanation should describe behavioral coverage,
not test function names, hidden fixture details, or source-code shape.

## tests/test.sh

Use this pattern:

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

python3 -I -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

The final reward block must end the script. The current `check_test_sh` gate
accepts either `if [ $? -eq 0 ]` immediately after pytest or the preferred
defensive form above, where `rc=$?` is captured immediately after pytest and
used in `if [ "$rc" -eq 0 ]`. Do not wrap the block in a helper, add extra
commands between pytest and the capture/conditional, or rewrite it as
`pytest && echo 1`.
End on the reward block's `fi`, with no trailing `exit`. Pytest's status is
captured rather than propagated, while a failed reward write must surface as an
infrastructure error.

Verifier dependencies must be available before `tests/test.sh` starts. Install
`pytest`, `pytest-json-ctrf`, and other verifier-only packages in the separate
`tests/Dockerfile` with exact pins. Create the landing parents for every
top-level artifact path there. Do not put dependency wheels in `tests/`, and do
not run `pip install` from `tests/test.sh`.

Keep project runtime dependencies separate from verifier-only packages.

For Hardware / CAD tasks, use the geometry-specific gate in
`docs/creating-tasks/cad-task-guidelines.md`. Measure every stated dimension on
the built solid with an observable method, keep any sampling grain finer than
the claimed tolerance, verify through/repeated/exact-count features, and test
the Oracle geometry rather than its constants. A parametric requirement needs a
fresh parameter mutation followed by recompute, error checking, and measurement
of the changed solid; parameter readback alone must fail review.

## Oracle Pattern

For large repos:

```bash
#!/bin/bash
set -euo pipefail

cd /app
patch -p1 < /solution/fix.patch
python -m pytest <focused upstream or smoke test>
```

For small apps, `solve.sh` may rewrite files directly, but it must implement general behavior and not encode verifier outputs.

The oracle should pass at least one variant that was not copied directly from
the upstream regression. Reject oracle patches that only satisfy the exact
visible verifier strings, filenames, or fixture names.
