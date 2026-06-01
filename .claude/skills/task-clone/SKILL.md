---
name: task-clone
description: Use when transforming a mined closed upstream issue or pull request into a Terminus Regular task under workspace/tbrain-*. Consumes mined_candidate artifacts when available, avoids re-mining GitHub, applies prompt sanitization, repo slimming, behavioral verifier design, oracle creation, and Harbor validation. Task folders must be named tbrain-<problem-slug> without domain/tool filler such as pytest, django, numpy, or repo names unless the problem itself requires it.
---

# Task Clone

Use this skill when the user wants to turn a real upstream closed issue or PR into a hard Terminus Regular task.

Preferred split:

```text
mine = candidate discovery + scoring only
clone = transformation + packaging only
```

If a mined candidate artifact exists, consume it and do not repeat the mining pass unless required fields are missing.

## Core Rule

Task folder names must be:

```text
tbrain-<problem-slug>
```

Task folders must be created under the workspace directory:

```text
workspace/tbrain-<problem-slug>/
```

Do not include repo/tool/domain filler in the slug. Prefer the behavior or bug:

- Good: `tbrain-maxfail-teardown-reporting`
- Good: `tbrain-timezone-cutoff-reconciliation`
- Good: `tbrain-async-cancel-cleanup`
- Bad: `tbrain-pytest-maxfail-teardown-reporting`
- Bad: `tbrain-django-async-cancel-cleanup`

Exception: keep a domain word only when it is part of the actual problem concept, not just the source repo name.

## Inputs

Accept any of:

- a `mined_candidate.json` or equivalent compact artifact
- a GitHub issue URL
- a GitHub PR URL
- `owner/repo` plus a requested domain
- a rough task idea plus a source repo

If a source URL is given without a mined artifact, browse or use `gh` only enough to verify it is closed/merged and identify the fixing PR/commit. Do not perform broad mining inside clone.

## Mined Artifact Contract

When available, clone should start from:

```yaml
candidate:
  source_url:
  issue_or_pr_id:
  repo:
  parent_commit:
  fixing_commit:
  bug_signature:
  touched_files:
  subsystem_tags:
  runtime_class:
  external_requirements:
  repro_summary:
  bad_behavior:
  expected_behavior:
  preserved_behavior:
  edge_cases:
  test_surface:
    primary_api:
    secondary_apis:
    constructor_contracts:
    offline_fixtures:
    skip_guard_policy:
  scoring:
    subsystem_interaction:
    deterministic_reproducibility:
    offline_viability:
    anti_shortcut_hardness:
    verifier_complexity:
    runtime_cost:
    leakage_risk:
```

If this exists, inspect only touched files, focused upstream tests, and support files needed to stage/build/run the task. Do not rescan large repo history or re-open unrelated issues.

If the artifact is missing `test_surface` details for a secondary implementation
that tests will cover, fill that gap before writing verifier tests. Do not guess
constructor signatures from class names.

## Dedupe Registry

Before cloning, check:

```text
mined-candidates/index.jsonl
```

If a shared team registry exists, check it too. Treat any matching `repo + fixing_commit`, `repo + issue_or_pr_id`, or `repo + bug_signature` with status `claimed`, `cloned`, or `submitted` as already taken unless the user explicitly wants a variant.

During clone, update or append a compact JSON line:

```json
{"repo":"pytest-dev/pytest","issue_or_pr_id":"14465","source_url":"...","fixing_commit":"...","parent_commit":"...","bug_signature":"maxfail session fixture teardown reporting","task_slug":"tbrain-maxfail-teardown-reporting","status":"cloned","rejection_reason":null}
```

Use `bug_signature` for near-duplicate detection when issue and PR URLs differ but the fix is the same behavior.

## Candidate Selection

Prefer candidates with:

- a real bug, not docs-only text
- a fix that changed tests upstream
- 50-500 meaningful LOC, or a smaller fix involving subtle cross-module behavior
- deterministic local reproduction
- no live credentials, no external service, no network needed at runtime
- at least two interacting subsystems

Reject candidates that are:

- docs-only, typo-only, dependency bump, CI-only, release metadata
- single-line validation or obvious message change
- tiny one-file patches where the likely solution is one branch or one flag check
- tasks whose verifier cases are mostly variants of the same condition
- too broad to isolate into one task
- impossible to test offline in Docker
- likely to pass current frontier agents in one shot

For Python Hard tasks, the final task must realistically target `difficulty = "hard"`.

## Workflow

1. Load the mined artifact or verify the source URL with the smallest needed browse/`gh` pass.
2. Choose the parent commit before the fix for `environment/repo`.
3. Create `workspace/tbrain-<problem-slug>` using the naming rule.
4. Stage the repo or focused subset under `environment/repo`, not by runtime network fetch.
5. Slim the repo to bug-relevant modules, support utilities, and minimal build config.
6. Write sanitized `instruction.md` from observable behavior only.
7. Write `task.toml` using `version = "2.0"`, `number_of_milestones = 0`, `allow_internet = false`, valid category/subcategories, and realistic resources.
8. Write `environment/Dockerfile` with digest-pinned `FROM`, `tmux`, `asciinema`, `bash`, useful search/edit tools, and required pinned deps.
9. Write `solution/fix.patch` and `solution/solve.sh` that apply a generalized fix and rebuild if needed.
10. Write behavioral `tests/test_outputs.py` and offline `tests/test.sh`.
11. Validate baseline: nop fails for the intended reason only; oracle passes all verifier tests.
12. Run structural checks, CI checks, and optional real-agent trials.

## Regular Layout

```text
workspace/tbrain-<problem-slug>/
├── instruction.md
├── task.toml
├── pyproject.toml              # add when excluding environment/repo from ruff
├── environment/
│   ├── .dockerignore
│   ├── Dockerfile
│   └── repo/
├── solution/
│   ├── solve.sh
│   └── fix.patch
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── reports/                    # optional local notes; exclude from ZIP
    └── mining_notes.md
```

For a small app task, `environment/app/` is acceptable, but cloned upstream bug tasks should normally use `environment/repo/`.

Prefer external notes under `workspace/reports/<task-slug>/` when possible so submission zips do not accidentally include them.

## Metadata Defaults

Use:

```toml
version = "2.0"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "hard"
category = "debugging"
subcategories = ["tool_specific"]
number_of_milestones = 0
codebase_size = "small"
languages = ["python"]
tags = ["<3-6 useful tags>"]
expert_time_estimate_min = 60
junior_time_estimate_min = 180

[verifier]
timeout_sec = 600.0

[agent]
timeout_sec = 1800.0

[environment]
allow_internet = false
build_timeout_sec = 1800.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
```

Valid categories are only:

```text
system-administration
build-and-dependency-management
data-processing
games
software-engineering
machine-learning
debugging
security
scientific-computing
```

Valid subcategories are only:

```text
long_context
tool_specific
api_integration
db_interaction
ui_building
```

Python tasks must be hard. Avoid `codebase_size = "minimal"` for new tasks; stage enough files to justify `small` or use a real large repo.

## Instruction Style

Write like a real engineer reporting a bug:

- 1-3 short paragraphs.
- Absolute paths only, such as `/app` and `/app/src/module.py`.
- State observable contract and exact user-facing strings only if tests assert them.
- No issue URLs, PR numbers, test names, rubrics, or solution hints.
- No step-by-step implementation guide.
- No task name in the prompt.
- No canary strings.
- If tests require a secondary implementation that is not obvious from the
  public behavior, name the relevant module or file path without giving the
  exact patch. This is allowed instruction sufficiency, not a solution hint.

Prompt sanitizer must remove:

- issue URLs, PR numbers, commit hashes
- upstream test names and fixture names copied from the PR
- internal helper/function names unless they are public API
- implementation guidance such as "change `nextitem`" or "edit `runtestprotocol`"
- benchmark meta language such as verifier, oracle, hidden tests, rubric, or CI

Good shape:

```md
The package in `/app` mishandles <scenario>. A user who <does normal workflow> currently sees <bad observable behavior>.

Fix it so `<public command or API>` <observable result>. The run should still <preserve important behavior>, and <edge case contract>.
```

## Docker Rules

`environment/Dockerfile` must:

- use `FROM ...@sha256:<digest>`
- install `tmux`, `asciinema`, `bash`, and usually `util-linux`
- include practical agent tools such as `git`, `ripgrep`, and `sed`/`coreutils` when the base image lacks them
- install build tools only when the agent must rebuild source
- pin Python/package dependencies exactly
- avoid `COPY tests/` and `COPY solution/`
- avoid creating `/tests`, `/oracle`, `/solution`, or `/logs/verifier`
- work with `allow_internet = false` at agent/verifier runtime

Add task-root `pyproject.toml` for upstream repos:

```toml
[tool.ruff]
target-version = "py312"
extend-exclude = ["environment/repo"]
```

Remove macOS junk and secret-shaped files:

```bash
find <task> \( -name '.DS_Store' -o -name '._*' -o -name '__MACOSX' \) -print
find <task>/environment -type f \( -name '*.key' -o -name '*.pem' -o -name '*.crt' -o -name 'id_rsa*' \) -print
```

## Oracle Pattern

For cloned repo tasks:

```bash
#!/bin/bash
set -euo pipefail

cd /app
patch -p1 < /solution/fix.patch
python -m pytest <focused smoke test or upstream regression>
```

If the project requires build artifacts, rebuild them in `solve.sh`. The patch must solve the general bug, not only verifier examples.

## Verifier Pattern

`tests/test_outputs.py` should create temporary reproducer projects or inputs and run the target externally.

Use real parsers for JSON/XML/CSV. Assert behavior, not source shape.

Verifier matrix must include:

- direct upstream regression
- boundary or ordering edge case
- normal behavior preservation
- anti-shortcut check
- no internal crash/traceback when the expected behavior is recoverable
- output format/schema check when relevant

Every test function needs a docstring. Every asserted behavior must be present in `instruction.md`.

Preservation tests are not exempt from prompt coverage. If a verifier checks that non-target modes, aliases, fallback paths, legacy layouts, or normal behavior still work, `instruction.md` must say so naturally.

Example:

```md
Fix the `--import-mode=importlib` collection case. Keep the existing `prepend` and `append` import modes working for the same shadowed-layout projects, and preserve assertion rewriting for nested package tests.
```

Anti-shortcut tactics:

- use temporary directories and generated project names
- vary filenames, ordering, or input values across tests
- include one unseen variant not present in the upstream PR
- avoid exact source-code assertions
- parse outputs semantically rather than matching full files

The oracle patch must pass the direct regression and at least one variant, proving it is not verifier-targeted hardcoding.

## Verifier API Sanity

Before packaging, run a focused smoke check for every import and constructor
used by `tests/test_outputs.py`.

For each tested API/class, verify:

- the import works in the pinned starting repo
- the constructor call matches the real signature
- the object under test actually owns the method/property being asserted
- skip guards catch only genuine absence, not broken construction or wrong API
- wrappers and raw containers are not confused

Bad pattern:

```python
try:
    from package.platform.response import RawResponse
except ImportError:
    pytest.skip("not available")

resp = RawResponse(wrapper_like_arg, request_method="GET")
```

The `ImportError` guard does not protect against a wrong constructor. If the
class exists, a `TypeError` is a verifier bug. Use the real wrapper class or
remove the secondary-implementation test.

Recommended smoke command before Harbor:

```bash
cd <task-folder>
python3 -m py_compile tests/test_outputs.py
```

Then run oracle and nop. A broken verifier must be fixed before any difficulty
or quality signal is trusted.

## tests/test.sh

Prefer the docs/current offline pattern with pytest already installed in the image:

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

cd /app

python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

Dependency policy is platform-sensitive. Never download from the network in
`tests/test.sh`.

Use the mode that matches the active platform quality checker:

- If the checker flags `test_deps_in_image`, keep test-only dependencies out of
  the app image and install them in `tests/test.sh` from bundled local wheels
  with `--no-index`.
- If the checker follows the newer docs that require baked verifier deps,
  install `pytest`, `pytest-json-ctrf`, and verifier deps in the Dockerfile.

In both modes, pin exact versions and keep runtime/project dependencies separate
from verifier-only dependencies. For editable installs of the target package,
prefer `pip install --no-deps -e .` after installing pinned deps so project
metadata cannot fetch or override unpinned packages.

## Quality Preflight

Before packaging or platform upload:

- run an instruction/test symmetry audit: every exact string, CLI flag, output key, XML/JSON field, ordering guarantee, and file path asserted by tests must be stated in `instruction.md`
- include preservation/non-regression test coverage in the prompt, including modes not directly part of the bug trigger
- run a verifier API sanity audit for every imported class/function and every
  constructor used in tests
- remove implementation hints, issue URLs, PR IDs, commit hashes, upstream test names, and private helper names from `instruction.md`
- verify `tests/test.sh` does not run `apt-get`, `npm install`, or network downloads; if it runs `pip install`, it must use only bundled local wheels with `--no-index`
- verify Dockerfile does not `COPY tests/`, `COPY solution/`, or create `/tests`, `/solution`, `/oracle`, `/logs/verifier`
- verify `environment/ <= 100 MiB` and no file under `environment/` exceeds `50 MiB`
- remove `.ruff_cache`, `.pytest_cache`, `__pycache__`, `.DS_Store`, `._*`, `__MACOSX`, reports, logs, and local notes from the submission ZIP
- run oracle and nop; nop must fail for the intended behavior, not missing deps or setup errors

## Quota Discipline

Avoid monolithic end-to-end exploration. After each phase, compress findings into compact notes and stop carrying raw diffs unless needed.

Exploration limits:

- inspect `<= 10` source/test files unless blocked
- inspect `<= 3` commits around the fix
- do not enumerate full repo trees or unrelated test suites
- reuse upstream regression tests as inspiration, but wrap them in behavioral verifier tests

For large repos such as TypeScript, go-ethereum, PyTorch, pandas, or NumPy, use focused staging/sparse extraction and strict runtime checks before investing in verifier/oracle work.

## Validation

Run what is available:

```bash
harbor run -a oracle -p <task-folder>
harbor run -a nop -p <task-folder>
harbor tasks check -m openai/@openai/gpt-5.2 <task-folder>
```

If Docker is not running, still run static checks:

```bash
python3 -m py_compile <python files>
python3 - <<'PY'
import tomllib
tomllib.load(open("task.toml", "rb"))
PY
```

Before submission, real-agent pass rate must be below 80%; Python tasks should target hard.

Difficulty gate:

- If any frontier reference agent passes `5/5`, treat the task as Medium unless another agent family consistently fails for implementation reasons.
- If aggregate real-agent pass rate is `>= 80%`, do not submit as Hard; re-mine or redesign.
- If the oracle patch is `<= 10` meaningful LOC in one obvious file, require empirical agent failures before keeping it.
- Timeouts count as weak evidence only; a good Hard task should produce wrong/partial fixes, not mostly environment/tooling timeouts.

## Final Packaging

Zip task contents, not the containing folder:

```bash
cd tbrain-<problem-slug>
find . \( -name '.DS_Store' -o -name '._*' -o -name '__pycache__' -o -name '.ruff_cache' -o -name '.pytest_cache' -o -name '.mypy_cache' \) -print
TASK_NAME="$(basename "$PWD")"
mkdir -p ../submissions
zip -rX "../submissions/${TASK_NAME}.zip" instruction.md task.toml pyproject.toml environment solution tests \
    -x '*.DS_Store' -x '__MACOSX/*' -x '*/__pycache__/*' -x '*/.ruff_cache/*' -x '*/.pytest_cache/*' -x '*.pyc'
```

Regular task ZIPs must include task-root `pyproject.toml`. The ZIP must contain only submission-required files/folders, not `reports/`, `submissions/`, `workspace/`, logs, caches, or scratch notes.

## Hand-Off

When done, report:

- source issue/PR URL and pinned starting commit
- task folder path
- task slug under `workspace/` and why the name omits repo/domain filler
- tests included and which prompt requirement each covers
- validation commands run and results
- any blocked step, especially Docker/Harbor/API key availability
