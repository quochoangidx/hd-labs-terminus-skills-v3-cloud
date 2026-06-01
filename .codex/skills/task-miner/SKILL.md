---
name: task-miner
description: Use when mining hard Terminus Regular task candidates, either from closed upstream bugfix issues/PRs or from an explicit category profile such as data-processing, build-and-dependency-management, software-engineering, system-administration, security, scientific-computing, machine-learning, or games. This metadata-only skill scores candidates, records source/base commits, behavior contracts, verifier shape, runtime risk, dedupe keys, and rejection reasons, but does not scaffold tasks, write verifiers, or patch code. Rotate sources instead of defaulting to pytest unless the user asks for pytest specifically.
---

# Task Miner

Use this skill when sourcing task ideas. If the user gives no category, use the default upstream bugfix mode. If the user names a category, use the matching Category Profile and do not force the task into `debugging`.

This is a lightweight mining pass. Do not create a task folder, Dockerfile, verifier, or oracle here. The output is a compact mined candidate artifact consumed later by `task-clone`.

## Operating Modes

### Upstream Bugfix Mode

Use for closed upstream issues/PRs where the task is to diagnose and fix bad behavior. These candidates normally become:

```yaml
category: debugging
subcategories: ["tool_specific"]
```

This mode needs `fixing_commit`, `parent_commit`, `bad_behavior`, `expected_behavior`, and upstream regression-test context.

### Category Profile Mode

Use when the user asks for a non-debugging category or a balanced category batch. Choose the category before mining, then select sources and acceptance criteria that fit that category. Do not accept a candidate whose primary work is bug diagnosis unless the requested category is `debugging`.

Valid categories:

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

For category-profile candidates, `fixing_commit` is optional. The artifact must instead include `base_commit`, `target_behavior`, `required_work`, `input_fixtures`, `output_contract`, and `why_not_debugging` when the category is not `debugging`.

## Category Profiles

- `data-processing`: Mine CLI/scripts/pipelines that transform CSV, JSON, YAML, logs, or directory trees. Accept tasks with joins, filtering, aggregation, schema normalization, deterministic sorting, malformed-input handling, or report generation. Verify by parsing output files/stdout semantically. Reject candidates that are only parser bugfixes, one-expression transforms, or require large/private datasets.
- `build-and-dependency-management`: Mine build config, packaging, lockfile, Docker, Make/Cargo/npm/pip workflows. Accept reproducible offline build/install/test tasks with inspectable artifacts. Reject version bumps, CI metadata, or live registry requirements.
- `software-engineering`: Mine feature/enhancement work where the agent implements or extends a public API/CLI behavior. Accept clear behavior contracts with preserved compatibility. Reject pure bugfixes unless the requested category is `debugging`.
- `system-administration`: Mine local service/config/process/permissions tasks. Accept Docker-contained health checks, config validation, shell automation, users/groups, or process supervision. Reject tasks needing privileged host daemons or external services.
- `security`: Mine local auth, escaping, sanitization, crypto, permissions, or reverse-engineering style tasks. Accept exploit-prevention plus legitimate-use preservation. Reject vague hardening, live targets, secrets, or network-only validation.
- `scientific-computing`: Mine numerical, simulation, geospatial, statistics, or domain-code tasks. Accept deterministic small fixtures with tolerances and boundary cases. Reject GPU, huge datasets, or compiled-extension rebuild requirements unless explicitly approved.
- `machine-learning`: Mine tiny offline data-loader, inference, tokenizer, metric, or evaluation tasks. Accept deterministic seeds and small fixtures. Reject downloads, GPU, model registry, or expensive training.
- `games`: Mine terminal game/puzzle/simulation rule tasks. Accept deterministic state transitions, move legality, scoring, or solver behavior. Reject visual-only or flaky/random tasks.

## Source Queue

Prioritize low-to-medium quota sources for upstream bugfix mode:

| Repo | Quota burn | Best task domains |
|---|---:|---|
| `pypa/pip` | low-medium | resolver behavior, wheel/cache handling, requirement parsing, install/report edge cases |
| `pypa/setuptools` | low-medium | editable installs, package discovery, metadata/config parsing, build hooks |
| `python/importlib_metadata` | low | entry points, metadata parsing, distribution discovery |
| `python/importlib_resources` | low | resource lookup, package files, namespace/package edge cases |
| `django/django` | medium | ORM/query generation, forms/validation, migrations, template rendering, management commands |
| `urllib3/urllib3` | medium | URL parsing, connection pools, retries, headers, redirects, timeout/proxy behavior with local servers |
| `encode/httpx` | medium | request/response behavior, transports, redirects, headers, timeouts with mock/local transports |
| `pytest-dev/pytest` | low but cooldown after Medium results | fixture lifecycle, collection, reporting, assertion rewriting |
| `pandas-dev/pandas` | medium-high, selective | indexing/groupby/merge/datetime/parser edge cases with tiny datasets |

Heavy repos are allowed only with explicit opt-in and strict limits:

- `numpy/numpy`
- `tokio-rs/tokio`
- `microsoft/TypeScript`
- `ethereum/go-ethereum`
- `pytorch/pytorch`
- `ray-project/ray`

For pandas, mine only localized bugs with small dataframes and no compiled-extension rebuild requirement.

For category-profile mode, use sources that naturally match the requested
category, including small CLI tools, example apps, data pipelines, build scripts,
admin config repos, numerical utilities, and terminal games. The Source Queue is
not a category-diversity limit.

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

For `pypa/setuptools`, prefer:

- editable install and package discovery behavior
- `pyproject.toml`, `setup.cfg`, and metadata parsing edge cases
- build hook behavior that can run with local temporary projects
- namespace package/resource edge cases without network

Avoid setuptools candidates requiring publishing, remote indexes, compiled extensions, or full downstream-package integration.

For `python/importlib_metadata` or `python/importlib_resources`, prefer:

- entry point parsing/selection behavior
- distribution metadata normalization and discovery
- resource lookup across packages, namespace packages, zip files, or missing files
- small public API regressions reproducible with temp packages

Avoid candidates that only update compatibility metadata or depend on a specific installed system package layout.

For `django/django`, prefer:

- ORM SQL/query behavior reproducible with SQLite
- form/model validation edge cases
- migration state rendering with a tiny project
- template or management-command behavior without external services

Avoid Django candidates needing PostgreSQL/MySQL-specific behavior unless SQLite can faithfully reproduce the bug.

For `urllib3/urllib3` or `encode/httpx`, prefer:

- URL parsing/canonicalization, headers, redirects, retries, pools, proxy configuration, or timeout handling
- reproductions using local loopback servers, in-memory transports, monkeypatched sockets, or deterministic fake connections
- public API/CLI behavior that needs no internet

Do not use network-library candidates that call live external URLs, depend on DNS/internet, need real proxies, require TLS cert infrastructure beyond local fixtures, or are flaky timing/concurrency issues.

For network-library candidates with alternate transports or platform-specific
implementations such as emscripten, the mined artifact must identify the actual
testable wrapper/API and constructor contract. Do not hand off a candidate that
only names an internal dataclass or raw container when the behavior lives on a
wrapper class.

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
- choose the category first when the user asks for category diversity
- verify the issue/PR is closed or merged for upstream bugfix mode
- identify the fixing commit and a parent commit before the fix for upstream bugfix mode
- identify a stable `base_commit` and observable target behavior for category-profile mode
- inspect only the source text, changed file list, focused diff hunks, docs/examples, and tests needed to evaluate the candidate
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

- `category + source + task_slug`
- `repo + issue_or_pr_id`
- `repo + fixing_commit`
- `repo + bug_signature`
- `repo + base_commit + target_behavior`

Reject or skip candidates already marked `cloned`, `submitted`, or `claimed` by another worker. If only the subsystem overlaps but the behavior differs, continue only when `bug_signature` is clearly distinct.

Append one compact JSON line per decision:

```json
{"category":"debugging","repo":"pytest-dev/pytest","issue_or_pr_id":"14465","source_url":"...","fixing_commit":"...","parent_commit":"...","bug_signature":"maxfail session fixture teardown reporting","task_slug":"tbrain-maxfail-teardown-reporting","status":"mined","rejection_reason":null}
```

Valid statuses: `mined`, `claimed`, `cloned`, `submitted`, `rejected`.

## Hardness Filter

For upstream bugfix mode, apply the repo-specific hard filters below.
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
- `<= 10` meaningful LOC in one obvious file unless prior agent trials show low pass rate
- one-condition fixes such as "if stop flag then do X" when all verifier cases exercise the same branch
- bugs whose verifier would need network, credentials, browser, database, or OS-specific services

For category-profile mode, reject candidates when:

- the target behavior can be solved by one obvious expression, option, or config line
- the verifier would only check one happy-path example
- the source repo/app is so small that there is no meaningful discovery work
- the prompt would need to reveal the exact implementation approach
- the category label is only cosmetic and the real work is debugging

## Candidate Scoring

Score each axis from 1 to 5:

- `subsystem_interaction`: needs multiple subsystems, data rules, build layers, or behavior surfaces, not one local branch
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
  category:
  subcategories:
  objective_type: upstream_bugfix | feature | data_pipeline | build | admin_config | security | scientific | ml | game
  source_url:
  issue_or_pr_id:
  repo:
  base_commit:
  parent_commit:
  fixing_commit:
  task_slug:
  bug_signature:
  touched_files:
  subsystem_tags:
  runtime_class:
  external_requirements:
  repro_summary:
  current_pipeline_summary:
  target_behavior:
  required_work:
  input_fixtures:
  output_contract:
  bad_behavior:
  expected_behavior:
  preserved_behavior:
  edge_cases:
  why_not_debugging:
  test_surface:
    primary_api:
    secondary_apis:
    constructor_contracts:
    offline_fixtures:
    skip_guard_policy:
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

For non-debugging category profiles, prefer `base_commit`, `target_behavior`, `required_work`, `input_fixtures`, and `output_contract` over bugfix-only fields. Leave bugfix-only fields empty instead of inventing a `fixing_commit`.

## Hardness Calibration

Treat platform difficulty as empirical, not just conceptual.

Downgrade or reject candidates when:

- the likely oracle is a tiny one-file patch
- all tests reduce to variants of the same condition
- a strong agent can locate the fix by grepping one or two obvious symbols from the prompt
- a previous difficulty check shows any frontier agent at `5/5` or aggregate pass rate `>= 80%`

For Python tasks, keep only candidates likely to make strong agents fail after understanding the prompt, not merely candidates that look complex by subsystem name.

## Clone Handoff

Pass only the mined artifact to `task-clone` when possible. The clone phase should not re-mine GitHub, rescan history, or re-read unrelated diffs unless the artifact is missing a required field.

The artifact must include enough verifier-facing API detail for clone to avoid
guessing. For each tested implementation, include:

- import path
- class/function that owns the behavior
- minimal valid constructor call
- whether the implementation is always present in the pinned repo
- any raw container or wrapper relationship

If this is unclear, mark the candidate incomplete and do not clone yet.

## Transformation Hints

1. Pin `environment/repo/` to a parent commit before the fix for upstream bugfixes, or to `base_commit` for category-profile tasks.
2. Remove upstream tests that reveal the exact patch if needed.
3. Write a prompt describing user-visible behavior only.
4. Put reproducer projects inside verifier tests, not in the prompt.
5. Verify the starting state fails the target behavior for the intended reason.
6. Write oracle as `solution/fix.patch` plus `solution/solve.sh`.
7. Test both the target behavior and normal behavior preservation.

## Bugfix Prompt Template

```md
Pytest in `/app` mishandles <observable scenario>. A user project that <setup> currently <bad behavior>.

Fix pytest so `python -m pytest <command shape>` <required behavior>. The run should <preserve important existing behavior>. Do not change the user project's tests.
```

Keep issue URLs and PR IDs out of `instruction.md`.

## Category Profile Prompt Template

```md
The tool in `/app` needs to produce <target artifact or behavior> from <input surface>. Implement support for <public command/API/workflow> so it follows <observable contract>.

The output must <format/schema/order/tolerance requirements>. Preserve <existing mode or compatibility behavior> for <normal workflow>.
```

Keep source URLs, commit hashes, upstream test names, verifier language, and
solution hints out of `instruction.md`.

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

## Borderline Candidate Warning

Fixture teardown under `--maxfail=1` with JUnit XML is now a borderline/retired pattern. It looks hard by subsystem names, but can collapse to a tiny `runtestprotocol` stop-flag patch and may be rated Medium if frontier agents pass reliably.

Use similar pytest reporting tasks only if the mined artifact shows a deeper architectural change than a one-branch teardown timing fix.
