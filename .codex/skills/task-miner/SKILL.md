---
name: task-miner
description: Use when mining closed upstream issues or PRs for hard Terminus Regular task candidates from low-to-medium quota Python repos such as pytest-dev/pytest, pypa/pip, django/django, and selected pandas-dev/pandas issues. This metadata-only skill scores candidates, records fixing/parent commits, reproducer shape, runtime risk, dedupe keys, and rejection reasons, but does not scaffold tasks, write verifiers, or patch code. Defaults to pytest-dev/pytest when no repo is specified.
---

# Task Miner

Use this skill when sourcing task ideas from closed upstream issues or PRs. Default source is `pytest-dev/pytest` when the user does not specify another repo.

This is a lightweight mining pass. Do not create a task folder, Dockerfile, verifier, or oracle here. The output is a compact mined candidate artifact consumed later by `task-clone`.

## Source Queue

Prioritize low-to-medium quota sources:

| Repo | Quota burn | Best task domains |
|---|---:|---|
| `pytest-dev/pytest` | low | fixture lifecycle, collection, reporting, assertion rewriting |
| `pypa/pip` | low-medium | resolver behavior, wheel/cache handling, requirement parsing, install/report edge cases |
| `django/django` | medium | ORM/query generation, forms/validation, migrations, template rendering, management commands |
| `pandas-dev/pandas` | medium-high, selective | indexing/groupby/merge/datetime/parser edge cases with tiny datasets |

Heavy repos are allowed only with explicit opt-in and strict limits:

- `numpy/numpy`
- `tokio-rs/tokio`
- `microsoft/TypeScript`
- `ethereum/go-ethereum`
- `pytorch/pytorch`
- `ray-project/ray`

For pandas, mine only localized bugs with small dataframes and no compiled-extension rebuild requirement.

## Heavy Repo Mode

Use this mode for TypeScript, go-ethereum, PyTorch, Ray, NumPy, Tokio, or any repo with large builds/tests.

Hard limits:

- mine at most 1 heavy candidate per session
- inspect at most 5 files before deciding whether to continue
- inspect at most 2 commits around the fix
- do not run full test/build suites
- require a focused staging plan before cloning
- require expected verifier runtime under 60 seconds
- require Docker build context likely under 100 MiB after slimming

Reject heavy candidates unless all are true:

- reproducer can run offline with small fixtures
- bug is localized to a small subsystem
- verifier can use public CLI/API behavior
- no GPU, browser, database, network, cluster, or long compile is needed
- oracle can be a focused patch, not a rebuild of the whole project

Heavy candidate artifacts must include:

```yaml
heavy_repo_mode: true
slimming_plan:
  keep:
  remove:
runtime_budget:
  verifier_sec:
  build_sec:
  expected_context_files:
heavy_rejection_reason:
```

If the slimming plan is unclear, mark `status: rejected` and stop.

## Source Selection

For `pytest-dev/pytest`, prefer closed bugs or PRs involving:

- fixture setup/finalization ordering
- `--maxfail`, `--lf`, `--ff`, `-x`, or interrupt handling
- assertion rewriting and traceback rendering
- parametrization ID generation and collection
- plugin hooks and report lifecycle
- JUnit XML, terminal summary, or warnings integration
- path/import mode edge cases
- xdist-facing behavior only if the task can run without needing xdist

For `pypa/pip`, prefer:

- deterministic resolver conflicts or marker evaluation
- wheel/cache behavior with local fixture files
- requirement file parsing and direct URL handling
- install/report behavior that can run offline from local wheels

Avoid pip candidates that need live package indexes, credentials, platform-specific binary downloads, or network.

For `django/django`, prefer:

- ORM SQL/query behavior reproducible with SQLite
- form/model validation edge cases
- migration state rendering with a tiny project
- template or management-command behavior without external services

Avoid Django candidates needing PostgreSQL/MySQL-specific behavior unless SQLite can faithfully reproduce the bug.

For `pandas-dev/pandas`, prefer:

- tiny dataframe/series reproducers
- indexing, merge, groupby, datetime, parser, or dtype edge cases
- pure-Python test execution without rebuilding C extensions

Avoid pandas candidates that need large datasets, slow IO formats, or compiled-extension changes.

Avoid as Hard tasks:

- documentation-only fixes
- typo or message-only changes
- single-line option validation
- release metadata, dependency bumps, or typing-only PRs
- issues requiring external plugins, network, or unavailable OS services

## Mining Boundary

Do:

- check the candidate registry before spending time on a PR/issue
- verify the issue/PR is closed or merged
- identify the fixing commit and a parent commit before the fix
- inspect only the issue/PR text, changed file list, focused diff hunks, and upstream regression tests
- score candidate quality and runtime risk
- write a compact artifact such as `mined-candidates/<slug>.json`
- append the candidate decision to `mined-candidates/index.jsonl`

Do not:

- scaffold `workspace/tbrain-*`
- write `instruction.md`, Dockerfile, verifier, or oracle patch
- run large upstream test suites repeatedly
- inspect more than 10 files unless the candidate is already high value and needs one extra confirmation
- inspect more than 3 commits around the fix
- enumerate unrelated test suites or full repository trees

Stop mining when a deterministic reproducer, localized touched files, and sufficient candidate score are found.

## Dedupe Registry

Before mining deeply, check:

```text
mined-candidates/index.jsonl
```

If the team has a shared registry path or URL, check that too before claiming a candidate.

Registry identity keys:

- `repo + issue_or_pr_id`
- `repo + fixing_commit`
- `repo + bug_signature`

Reject or skip candidates already marked `cloned`, `submitted`, or `claimed` by another worker. If only the subsystem overlaps but the behavior differs, continue only when `bug_signature` is clearly distinct.

Append one compact JSON line per decision:

```json
{"repo":"pytest-dev/pytest","issue_or_pr_id":"14465","source_url":"...","fixing_commit":"...","parent_commit":"...","bug_signature":"maxfail session fixture teardown reporting","task_slug":"tbrain-maxfail-teardown-reporting","status":"mined","rejection_reason":null}
```

Valid statuses: `mined`, `claimed`, `cloned`, `submitted`, `rejected`.

## Hardness Filter

A good Hard candidate should require the agent to understand at least two pytest subsystems. Examples:

- fixture finalization plus JUnit XML reporting
- collection tree plus import/path mode
- assertion rewriting plus traceback formatting
- warning capture plus terminal reporting
- hook ordering plus test outcome propagation

Reject candidates solvable by only matching the issue title or changing one expected string.

Reject false-hard candidates:

- docs-only, typo-only, dependency bump, CI-only, release metadata, or typing-only
- message-only changes unless the bug is specifically user-facing diagnostic correctness
- single validation branch fixes
- `<= 3` meaningful LOC unless the interaction crosses subsystems
- bugs whose verifier would need network, credentials, browser, database, or OS-specific services

## Candidate Scoring

Score each axis from 1 to 5:

- `subsystem_interaction`: needs multiple pytest subsystems, not one local branch
- `deterministic_reproducibility`: reproduces offline with stable inputs
- `offline_viability`: no external service or missing plugin dependency
- `anti_shortcut_hardness`: hard to satisfy with a narrow hardcode
- `verifier_complexity`: can be tested behaviorally with 4-6 focused tests
- `runtime_cost`: 5 is lightweight, 1 is too heavy
- `leakage_risk`: 5 is low leakage, 1 exposes exact patch/test names

Reject if:

- `subsystem_interaction < 3`
- `deterministic_reproducibility < 4`
- `anti_shortcut_hardness < 3`
- `offline_viability < 4`

Runtime classes:

- `lightweight`: small Python-only reproducer
- `moderate`: imports a real package subset or writes temporary projects
- `heavy`: large install/build or broad suite needed
- `infra-heavy`: database, browser, GPU, network, or OS service; avoid for mass generation

## Output Artifact

Write or return this schema. Keep it compact; raw diffs stay out unless needed.

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
  upstream_regression_tests:
  scoring:
    subsystem_interaction:
    deterministic_reproducibility:
    offline_viability:
    anti_shortcut_hardness:
    verifier_complexity:
    runtime_cost:
    leakage_risk:
  hardness_score:
  reproducibility_score:
  verifier_complexity:
  repo_size_risk:
  leakage_risk:
  heavy_repo_mode:
  slimming_plan:
  runtime_budget:
  rejection_reason:
```

Use `rejection_reason: null` only when the candidate is suitable for cloning.

## Clone Handoff

Pass only the mined artifact to `task-clone` when possible. The clone phase should not re-mine GitHub, rescan history, or re-read unrelated diffs unless the artifact is missing a required field.

## Transformation Hints

1. Pin `environment/repo/` to a parent commit before the fix.
2. Remove upstream tests that reveal the exact patch if needed.
3. Write a prompt describing user-visible behavior only.
4. Put reproducer projects inside verifier tests, not in the prompt.
5. Verify the starting state fails by behavior.
6. Write oracle as `solution/fix.patch` plus `solution/solve.sh`.
7. Test both the regression and normal behavior.

## Prompt Template

```md
Pytest in `/app` mishandles <observable scenario>. A user project that <setup> currently <bad behavior>.

Fix pytest so `python -m pytest <command shape>` <required behavior>. The run should <preserve important existing behavior>. Do not change the user project's tests.
```

Keep issue URLs and PR IDs out of `instruction.md`.

## Verifier Patterns

Verifier tests should create temporary user projects and run:

```python
subprocess.run(
    ["python", "-m", "pytest", "<test file>", "...options..."],
    cwd="/app",
    capture_output=True,
    text=True,
)
```

Assert externally visible behavior:

- return code category
- no `INTERNALERROR` unless explicitly expected
- terminal output includes or excludes key user-facing text
- JUnit XML structure when relevant
- side-effect files prove skipped or unexecuted tests did not run
- behavior without the edge case remains unchanged

## Example Hard Candidate

Issue domain: fixture teardown under `--maxfail=1` with JUnit XML.

Why hard:

- requires runner/session stop logic
- requires fixture teardown reporting
- requires JUnit XML plugin outcome mapping
- cannot be fixed by changing one output string

Expected task behavior:

- first failing test is reported
- already-started fixture teardown error is also reported
- later tests are not executed because maxfail is honored
- no internal traceback
- XML records both failure and error
