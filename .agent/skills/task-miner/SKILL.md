---
name: task-miner
description: Use when mining Terminus Regular task candidates that fit the live task gallery (/portal/tasks) — self-contained, spec-driven problems aligned to the gallery's canonical 3-level taxonomy (10 categories: Software Engineering & Development, Data Processing & Scripting, Machine Learning & AI, Security & Cryptography, System Setup & Configuration, Build & Dependency Management, Debugging & Troubleshooting, Scientific Computing & Analysis, Interactive Challenges & Games, Large Codebase Tasks; each with subcategory → subsubcategory) plus the 5 cross-cutting subtypes (long_context, tool_specific, api_integration, db_interaction, ui_building). Targets the gallery's difficulty mix: Hard or Medium model pass rate (Easy is blocked; Python tasks must be Hard). This metadata-only skill scores candidates, checks novelty against the existing gallery, and records source/base commits, behavior contracts, category/subcategory/subsubcategory + subtype fit, verifier shape, runtime risk, dedupe keys, and rejection reasons, but does not scaffold tasks, write verifiers, or patch code. The full taxonomy menu lives in mined-candidates/gallery_taxonomy.md. The debugging and software-engineering categories are currently ON HOLD (pending on the platform) — skip them and mine the other 7. Default to gallery-style spec-driven mining; use upstream bugfix PRs only as a minority lane or when the user asks.
---

# Task Miner

Use this skill when sourcing task ideas for the Terminus task gallery
(`/portal/tasks`). The gallery IS the target distribution — mine candidates that
look like they belong in it and that do NOT already exist there.

- **No direction given → default to Gallery-style mining** (Category Profile Mode
  below): self-contained, spec-driven "implement a tool/engine/pipeline/algorithm
  end-to-end" tasks (Lane A), spread across UNDER-represented ALLOWED categories
  (see the Category Hold callout below). Do NOT default to upstream bugfix PRs —
  those are a minority of the gallery.
- **User names a category** → use the matching Category Profile (reject if it is on hold).
- **User names a subtype** → use the matching Subtype Profile.
- **User asks for a bugfix / closed PR** → use Upstream Bugfix Mode (minority lane) —
  but it produces the `debugging` category, which is currently ON HOLD (see callout
  below); only proceed if the user explicitly overrides the hold.

This is a lightweight mining pass. Do not create a task folder, Dockerfile,
verifier, or oracle here. The output is a compact mined candidate artifact consumed
later by `task-clone`.

> **⛔ CATEGORY HOLD (active — set 2026-06-21).** `debugging` and `software-engineering`
> are PENDING on the platform and are NOT being accepted right now. Do NOT mine or
> propose candidates in these two categories, and do NOT default to Upstream Bugfix Mode
> (it produces `debugging`). **Allowed categories (7):** `system-administration`,
> `build-and-dependency-management`, `data-processing`, `games`, `machine-learning`,
> `security`, `scientific-computing`. If a candidate naturally lands in a held category,
> either reframe it into an allowed category ONLY when the primary work genuinely fits
> there, or reject with `rejection_reason: category_on_hold`. This is a TEMPORARY hold —
> re-enable by editing this one callout (and the mirrored note in `task-clone`) when the
> platform reopens these categories.

## Task Gallery Alignment (mine toward the live benchmark)

The gallery is the live benchmark corpus (snapshot + dedupe list:
`mined-candidates/gallery_tasks_snapshot.md`, 543 tasks as of 2026-06-21). Match its
SHAPE, distribution, and difficulty, and never duplicate an existing task.

**Canonical taxonomy (align every candidate to this).** The gallery organizes tasks
on TWO orthogonal axes; the full menu — 10 categories → subcategory → subsubcategory,
the 5 subtypes, and the language mix, read live from the portal's Supabase backend on
2026-06-21 — is in `mined-candidates/gallery_taxonomy.md`. Read it before mining.

- **Axis 1 — 3-level category taxonomy** (`category` → `subcategory` →
  `subsubcategory`). 10 canonical categories (skill kebab alias in parens):
  Software Engineering & Development (`software-engineering`), Data Processing &
  Scripting (`data-processing`), Machine Learning & AI (`machine-learning`), Security
  & Cryptography (`security`), System Setup & Configuration (`system-administration`),
  Build & Dependency Management (`build-and-dependency-management`), Debugging &
  Troubleshooting (`debugging`), Scientific Computing & Analysis
  (`scientific-computing`), Interactive Challenges & Games (`games`), and **Large
  Codebase Tasks** (milestone-heavy large multi-layer repos — the milestone lane, NOT
  one of the 9 kebab categories). Pick ONE category, then the nearest
  subcategory/subsubcategory leaf; prefer near-empty leaves (`[1]` in the reference)
  for novelty.
- **Axis 2 — 5 cross-cutting subtypes** (`long_context`, `tool_specific`,
  `api_integration`, `db_interaction`, `ui_building`). The gallery's
  `task_inspiration_v2.subtypes`, orthogonal to the category; a task has zero or more.
  SQL being the #2 language in the pool reflects the `db_interaction` weight. See
  Subtype Profiles.

Gallery difficulty is an `easy|medium|hard` field but is currently unpopulated
(all-null in the data), so keep gating hardness by MODEL PASS RATE (below), not the
gallery field.

**Keep the taxonomy fresh (the gallery changes continuously).** `gallery_taxonomy.md`
is regenerated by `.agent/skills/task-miner/refresh_gallery_taxonomy.py`, which re-discovers
the portal's live Supabase backend on each run (so it survives bundle-hash and anon-key
rotation) and rewrites the file stamped with today's date. At the START of any mining
batch, read the `Snapshot date:` line in `gallery_taxonomy.md`; if it is missing or
older than ~7 days, refresh first:

```bash
python3 .agent/skills/task-miner/refresh_gallery_taxonomy.py
```

Then mine against the refreshed menu. Re-run it any time the category counts look stale
or a candidate straddles a category boundary. For hands-off tracking, put this script on
a schedule (e.g. weekly) so the local taxonomy never drifts from the live gallery.

**Dominant shape — Lane A, self-contained spec-driven tasks.** The gallery is mostly
"build/implement a thing to a precise spec, end-to-end" — e.g.
`airport-gate-scheduler`, `json-3way-merge-engine`,
`yaml-job-scheduler-with-deadlock-detection`, `ssa-dead-code-eliminator`,
`mini-sqs-server`, `multi-format-etl-pipeline`, `ml-explainability-cli`,
`merkle-tree-collision`. Each is one problem, deterministic, offline, with a
human-style instruction and a pytest verifier that shells out to the produced
artifact. Bugfix-PR clones are the MINORITY — prefer Lane A unless the user asks.

**Real distribution to mirror (sampled 2026-06-21):**
- Category: software-engineering ~40%, data-processing ~20%, machine-learning ~11%,
  security ~9%, system-administration ~7%, debugging ~5%, scientific-computing ~4%,
  games ~4%, build-and-dependency-management present. NOTE: those percentages are from
  a 55-task sample. The FULL Supabase corpus (see `gallery_taxonomy.md`) is far more
  BALANCED — every category sits ~390–600 curated rows (Security 600, Debugging 592,
  Scientific 589, Games 520, ML 516, Software-Eng 499, Data-Processing 417, System
  Setup 396, Build 392). So treat all 9 as first-class; the diversity rule (no single
  category >~30%, ≥4 categories ≥10%) still holds — don't pile onto software-engineering.
- Difficulty: hard ~53%, medium ~38%, easy ~4%. Mine Hard-or-Medium ONLY.

**Archetype catalog (mine toward these; counts = gallery prevalence across 543):**
log/ETL/data-processing pipelines (88) · API/web/DB services (50) · build/deps
toolchains (39) · sysadmin/ops automation (35) · crypto/security (34) ·
compiler/language/parsing engines (31) · ML/AI CLIs & loaders (30) · algorithmic
solvers/schedulers (29) · games/puzzles/simulations (24) · scientific/numeric (14).

**Difficulty band (model pass rate, NOT the `task.toml` field) — platform rule:**
- Hard — accuracy ≤20% on the **best** OR **worst** model. Python MUST be Hard.
- Medium — 20% < accuracy ≤60% on the **worst** model. ACCEPTABLE for non-Python;
  tag `target_difficulty: medium`, do not discard.
- Easy — 60–80% on worst model → BLOCKED. >80% → auto-rejected. NEVER mine toward Easy.

**Subtypes (the `subcategories` enum) — optional, orthogonal to the one category:**
`long_context` (≥50k-token doc, semantic-not-greppable), `tool_specific`
(Blender/FFmpeg/ImageMagick/Graphviz/MLFlow/… offline), `api_integration` (API source
in-env, mocked in Docker, terminal-only, avoid FastAPI), `db_interaction` (real
engine, not flat-file CSV), `ui_building` (pytest + Playwright **Python** bindings).
Add a subtype only if it genuinely fits; otherwise leave `[]`. See Subtype Profiles.

**Novelty gate (gallery-specific, MANDATORY):** before accepting a candidate, check
its name/archetype+domain against `mined-candidates/gallery_tasks_snapshot.md`. If the
gallery already has the same problem (e.g. another CSV-merger, another gate-scheduler),
REJECT as duplicate unless the candidate adds a clearly distinct twist. Record the
closest existing gallery task in the artifact (`closest_gallery_task`).

**Operational invariants (unchanged):** offline (`allow_internet=false`), 2 CPU / 4 GB,
build ≤600s, verifier ≤450s (always Python pytest shelling out to the task's
executable/API/DB/file outputs), agent default 900s (cap 1800), `environment/` ≤100
MiB. Codebase size minimal/small/large all accepted — aim for a mix.

## Operating Modes

### Upstream Bugfix Mode (minority lane)

> **ON HOLD (2026-06-21):** this mode produces the `debugging` category, which is
> currently pending — do NOT run it by default. Only use it when the user explicitly
> overrides the Category Hold, and even then prefer reframing into an allowed category.

Use ONLY when the user asks for a bugfix, or for the small bugfix/debug slice of the
gallery (`debugging` is ~5% of the corpus). For closed upstream issues/PRs where the
task is to diagnose and fix bad behavior. These candidates normally become:

```yaml
category: debugging
subcategories: []   # add a subtype ONLY if one genuinely applies (see Subtype Profiles)
```

`subcategories` is OPTIONAL and orthogonal to `category` — leave it `[]` unless a
subtype truly fits; do not auto-stamp `tool_specific`. This mode needs
`fixing_commit`, `parent_commit`, `bad_behavior`, `expected_behavior`, and upstream
regression-test context. Prefer Gallery-style Lane A (Category Profile Mode) by
default.

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

**`debugging` and `software-engineering` are currently ON HOLD — do not choose them**
(see the Category Hold callout above); mine the other 7. These kebab labels map 1:1 to
the gallery's canonical category names (see the table in
`mined-candidates/gallery_taxonomy.md`). The gallery also has a 10th category, **Large
Codebase Tasks** (milestone-heavy multi-layer repos) — mine it only when the user asks
for the milestone / large-codebase lane; standard Regular tasks use the 9 above. After
choosing a category, also record the gallery `subcategory` and `subsubcategory` the
candidate maps to (pick the nearest leaf from the taxonomy reference).

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

## Subtype Profiles

The 5 subtypes are the gallery's **cross-cutting axis** (`task_inspiration_v2.subtypes`)
— distinct from the 3-level `subcategory`/`subsubcategory` taxonomy, do not confuse the
two. They target areas where frontier agents underperform. OPTIONAL and orthogonal to
`category`: a task has one category and zero-or-more subtypes. Do not shoehorn a subtype
that does not fit.

- `long_context`: ONE large document (**≥50k tokens**) the agent must understand
  SEMANTICALLY — the answer must NOT be reachable by `grep`, keyword search, or pure
  programmatic parse. Formats: PDF (papers, 10-K, ISO standards), DOCX, MD/TXT
  (transcripts, handbooks), HTML (a docs site flattened), JSON/YAML (huge schemas),
  CSV (metadata-heavy), chat logs, long email threads. Accept when the answer needs
  cross-referencing/synthesis and is deterministic offline. Reject greppable single
  strings, docs <50k tokens, or docs needing network. Honor the portal **Long Context
  Task Checklist**. Artifact: `document_source`, `approx_tokens` (≥50k), `format`,
  `why_not_greppable`.
- `tool_specific`: Real workflows for tools with SDKs/APIs where models underperform —
  Blender, FFmpeg, ImageMagick, Graphviz, MLFlow, WandB, Prefect, Superset, GIMP,
  QGIS, etc. Accept when the tool installs/runs OFFLINE in Docker (no
  GPU/display/license/network) and produces a deterministic inspectable artifact via a
  non-trivial multi-step workflow. Reject single-command usage or live services.
  Artifact: `tool` + offline install plan.
- `api_integration`: Build/interact/debug an API whose **source code is in the
  environment** and **fully mocked in Docker (no external deps)**; the agent uses the
  terminal only (curl/CLI — NO MCP). Frameworks: Flask, Rails, Rustapi, Spring Boot,
  Django, Express, Fastify, Play, Gin, etc. **Avoid FastAPI** (oversaturated) unless
  the user insists, and record why. Accept multi-endpoint/multi-step, deterministic,
  offline. Reject live external APIs or a single trivial endpoint. Artifact:
  `api_framework`, `mock_plan`, `endpoints`.
- `db_interaction`: Solved by INTERACTING with a database engine (SQL, NoSQL, vector,
  in-memory) — the agent must query the engine, not read the data directly. Accept a
  real engine running offline in Docker. Reject when the "DB" is just a CSV the agent
  reads directly (flat-file/CSV-as-DB must stay a MINORITY) or needs a hosted/cloud DB.
  Artifact: `db_engine`, `why_engine_not_flatfile`.
- `ui_building`: Create/edit/update a UI. **Verification MUST be Python pytest**; for
  browser automation use **Playwright's Python bindings** from pytest — never a JS/TS
  suite. Use the UI Task Skeleton downstream. Accept deterministic, checkable UI
  behavior offline. Reject purely visual/subjective goals. Artifact: `ui_stack`,
  `playwright_python_plan`.

## Selection axis — archetype × build-viability, NOT language

Pick by ARCHETYPE first; language is free. Only the verifier must be Python
pytest, and it merely shells out to the task's executable / API / file outputs —
so the codebase the agent works in (`languages` in task.toml) can be ANY
language. Docs treat "niche tools/languages" as a Hard lever (less training data
→ frontier agents fail more), so a non-Python codebase often HELPS difficulty.

The real gate is operational viability, not language: build <=600s after
slimming, verifier <=450s, offline (`allow_internet=false`), deterministic,
2 CPU / 4 GB, `environment/` <=100 MiB. Language matters only INDIRECTLY through
build cost.

Hard-dense archetypes (language-agnostic) — mine TOWARD these:

| Language | Hard archetypes | Build/viability |
|---|---|---|
| Go | scheduler/reconciler, SQL planner, protocol state machine, EVM/consensus (scoped) | fast static build ✅ — AVOID one-guard parser/crypto libs |
| Rust | async cancellation, trait resolution, borrow/lifetime, codegen | slow but cacheable; pick small crates |
| TypeScript/JS | TS compiler inference/narrowing, type-level libs | TS compiler heavy but offline |
| C/C++ | optimizer pass, UB/codegen, numerical algorithm | small make/cmake builds fast; watch toolchain |
| Java/Kotlin/C# | Roslyn/javac analyzer, query engine, bytecode | JVM/.NET build heavier (use offline mode) |
| Haskell/OCaml/Scala | type inference, parser-combinator engine, evaluator | NICHE BONUS for Hard; build can be heavy |
| Lua/PHP/Perl/Elixir/Erlang/R/Fortran/Lisp/Prolog | interpreter/engine quirks, version-ordering & canonicalization tails, numeric kernels | apt-installable on the canonical Debian/Ubuntu base (Fortran: gcc image) — fast offline install, NICHE BONUS, widens the dedupe cell; vet the language's OWN stdlib for in-env reference impls (Ruby `URI`, PHP `parse_url` count like `tomllib`) and confirm agents still write it competently |
| Python | mypy, Django ORM compile, scientific, multi-layer interpreter | fastest build — convenient, NOT mandatory |

3-step selection rule (replaces "prefer Python"):

1. Choose a hard archetype (compiler / planner / state-machine / numerical /
   multi-layer interpreter), regardless of language.
2. Confirm that scope builds offline within 600s after slimming. If yes, accept
   — any language.
3. Tie-break between equally-hard candidates by preferring the NICHE language
   (Haskell/OCaml/Rust earn the Hard bonus) and the lighter build.

Deliberately MIX languages across a batch to avoid the "17 tasks all Go libs"
failure (June 2026 batch B). A healthy batch spans e.g. Rust + Go + TS + C/C++ +
a niche language, not one library family.

## Source Queue

The repos below are the OPERATIONALLY-EASY Python lane (fast offline builds) —
convenient, but NOT the default or the only lane. Do not let this list pull
every batch back to Python parser/validator libs. Apply the archetype-first
selection rule above and the patch-shape gate before using any of them.

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
- bug is localizable after slimming but still spans 5-6 meaningful components,
  behavior surfaces, or project layers
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

## Sample Source Selection

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
- inspect more than 15 files unless the candidate is already high value and needs one extra confirmation
- inspect more than 3 commits around the fix
- enumerate unrelated test suites or full repository trees

Stop mining when a deterministic reproducer, localized touched files, and sufficient candidate score are found.

## Dedupe Registry

Before mining deeply, check these:

```text
mined-candidates/index.jsonl               # candidates already mined/claimed/cloned by the team (incl. the spec-conformance resource-claim lane)
mined-candidates/gallery_tasks_snapshot.md # task NAMES already IN the live gallery — do not duplicate
mined-candidates/gallery_taxonomy.md       # the category/subcategory/subsubcategory + subtype menu to align to
.agent/skills/task-miner/lever_patterns.md # SHARED, resource-agnostic pattern specs + claimed-resource ledger — the in-repo home of "learn the pattern, not the resource" (replaces relying on any personal memory)
```

The gallery snapshot is the **novelty gate**: if the gallery already contains the
same problem/archetype+domain as your candidate, REJECT as a duplicate unless the
candidate adds a clearly distinct twist, and record `closest_gallery_task`. Refresh
the snapshot from a public fork of `snorkel-tb-tasks` when it is stale (see the file
header). If the team has a shared registry path or URL, check that too before
claiming a candidate.

Registry identity keys:

- `category + source + task_slug`
- `repo + issue_or_pr_id`
- `repo + fixing_commit`
- `repo + bug_signature`
- `repo + base_commit + target_behavior`
- `conformance_suite + spec + language` **(spec-conformance lane — MANDATORY).
  The keys above do NOT catch conformance-suite collisions: the task slugs
  differ and there is no repo/issue, so two teammates independently pick the
  same official suite and only discover the clash after both are built. Claim
  the suite+spec HERE before building. Cell-dedup on
  `gallery_category × language × lever` requires a NOVEL resource within the
  cell — a different suite than the ones the lever catalog names, not just a
  different slug.**

Reject or skip candidates already marked `cloned`, `submitted`, or `claimed` by another worker. If only the subsystem overlaps but the behavior differs, continue only when `bug_signature` is clearly distinct.

Append one compact JSON line per decision:

```json
{"category":"debugging","repo":"pytest-dev/pytest","issue_or_pr_id":"14465","source_url":"...","fixing_commit":"...","parent_commit":"...","bug_signature":"maxfail session fixture teardown reporting","task_slug":"tbrain-maxfail-teardown-reporting","status":"mined","rejection_reason":null}
```

Valid statuses: `mined`, `claimed`, `cloned`, `submitted`, `rejected`.

**Family ledger (difficulty memory at the family level, not just exact dedupe).**
Exact-candidate dedupe does not stop the team from re-mining the same SHAPE of
bug in a different function. Maintain a `family_difficulty` ledger keyed by
`library + bug_family` (e.g. `golang-crypto-ssh + validation-bound-check`,
`go-yaml + parser-edge-condition`). Record the max platform rating observed for
that family. If a family's ceiling is `<=EASY` (or `<=MEDIUM` after >=2 samples),
skip new candidates in it unless a frontier-agent probe failed semantically.
Append difficulty outcomes back into this ledger after platform rating so the
miner stops feeding known-collapsed families.

## Hardness Filter

For upstream bugfix mode, apply the repo-specific hard filters below.
A good Hard candidate should require the agent to understand 5-6 meaningful
components, behavior surfaces, or project layers. Components can be source
modules, public APIs, CLI/config parsing, build/dependency metadata, data/schema
rules, cache/state management, error handling, compatibility paths, or test
fixtures. Do not count trivial call-stack frames or files that are merely
adjacent.

Examples of component-rich candidates:

- fixture finalization plus JUnit XML reporting
- collection tree plus import/path mode
- assertion rewriting plus traceback formatting
- package discovery plus editable install metadata plus legacy fallback
- requirement parsing plus marker evaluation plus wheel/cache selection
- ORM query compilation plus model validation plus migration state rendering
- HTTP redirect/retry handling plus header preservation plus transport state
- warning capture plus terminal reporting
- hook ordering plus test outcome propagation

Reject candidates solvable by only matching the issue title or changing one expected string.

Reject false-hard candidates:

- docs-only, typo-only, dependency bump, CI-only, release metadata, or typing-only
- message-only changes unless the bug is specifically user-facing diagnostic correctness
- single validation branch fixes
- `<= 10` meaningful LOC in one obvious file unless prior agent trials show low pass rate
- one-condition fixes such as "if stop flag then do X" when all verifier cases exercise the same branch
- candidates with fewer than 4 meaningful components unless prior frontier-agent
  trials show repeated failures for semantic reasons
- bugs whose verifier would need network, credentials, browser, database, or OS-specific services

### Mechanical patch-shape gate — RUN FIRST, pass/fail, before any scoring

The fix-shape filter below is correct but kept getting ignored: 17 candidates
shipped and 14 rated <=EASY (June 2026 batch B). So gate it MECHANICALLY. Open
the fixing diff and answer these. A candidate is Hard-eligible ONLY if at least
ONE is true:

- the diff ADDS >=1 new exported symbol (type, interface, func, method, or
  struct field) that call sites must be rewired to use;
- the diff changes >=2 NON-TEST source files whose logic INTERACTS (not the same
  guard copied to a second path — that is the mirror anti-pattern, still fails);
- the upstream fix landed as >=2 iterated commits where maintainers reworked the
  design (link them);
- a frontier-agent probe has already FAILED this candidate for a semantic reason
  (record it).

If NONE hold — i.e. the entire fix is "+1..~20 lines inside ONE existing
function / one obvious spot" — REJECT for Hard with no exception for CVE status,
security/crypto domain, severity, or impressive component names. Record
`patch_shape_gate: fail`. This is the single most important gate in this skill.

### Empirical override (2026-06 non-Python batch, 9 agent-RATED tasks): the count-based gate above is NECESSARY, NOT SUFFICIENT

Platform agent-trial ratings refuted file-count / LOC / "adds a new exported
symbol" as Hard predictors:

| Rated | task | files | LOC | decisive factor |
|---|---|---:|---:|---|
| HARD | caffeine cache-eviction scan | 1 | 38 | design a non-obvious traverse-and-requeue invariant |
| HARD | elixir set-theoretic types | 1 | 155 | design static/dynamic projection invariant |
| HARD | valkey hashtable resize-policy | 5 | 67 | re-derive ALLOW/AVOID/FORBID policy state machine |
| HARD | go-mysql-server optimizer FDS | 2 | 132 | invent a conditional-equivalence concept |
| MEDIUM | hashicorp/raft commit-index | 5 | 200 | new interface+flag BUT the prompt must NAME the API |
| MEDIUM | h2 push-promise waker | 5 | 40 | mechanical-once-diagnosed (add a waker + notify) |
| EASY | vue reactivity flag-dedup | 1 | 26 | known idiom; the "5 functions" are all in one file |
| EASY | nats scale-down unify | 1 | 75 | spec'd-signature transcription |
| TRIVIAL | jq codec rewrite | 1 | 118 | accumulate-then-validate, mechanical |

raft hit EVERY mechanical condition (new interface, 6 files, 38 commits) yet
rated MEDIUM; caffeine hit NONE (1 file, 38 LOC) yet rated HARD. So once the
mechanical gate passes, apply the TWO REAL predictors — BOTH must hold for Hard:

1. **DESIGN-not-transcribe.** The fix must require reasoning out a NON-OBVIOUS
   invariant / algorithm / policy. REJECT to MEDIUM/EASY if, once the symptom is
   diagnosed, the fix is MECHANICAL: add a waker/field/guard at known points
   (h2 push-promise → MEDIUM), a known idiom (flag-dedup = vue → EASY;
   accumulate-then-validate codec = jq → TRIVIAL), or mirror an existing path.
   "Adds a new exported symbol" does NOT save it — raft added a whole interface
   and still rated MEDIUM.
2. **BEHAVIORAL-verifiability (the cap that bit raft + nats).** The fix must be
   verifiable through OBSERVABLE PUBLIC behavior (CLI/API output, a metric, an
   `EXPLAIN` plan, rendered state) so `instruction.md` can describe ONLY the
   symptom and the agent must DISCOVER + DESIGN the fix. If the fix logic is
   UNEXPORTED and the only fair verifier is a white-box test that must CALL a
   named new symbol, the prompt is forced to NAME it → the agent transcribes the
   spec → MEDIUM ceiling. Pre-mine question: "can a verifier prove this fix purely
   through public/observable behavior, WITHOUT the prompt naming any new symbol?"
   If no → MEDIUM at best; re-mine.

**Bonus HARD signal — secondary-observable bug:** prefer bugs that surface in a
SECONDARY observable (cost / plan / cardinality / metric / memory / eviction
timing / internal state), NOT a wrong primary output — the agent then cannot
pattern-match a wrong result and must reason about the engine (go-mysql-server:
query RESULTS stay correct, only the plan/row-estimate is wrong → HARD).

**Archetype weighting from this batch:** ENGINES with algorithm/policy/invariant
state — query optimizers, type systems, cache eviction, data-structure
resize/rebalance, numerical kernels — rated HARD. Codec / parser / scheduler-flag
/ protocol-waker / membership-unify rated TRIVIAL→MEDIUM. Weight engine
archetypes UP; treat the latter as MEDIUM-at-best absent an agent-probe failure.

**Operational-ease inversion (why the other scores mislead):** high
`offline_viability` / `deterministic_reproducibility` / low `runtime_cost`
correlate NEGATIVELY with difficulty here. Parser, validator, crypto-blob, and
numeric-precision bugs score perfectly on those axes PRECISELY because they are
localized one-spot fixes. A candidate that is "clean and easy to test" is a
yellow flag for Hard, not a green one. Never let operational tidiness raise the
hardness score.

### Collapsed families — do NOT re-mine (each empirically rated <=EASY/MEDIUM)

These bug families have a fixed low ceiling regardless of library. Skip new
candidates in them unless a recorded frontier-agent probe failed semantically:

- input validation / bound / range / size / FIPS checks (ssh RSA-modulus,
  bcrypt-rounds, RSA-privatekey, DSA-param)
- malformed-blob / type-mismatch / marker / revoked rejection in key parsing
  (knownhosts-*, ssh key parse, ecdsa curve confusion)
- single-condition parser edge-cases in compose/parse (go-yaml sibling-anchor
  scope, tag-node container, empty-seq sibling; JSON/struct decode edges)
- cycle / nil / recursion guards (goja circular ToPrimitive)
- precision / rounding / scale tweaks in one numeric routine (decimal Pow)
- regex anchoring / partial-match fixes (grpc RBAC regex-partial — still only MEDIUM)
- single-table / histogram construction in one func (huff0 ctable)
- reflection field-access traversal (expr interface field — only MEDIUM)

Low-yield-for-Hard SOURCES (treat single-bugfix PRs here as default-reject for
Hard): golang/crypto ssh + knownhosts, go-yaml/yaml, dop251/goja,
shopspring/decimal, klauspost/compress (huff0/zstd), expr-lang/expr, and similar
parser/validator/crypto/numeric libraries. Their bugfix PRs are almost always
one-spot patches. The earlier note calling golang/crypto ssh "a rich, fast-
building source" is RETRACTED for Hard mining — it is rich in TRIVIAL.

### Fix-shape filter — the #1 cause of EASY/TRIVIAL ratings (empirical, June 2026)

Difficulty is set by the reasoning needed to PRODUCE THE FIX, NOT by the bug's
severity, CVE status, security domain, file count, or impressive subsystem
names. A security-critical, CVE-grade, multi-file bug still rates TRIVIAL/EASY
if the fix is a small obvious guard. The "5-6 components" heuristic does NOT
save such candidates — they look component-rich but the patch lives in one
obvious spot.

REJECT a candidate (for Hard) when the likely fix is any of:

- a single bound / size / range check (`if N.BitLen() > 8192 { reject }`,
  `if rounds > 2048 { reject }`, `Q must be 160 bits`)
- a missing validation that is an obvious idiom (compare a declared type vs the
  actual decoded type and reject mismatch; reject a malformed/duplicate marker;
  anchor a regex)
- MIRRORING an existing check onto another code path (the bug is "path B lacks
  the guard that path A already has"; the agent copies A's logic to B)
- adding a nil-guard, an early return, or a missing error return
- anything a strong agent produces just by reading the observable symptom and
  adding ~1-15 lines in the one function the symptom points to

This holds even if the candidate is a published CVE, touches auth/crypto, or
spans several files. Empirical confirmations (all rated TRIVIAL on platform
despite "hard" metadata): ssh RSA-modulus DoS (one `BitLen()>8192` check), ssh
knownhosts key-type mismatch (compare declared vs actual type), knownhosts
multiple-marker rejection (reject host starting with `@`), DSA param validation
(three FIPS bound checks in one func), and even ssh source-address bypass
(CVE-2026-46595 — fix just mirrors the existing source-address check onto the
VerifiedPublicKeyCallback path). knownhosts revoked-CA (also check the signing
CA key against the revoked set) rated EASY.

KEEP for Hard only when the fix requires at least one of: designing a new
abstraction (new type/interface/struct field, multi-method refactor with new
signatures); a non-obvious algorithm or state-machine change; reconciling a
genuine cross-component contradiction the agent must reason through and CANNOT
copy from an existing site; or prior frontier-agent trials that fail for
semantic (not tooling) reasons. Prefer bugs where naming the observable symptom
does NOT hand the agent the patch location and shape.

### Mine TOWARD these Hard fix-signatures (positive selection)

Don't just filter out easy bugs — actively seek bugs whose fix has one of these
shapes. Empirically-confirmed HARD (June 2026 batches):

- **New abstraction / type-design fix:** the fix adds a new type, interface,
  struct field, or method signature and rewires call sites. E.g. go-ethereum
  mux-tracer "V2 hooks" (expose `OnNonceChangeV2`/`OnCodeChangeV2` on the Hooks
  struct + propagate). The agent must design the surface, not add a guard.
- **New-architecture fix:** the bug is fixed by restructuring control flow, not
  inserting a check. E.g. basicauth timing-leak (introduce verifier ranking +
  a dummy-verify path + constant-time comparison). No single "add if" works.
- **Spec-correctness across multiple contexts:** the fix must satisfy an RFC /
  protocol in several places with different encodings, where a naive single fix
  breaks another context. E.g. JOSE `b64` critical header across JWS + JWE;
  RFC 6265 cookie domain/host-only semantics.
- **Branch-heavy logic with preservation constraints:** the fix changes
  behavior across many interacting branches and must NOT regress neighbours
  (path-traversal confinement across middleware + io/fs + path rewrite).
- **Algorithm / numerical / state-machine change:** log-sum-exp rewrite,
  deflation trigger, SIMD pivot ordering, CRT/precompute logic, parser
  state-machine reshaping.

Source patterns that tend to yield these: large feature/refactor PRs (not
one-line bugfixes); PRs that ALSO change several non-test files and add new
exported symbols; bugs whose upstream fix touches a core algorithm or a
protocol state machine; issues where maintainers debated the design. AVOID PRs
whose diff is a few added `if` lines in one function, however serious the bug.
When mining a security CVE, check the fix-shape FIRST: many CVEs are one-guard
fixes (TRIVIAL) — only keep the ones whose patch redesigns logic.

NOTE on the "5-6 components" heuristic used elsewhere in this skill: component
count is NECESSARY-NOT-SUFFICIENT. A bug can touch many components yet have a
one-spot fix (rates TRIVIAL). Always apply the fix-shape probe on top of the
component count; the fix-shape is the real difficulty test.

For category-profile mode, reject candidates when:

- the target behavior can be solved by one obvious expression, option, or config line
- the verifier would only check one happy-path example
- the source repo/app is so small that there is no meaningful discovery work
- the prompt would need to reveal the exact implementation approach
- the category label is only cosmetic and the real work is debugging
- the task does not naturally involve at least 4 meaningful components,
  behavior surfaces, or project layers; prefer 5-6 when available

## Candidate Scoring

Score each axis from 1 to 5:

- `subsystem_interaction`: 5 means 5-6 meaningful components/surfaces/layers
  must be coordinated; 4 means four components and is borderline; 3 or lower is
  too shallow for new Hard mining unless empirical agent failures justify it
- `deterministic_reproducibility`: reproduces offline with stable inputs
- `offline_viability`: no external service or missing plugin dependency
- `anti_shortcut_hardness`: hard to satisfy with a narrow hardcode
- `verifier_complexity`: can be tested behaviorally with 4-6 focused tests
- `runtime_cost`: 5 is lightweight, 1 is too heavy
- `leakage_risk`: 5 is low leakage, 1 exposes exact patch/test names

Reject if:

- `subsystem_interaction < 4` unless prior real-agent evidence shows the task is
  still hard for semantic reasons
- `deterministic_reproducibility < 4`
- `anti_shortcut_hardness < 3`
- `offline_viability < 4`
- the agent's edit→build→test cycle cannot be made fast. If testing a change
  requires a long cold rebuild that cannot be warmed to an incremental per-edit
  rebuild (Dockerfile pre-build + retained cache), the task trips the **Agent
  Timeout Gate** (`> ~5/10` agents time out) no matter how interesting the bug
  is. Prefer bugs in repos with incremental builds and small focused tests; a
  slow cold build is not difficulty, it is a blocker.

Runtime classes:

- `lightweight`: small Python-only reproducer
- `moderate`: imports a real package subset or writes temporary projects
- `heavy`: large install/build or broad suite needed
- `infra-heavy`: database, browser, GPU, network, or OS service; avoid for mass generation

## Output Artifact

Write or return this schema. Keep it compact; raw diffs stay out unless needed.

```yaml
candidate:
  category:                # skill kebab category (one of the 9; or the Large Codebase lane)
  gallery_category:        # canonical gallery category name, Title Case — see gallery_taxonomy.md
  subcategory:             # nearest gallery subcategory leaf (from gallery_taxonomy.md)
  subsubcategory:          # nearest gallery subsubcategory leaf (from gallery_taxonomy.md)
  subcategories:           # the 5 cross-cutting subtypes: zero or more of long_context, tool_specific, api_integration, db_interaction, ui_building
  target_difficulty:       # hard | medium  (never easy; Python => must be hard)
  expected_codebase_size:  # minimal (~0-20 files) | small (~20+) | large (~200+)
  closest_gallery_task:    # nearest existing gallery task name (from gallery_tasks_snapshot.md)
  gallery_novelty:         # novel | twist-on-existing | duplicate  (duplicate => reject)
  objective_type: spec_implementation | data_pipeline | tool_workflow | api_service | db_interaction | ui_build | upstream_bugfix | feature | build | admin_config | security | scientific | ml | game
  subtype_profile:         # fill ONLY the block(s) matching subcategories above
    long_context: { document_source:, approx_tokens:, format:, why_not_greppable: }
    tool_specific: { tool:, offline_install_plan: }
    api_integration: { api_framework:, mock_plan:, endpoints: }
    db_interaction: { db_engine:, why_engine_not_flatfile: }
    ui_building: { ui_stack:, playwright_python_plan: }
  source_url:
  issue_or_pr_id:
  repo:
  base_commit:
  parent_commit:
  fixing_commit:
  task_slug:
  bug_signature:
  touched_files:
  component_count:
  component_map:
    - name:
      role:
      evidence:
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
  difficulty_rationale:
  reasoning_bottlenecks:
  tempting_partial_fixes:
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
  patch_shape_gate:        # pass | fail — from the mechanical gate; fail => not Hard-eligible
  patch_shape_evidence:    # which gate condition passed (new symbol / >=2 interacting files / multi-commit / probe-fail)
  family_key:              # library + bug_family, checked against the family ledger
  agent_probe:             # {ran: bool, passed_oneshot: bool} — required if claiming Hard
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

## Opus-4.8 resistance — what actually makes a from-scratch SPEC task hard (2026-06-21, hard-won)

When the local probe model is Opus 4.8, mining clean "implement standard X" spec
tasks is a **~1/5 lottery** (one session: 7 built, 2 MEDIUM, 5×3/3). Internalize
this before mining a batch of spec-implementation tasks and DO NOT promise the
user N hard tasks from a pipeline:

- **A well-specified standard is NOT hard.** Opus knows standard algorithms/specs
  cold and differential-tests its output against any reachable reference, so
  withholding the formula, using a niche language, or omitting the reference
  library from the image does NOT help. Confirmed 3/3: push/move-optimal Sokoban,
  GNU `chmod` symbolic modes, NumPy quantile methods, RFC 5952 IPv6, DST gap/fold.
- **Reference-reachability kills it.** If the ground truth is a tool baked in
  every image (`chmod`, `git`) or a host stdlib (`ipaddress`, `csv`, `datetime`,
  `numpy`), the solver differential-tests exhaustively → 3/3. Pick behaviors whose
  reference is not trivially reachable, OR rely on a blind spot (below).
- **Do NOT headline the trap.** If the subtle behavior is the task's CENTRAL,
  explicitly-stated requirement, the solver attends to it, fuzzes it, and passes.
  The trap must be a SECONDARY sub-rule inside a LARGER multi-rule spec.
- **The one lever that worked (twice):** a discriminating fixture in an input
  category the solver under-fuzzes even with the reference in hand. Both MEDIUM
  wins were gitignore-family path matching where the fixture was `<dir>/**` + a
  query of the directory ITSELF (`type=dir` / trailing slash) — random fuzzers
  under-generate directory-typed queries at a `/**` parent, so ~1/3 of solvers
  get it wrong. Recipe: large gitignore/glob-style spec, reference an authoritative
  external tool ("match `git check-ignore`") rather than enumerating rules, and
  bury the `/**`-vs-its-own-directory + parent-exclusion-blocks-reinclude cases in
  the hidden fixtures.
- **Empirically-hard non-spec lever stays the subtle-invariant BUGFIX** (caffeine
  cache-eviction, valkey resize policy, go-mysql FDS) — but those are `debugging`,
  currently ON HOLD.
- **The strongest ALLOWED-category lever (2026-07-01, netted 10 HARD / 17 built):
  an OFFICIAL machine-checkable conformance suite over a spec with a genuinely
  DIVERGENT / irregular long tail, where NO host-stdlib matches.** Ship the stub,
  bake the official suite HIDDEN under `tests/` (a leaked answer table in
  `environment/repo` makes it trivial — see task-clone), oracle passes 100%. Wins:
  WHATWG-URL (urltestdata.json), UTS-46 IDNA (IdnaTestV2), RFC 9535 JSONPath (CTS),
  UAX-14 line-break (LineBreakTest), UAX-29 SENTENCE-break, JSON-Schema-2020-12
  (unevaluated*+$dynamicRef), HTML5 tokenizer (html5lib). **LEARN THE PATTERN, NOT THE RESOURCE: those
  named suites are ILLUSTRATIVE and by now mostly CLAIMED/BUILT by the team
  (including sibling memories) — the LEVER is the reusable asset; a specific
  suite is a shared, FINITE commodity. Do NOT default to a named suite. The
  resource universe (WHATWG / Unicode UTS-UAX / RFC CTS / JSON-Schema / TOML
  toml-test …) is small, so two miners who both "learned the resource"
  independently reach for it and ship duplicates — confirmed: our TOML
  (Go/toml-test) task collided outright with a teammate's, and our
  html5-tree-construction collided with their whatwg-url-parse on the same
  Rust × Data-Processing × WHATWG-conformance cell. Apply the pattern to a
  FRESH spec+suite that is NOT already in the registry, and claim its
  `conformance_suite`+`spec` in `index.jsonl` BEFORE building (see the
  spec-conformance dedupe key below). The resource-agnostic spec for this
  lever, the claimed-resource ledger, AND a complete step-by-step **L1 build
  procedure** live in `.agent/skills/task-miner/lever_patterns.md` — follow that
  runbook top-to-bottom (pivot-check for in-env reference impls, messy-spec check,
  blind probe, fairness audit, disclose-vs-collapse, instruction_check). It is a
  memory-free source of truth: anyone can build a fair-HARD task from it with NO
  personal memory. Read it instead of relying on memory; it is shared, memory is
  per-person.** Independent full
  implementations each miss DIFFERENT tail cases → 0-1/3 solve. NON-winners with a
  suite: clean CLEAN-RULE-SET segmenters (UAX-29 WORD-break was 3/3 EASY — a finite
  rule set + a provided property table is learnable) and well-known algos (byte-BPE,
  3/3). Clean bidirectional CODECS (bech32/punycode/structured-fields) and matching
  engines (git-pathspec) also 3/3 EASY. So the suite is necessary-not-sufficient:
  it must cover a spec people actually implement INCONSISTENTLY. Probe CENTRALLY
  from the manager (this harness spawns subagents async-only); blind solvers must
  NOT paste source (dumps blow up context). Audit any 0/3 for the unfair artifact:
  if all runs fail the SAME single narrow test it is a spec-ambiguity, not hardness
  (a MIME encoded-word task's encode-structure test had legit fold/B-vs-Q freedom).
- **The full lever menu is codified as L1–L4 in
  `.agent/skills/task-miner/lever_patterns.md` — spread batches across levers, not just
  L1.** L1 conformance-suite resources are a SHARED FINITE commodity (claim first); L2
  synthetic interval/continuous-time invariant ledgers are **SATURATED / on cooldown**
  (10+ near-identical `-ledger` instances shipped; empirical ceiling MEDIUM; the
  domain-port re-skin lane is CLOSED — see the L2 STATUS callout + anti-anchoring
  naming rule in `lever_patterns.md` before proposing one); L3
  differential-vs-in-env-authority is fair-by-construction (no disclose-vs-collapse
  trap); L4 multi-vector security hardening is confirmed-HARD in an allowed category.
  Plan every batch as a PORTFOLIO: beating the best model is a ~1/5 lottery per task,
  so design each task for a fair-MEDIUM floor (union-of-misses corpus, per-case or
  banded scoring — see L1 step 5) with HARD upside, and SUBMIT non-Python Medium
  results (`target_difficulty: medium`) instead of discarding them.

## Hardness Calibration

Treat platform difficulty as empirical, not just conceptual.

Downgrade or reject candidates when:

- the likely oracle is a tiny one-file patch
- all tests reduce to variants of the same condition
- a strong agent can locate the fix by grepping one or two obvious symbols from the prompt
- a previous difficulty check shows any frontier agent at `5/5` or aggregate pass rate `>= 80%`
- fewer than 4 meaningful components/surfaces/layers are required to understand
  and solve the task

**Pre-mine fix-shape probe (apply to EVERY candidate before scoring it Hard):**
read the actual fixing diff and ask, "if I describe only the observable symptom
to a strong agent, does it produce this patch by adding an obvious guard /
validation / bound check / nil-check, or by copying a check that already exists
on another path?" If yes → EASY/TRIVIAL, reject for Hard regardless of CVE
status, security domain, or component count (see the Fix-shape filter above).
The patch's REASONING content, not its severity or LOC spread, sets difficulty.
A 7-line CVE fix that mirrors an existing guard onto a second path is TRIVIAL;
a 7-line fix that requires inventing a new invariant is not.

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

Also provide factual input for the later reviewer-facing Difficulty
Explanation:

- `difficulty_rationale`: intrinsic technical reason the task is hard
- `reasoning_bottlenecks`: interacting invariants, layers, or state transitions
- `tempting_partial_fixes`: plausible local repairs that miss required behavior

Do not describe these in terms of LLM/model/agent tendencies. Do not use build
time, repository size, test count, or expected timeouts as hardness evidence.
These fields are mining evidence, not final submission prose.

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
Do not rely on environment README/spec files to carry extra prompt goals or
solution guidance; if the behavior cannot fit fairly in `instruction.md`, reject
or narrow the candidate.

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
