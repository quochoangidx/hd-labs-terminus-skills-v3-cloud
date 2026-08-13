---
name: terminus-regular-task-authoring
description: Use when creating, reviewing, or repairing a Terminus 3 task, especially from the Snorkel Platform Submission Guide. Covers required layout, isolated-verifier constraints, oracle/verifier expectations, CI readiness, and ZIP submission hygiene.
---

# Terminus 3 Task Authoring

Use this skill when the user asks to create or audit a Terminus 3 task.

## Required Layout

Tasks must contain:

```text
instruction.md
task.toml
environment/
  Dockerfile
  .dockerignore
  [agent-visible app/source files]
solution/
  solve.sh
  [optional fix.patch]
tests/
  Dockerfile
  test.sh
  test_outputs.py
  [optional fixtures]
```

Milestones are not part of Terminus 3. Do not put `tests/` or `solution/` inside
the agent image; `tests/Dockerfile` builds a separate verifier image.

## Authoring Workflow

> ⚙️ Tooling shortcuts (repo root): `scripts/new-task.sh <slug> <lang>
> <category>` stamps steps 2–4 and 7–8 as a skeleton with the packaging +
> verifier hygiene (canonical digest-pinned base, full .dockerignore,
> `_hide_corpus`/`nobody`-candidate/`_find_exec_base`/build-exit-check
> helpers, per-case parametrize) pre-wired — fill its TODOs instead of
> re-deriving the boilerplate. `scripts/preflight.sh <task-dir> --strict
> --report-json workspace/reports/<slug>/preflight.json --evidence-dir
> workspace/reports/<slug>/preflight-logs` then runs
> every mechanical gate (layout, .dockerignore, Dockerfile, task.toml, leak
> sweep, zip arcnames, rubric format, docker oracle=1/nop=0, and the
> oracle-under-`--tmpfs /tmp:noexec` repro) in one command — run it before
> zipping, every time.

1. Pick a domain that maps honestly to one exact Terminus 3
   category/subcategory pair. A training-loop repair is `ML / Training`; a
   compiler repair is `Software / Languages`. Do not classify by the repair
   verb alone.
2. Write concise `instruction.md` using absolute paths only.
3. Configure Terminus 3 `task.toml` with top-level `artifacts`, one exact
   category/subcategory pair, descriptive fields under `[metadata]`,
   `environment_mode = "separate"`, `network_mode`, and honest runtime limits.
4. Build `environment/Dockerfile` with `tmux`, `asciinema`, pinned package versions, and digest-pinned `FROM`.
5. Put the starting state under `environment/` (a deliberately buggy state
   only for the bug-repair variant that cleared the category gate).
6. Write deterministic `solution/solve.sh`; prefer `fix.patch` for large codebases.
7. Write digest-pinned `tests/Dockerfile` plus Python `pytest` verifier tests in
   `tests/test_outputs.py`; create every artifact landing directory there.
8. Make `tests/test.sh` run pytest and always write `/logs/verifier/reward.txt`.
9. Run oracle, CI checks, and real-agent trials before packaging.

> ⚠️ All seven Terminus 3 categories are open. Choose exactly one Title Case
> category/subcategory pair by the domain knowledge the task requires, not merely
> because code is written. `template_detection` (first observed 2026-07-13) still blocks tasks matching a named
> template library entry — confirmed `rust_cli` = minimal single-source-file
> stub project + stdin→stdout batch binary + "extend the starter" instruction +
> hidden vector-corpus verifier; assume per-language siblings. Design away from
> the template shape up front (realistic multi-module repo, in-repo tests,
> domain-authentic file I/O). Details and current remediation verdicts live in
> AGENTS.md §9.

## Metadata Rules

For new submissions:

- Use difficulty `frontier`, `advanced`, `core`, or `base`; tiers are
  language-independent.
- Put `artifacts` at top level and every descriptive field under `[metadata]`.
- Set `[verifier].environment_mode = "separate"`.
- Use `[environment].network_mode = "public"` by default and `"no-network"`
  only when internet access would defeat the task.
- Set `[agent].timeout_sec` between 1800 and 18000 seconds.
- Do not emit removed Terminus 2 fields: `version = "2.0"`, `codebase_size`,
  `number_of_milestones`, `subcategories`, `allow_internet`,
  `expert_time_estimate_min`, or `junior_time_estimate_min`.
- `languages` lists the main language(s) used by the task/oracle changes. Do
  not include Python solely because verifier tests are written in pytest.

## Reviewer-Facing Submission Explanations

Terminus 3 requires four reviewer-facing metadata fields:

- `Difficulty Explanation`
- `Solution Explanation`
- `Verification Explanation`
- `Relevant Experience`

These are submission metadata, not agent-visible task requirements. Store them
under `[metadata]` in `task.toml`; Snorkel assembles `README.md` from them. Local
drafts may remain outside the task folder:

```text
workspace/reports/<task-slug>/submission-explanations-source.md
submissions/SUBMISSION-<task-slug>.md
```

Write the source draft only after the task behavior, oracle, verifier, and
available difficulty probes are stable. The source draft is the factual record;
`submissions/SUBMISSION-<task-slug>.md` is the canonical copy-paste packet for
the platform UI (same name/shape as `task-batch` and `task-clone` produce): the
three explanations PLUS the Metadata answers ("approved canonical base image?"
Yes/No + exact digest-pinned image; "Task Inspiration from the Task Gallery?"
Yes/No + Inspiration ID), the full paste-ready Rubrics block (format rules:
AGENTS.md §9 — `Agent`-prefixed single physical lines, closed score set with
leading `+`, positive sum 10–40), and the matching zip file name. The packet is
never shipped inside the ZIP.

### Difficulty Explanation

Explain why the engineering problem itself is difficult:

- identify the interacting subsystems, invariants, state transitions, numerical
  constraints, compatibility paths, or project layers involved
- describe the natural partial fix and the legitimate behavior it misses
- identify the origin and realism of any corpus, capture, trace, fixture set,
  dataset, or other accompanying data; explicitly say when no such data exists
- name the professional role that would perform this work (for example a
  systems engineer, maintainer, analyst, operator, or researcher)
- use semantic local/Harbor solve failures as evidence when available
- distinguish genuine reasoning difficulty from instruction ambiguity,
  verifier defects, dependency failures, cold builds, or timeouts

Do not claim that a task is hard merely because the repository is large, the
build is slow, the verifier has many tests, or runs time out. Do not describe
what an LLM, AI system, model, or agent tends to do. State the technical trap
directly.

### Solution Explanation

Describe the high-level root cause, repair strategy, and key insight behind the
oracle:

- name relevant files, public APIs, state transitions, or algorithms when that
  makes the explanation concrete
- explain how the fix addresses the general behavior and preserves unaffected
  paths
- mention rebuild/regeneration work only when it is part of correctness

Do not paste the patch, reproduce long code blocks, narrate every edited line,
or turn the explanation into instructions for the solving agent. This field is
reviewer-only and must never be copied into `instruction.md` or environment
documentation.

### Verification Explanation

Explain how the verifier distinguishes correct, partial, and broken solutions:

- map the direct regression, boundary case, preservation check, anti-shortcut
  variation, and recoverability/stateful checks to observable requirements
- state why important cases discriminate against the buggy starting state or
  an incomplete fix
- include oracle-pass and nop-fail results only when they were actually run
- mention deterministic semantic parsing, tolerances, or generated fixtures
  when relevant

Do not settle for "all tests pass", list only test function names, expose hidden
fixture contents unnecessarily, or describe source-code-shape assertions.

### Human-Writing Pass

Apply the human-writing pass only after factual review:

- start with the task-specific point; remove template openings and conclusions
- prefer concrete behavior, numbers, paths, and API names over unsupported
  abstractions such as "robustness", "comprehensive coverage", or "confidence"
- vary sentence and paragraph shape instead of giving all three fields the same
  problem/fix/test skeleton
- remove hedging when the evidence is conclusive
- do not cite submission guidelines, reviewer criteria, policy dates, or call
  the prose "LLM-like"
- do not mention LLMs, AI, models, agents, anti-LLM mechanisms, or detection
  avoidance in the three explanations
- preserve every technical fact, threshold, API name, path, and validation
  result from the source draft

Natural prose is an editorial goal, never permission to weaken or embellish the
technical record. After rewriting, compare the final version against the source
draft and the task artifacts once more.

## Prompt Rules

**Step 0 — after writing (or editing) `instruction.md`, ALWAYS run the mechanical
pre-flight and fix every finding before anything else:**

```bash
python3 .agent/skills/terminus-regular-task-authoring/scripts/instruction_preflight.py <task-folder>
```

It catches the structural triggers (headers, bullets, tables, over-length, hint
phrases, verifier/test leakage, mapping-chain density) mechanically. A clean run
is necessary, not sufficient — the content rules below (algorithm narration,
mechanism leaks, sufficiency of tested values) still need a read.

**Mandatory semantic sufficiency gate:** before any difficulty probe, create
`workspace/reports/<slug>/instruction-sufficiency.json`, run two blind contract
reviews, and validate it with
`scripts/sufficiency_manifest_check.py`. Follow
[`references/instruction-sufficiency-gate.md`](references/instruction-sufficiency-gate.md)
exactly. Hidden cases and expected outputs are allowed; hidden contract rules
are not. Oracle/NOP success, solver pass rates, union coverage, or a larger
platform sample never override this gate.

**`instruction_check` — pass on the FIRST try. Two DIFFERENT checks share the word
"instruction" and pull in OPPOSITE directions, so blindly adding or cutting detail
ping-pongs between them. Identify which one failed, then pull the matching lever:**

| Failure | It complains that… | Usual cause | Lever |
|---|---|---|---|
| *"reads like a reference manual / design document"* (structural) | too much structure / enumeration | `##`/`###` headers, bullet or numbered rule lists, tables, step-by-step algorithm narration, function-signature / struct-field dumps, "pay attention to…", >~300 words | REMOVE structure → flowing prose; delegate the rule-set to the named standard |
| *Task Instruction Sufficiency* / `task_specification` (completeness) | a behavior/value the hidden tests assert is not stated | prompt defers everything to a spec URL but a test pins an edge/constant an agent won't infer (e.g. TOML's UTF-8 BOM) | ADD that edge/value in a SENTENCE (never a table); or make the verifier behavioral so it isn't pinned |

**#1 recurring cause of the structural FAIL:** writing `instruction.md` with `## Input` /
`## Output` / `## Rules` headings and bullet lists — that shape alone trips it every time.
Use flowing prose: no headers, no bullets, no tables.

**Sweet spot that passes BOTH** = prose containing only the one-sentence objective + the
exact I/O contract + "treat <NAMED STANDARD> as the definition of correct behavior" + one
or two sentences naming any tested edge the standard leaves implicit. Delegate general
rules to the standard; state only what it does NOT define plus tested constants; keep code
identifiers out (make the verifier opaque instead).

**Disclosure ladder — when a tested edge/value MUST be stated (sufficiency) but keeps
tripping the structural check, escalate in this order; never iterate wording sideways
(the check flip-flops prose↔structure across re-runs):**

1. **One flowing-prose sentence inline** (never a table/list/mapping chain — a long run
   of "X is Y, X is Y" mappings reads as a table even in prose). Right default for a
   single edge or constant. Embed examples at the operation definitions so they read as
   contract clarification, not enumeration.
2. **An in-environment reference DATA file** (`/app/examples.json` with oracle-verified
   input→output pairs, a format doc, a non-derivable standard table like `entities.json`)
   plus a one-line declarative pointer in `instruction.md`. instruction_check judges ONLY
   instruction.md, so this clears it while keeping sufficiency/symmetry. Rules: ship
   DATA, never the task's goals or a prompt extension (the "environment files must not
   compensate for a short prompt" rule below still applies — reference data a realistic
   engineering artifact would contain is fine, relocated prompt prose is not); examples
   must be disjoint from the hidden corpus and verified against the oracle before
   writing; `COPY` the file before the image's `git add -A` initial commit; recheck
   build-context size after adding env files; keep the words
   "verifier"/"test" out of the file (bare-word scanner).
3. **Keep the flagged items and ship the non-blocking ⚠️** when they are test-pinned
   literals/values and neither form clears the check — removing them trades a warning
   for a blocking `behavior_in_tests`/sufficiency failure. If a pinned exact-output
   token is the irritant, consider relaxing the verifier to observable accept/reject
   with single-rule-isolating cases instead (then the token can leave both places).

**Writing the in-env reference file itself (ladder tier 2 — `FORMAT.md`, `SPEC.md`,
`examples.json`):**

- Two proven shapes: an **examples file** (oracle-verified input→output pairs, JSON
  with a short `note` per entry) and a **format/contract doc** (output schema and
  conventions). Pick by what the blind runs actually missed.
- Formatting is FREE here — headers, bullets, and tables are fine in environment
  files; instruction_check judges only `instruction.md`. But keep GRADER-FACING
  vocabulary out (the feedback scanner greps environment files and reviewers read
  them): none of "verifier", "test", "pytest", "grading", "grader", "compares",
  "checks", "reward". Write it as a product/format contract ("the output is…",
  "a value is emitted as…"), never "grading compares…" / "the check asserts…"
  (HOCON 2026-07 was flagged for exactly this).
- **The reference doc MUST AGREE with the instruction and rubric — no
  contradictions.** A format doc that says "key order is ignored" while the
  prompt/rubric require sorted keys (or vice-versa) is a review reject: it both
  leaks grader mechanics and contradicts the visible contract. Before shipping,
  reconcile the doc, the instruction, and the rubric to one story; if the
  verifier can't enforce a property (see the ordering/value-compare rule under
  Verifier Rules), state it in NONE of the three.
- **Completeness is the whole point:** document EVERY convention the expected output
  depends on — the sort order of each emitted array, merge/coalesce rules for
  adjacent or overlapping spans, half-open vs closed boundary semantics, tie-breaks,
  zero-length handling, null/absent-field shape. An undocumented convention that
  every solver must guess is a guaranteed universal blind spot (a coldchain-style
  task went 0/N on exactly this: unmerged overlaps + unspecified array order).
- Verify every stated fact and example **against the oracle binary before writing
  it down** — never from memory; one confidently-wrong example poisons the task.
- Style: a realistic engineering artifact a team would keep in the repo — states
  what the system requires, never how to implement it, no trap-pointing ("note the
  tricky…"), no algorithm walkthrough (the env-docs rules below apply in full).
- Disclosure budget: state every graded contract rule while withholding worked
  solutions, fixture literals, expected outputs, root cause, and implementation
  method. If stating a required rule makes the iteration sample 100%, drop or redesign
  the task; never preserve difficulty by hiding that rule.

Copyable skeleton (no headers/bullets/tables, ≤300 words):

> The program at `<path>` should `<objective, one sentence>`. It reads `<input>` from
> `<source>` and writes `<output>` to `<destination>`. Its behavior follows
> `<NAMED STANDARD>` exactly; treat that standard as the definition of correct behavior.
> `<One or two sentences for any tested edge an agent would miss, e.g. "a leading UTF-8
> BOM must be accepted and silently ignored">`. Build it with `<cmd>`; the output must be
> exactly `<format>` and nothing else.

Binary preflight (every box YES before running the check):

- no `##`/`###` headers, no bullet/numbered lists, no tables;
- no step-by-step algorithm, no function signatures / struct-field dumps;
- no "pay attention" / "note that" / "make sure" hint phrases; no PR/issue/test-name/rubric leakage;
- ≤ ~300 words of flowing prose;
- every VALUE/constant/edge the hidden tests assert appears in a sentence (sufficiency);
- general rule-sets delegated to the named standard, not transcribed;
- code identifiers the tests pin are NOT in the prompt (verifier is behavioral instead).

For **L1 conformance tasks**, "implement <spec>; treat <spec> + its official suite as the
definition" normally satisfies BOTH. But if a SINGLE tested edge is both undisclosed AND
trivially pivotable via an in-env reference (TOML + BOM + `tomllib`), you are in the
disclose-vs-collapse trap — fix the RESOURCE, not the prose (see
`.agent/skills/task-miner/lever_patterns.md`, L1 step 8).

`instruction.md` should:

- Be short and human-styled.
- State observable behavior, not implementation hints.
- Mention all required paths and output files.
- Avoid issue URLs, PR numbers, exact test names, canaries, and rubrics.
- Include enough edge-case requirements that tests are fair.
- Apply the real-user prompt test to every sentence: would a developer who did
  not already know the solution naturally include this detail? If not, it is
  probably a hint rather than a requirement.
- For spec / conformance tasks, DELEGATE the rule enumeration to the named
  authoritative standard instead of transcribing it. Say "expansion follows RFC
  6570 Level 4 exactly, treat it as governing" rather than walking through every
  operator, encoding set, and edge case. The CI `instruction_check` rejects
  instructions that "read like a reference manual"; a long enumeration also hints
  at the traps and makes the task easier. KEEP explicit only what the standard
  does NOT define: the CLI, the exact input/output format, the `ERROR: <code>`
  strings and exit codes, and any task-specific decisions (which malformed inputs
  map to which error). Verify instruction/test symmetry still holds: everything
  the verifier checks must be derivable either from the named standard or from the
  kept task-specific contract. Stay narrative prose; do NOT convert to bullet
  lists or `## Input`/`## Rules` headings (the same check penalizes that shape).
  CAUTION when delegating: the named standard must AGREE with the test ground
  truth. If the standard has advisory / "should" language that a real runtime
  implements differently, delegating creates a spec ambiguity, agents follow the
  standard's strict reading and fail while the tests use the runtime's permissive
  behavior (`task_specification: FAIL`, an unfair 0/N). Confirmed 2026-07-01: a
  dpkg task delegated validity to "the Debian Policy Manual" (upstream *should*
  start with a digit) but tested against real `dpkg --compare-versions` (which
  accepts `a`/`abc`/`1..0`); 8/10 trials flagged the spec, and every agent failed
  the same ~5 validity cases. Fix: pin the exact runtime behavior the tests use
  ("validity matches `dpkg --compare-versions` at runtime; upstream MAY begin with
  a non-digit"), or restore an explicit unambiguous rule. NOTE this also revealed
  the task was never genuinely hard, its whole 0/N came from that one ambiguity;
  see [[platform-hard-can-be-unfair-ambiguity-artifact]].
  NEVER add a "here is where a naive implementation goes wrong / the tricky parts
  are X, Y, Z / a few points bear emphasis" paragraph, and NEVER mention the
  verifier or the tests ("the verifier leans on this", "getting it wrong is
  easy"). Those are no-hints violations (CI `instruction_check` flags them) AND
  they make the task easier by pointing at the traps. State the observable
  contract and the governing standard; let the solver discover the hard parts.
  Confirmed 2026-07-01: four conformance tasks (UAX-14/29, RFC 9535, Selectors L4)
  shipped exactly such pitfall paragraphs and got flagged.
- Do not narrate the internal mechanism or root cause (the #1 client reject,
  June 2026 trial feedback). Describe the observable symptom and the desired
  outcome, not how the code is wrong inside. Cut "Right now the parser does X
  internally" sentences (state what is observed instead), "the other path
  already handles it" tells (they point at where to copy the fix), and
  fix-shaped requirements that restate the implementation (state them
  behaviorally). KEEP test-asserted spec contracts even when specific
  (thresholds, public API the tests drive, preservation/edge cases) so
  instruction/test symmetry still holds.

Environment files must not compensate for a short prompt:

- Do not hide step-by-step walkthroughs, TODO hints, commented solution guides,
  or prescriptive implementation notes in README, config, scripts, comments, or
  source files.
- `spec.md`, README, and architecture docs may define requirements, schemas,
  protocols, or business rules, but they must state what the system requires,
  not how to solve the task.
- Do not split the task's logical prompt or goals out of `instruction.md` into
  environment docs to dodge length limits. Supporting docs should read like
  realistic engineering artifacts, not prompt extensions.

Before finalizing, run an instruction/test symmetry audit:

- list every exact string, flag, command, file path, output key, XML/JSON field, and ordering guarantee asserted by tests
- ensure each asserted behavior appears naturally in `instruction.md`
- include preservation requirements explicitly, even when they test "unchanged" behavior outside the main bug path
- if tests cover non-target modes, aliases, legacy modes, fallback paths, or normal layouts, state that those modes must continue working
- remove tests for behavior that would be unfair to state in the prompt
- keep implementation symbols out of the prompt unless they are public API
- distinguish two kinds of things a test can pin (docs: prompt-styling.md gives
  the what not the how; `behavior_in_task_description` + `structured_data_schema`
  want asserted behavior and output schemas explicit; prompt-styling section 4
  "Overly Prescriptive Guidelines" calls listing exact function signatures /
  struct layouts BAD):
  - VALUES the test asserts (numeric thresholds, output keys, JSON/CSV/data
    schema the agent produces, exact-match constants) MUST be explicit. Omitting
    a tested cutoff makes agents guess and fail unfairly; this is required
    sufficiency, not over-spec.
  - CODE IDENTIFIERS the test pins (function signatures, struct field
    names/types, project layout the agent must produce) are exactly what
    prompt-styling section 4 forbids prescribing. Do NOT resolve a compile-time
    name mismatch by pasting a struct schema or signature list into the prompt
    (that is the "reads like a design document" failure). Resolve it by making
    the verifier BEHAVIORAL/OPAQUE: drive observable output and pass any new
    value straight back into the API as a black box, so the test never reads
    its fields and the instruction can say "you choose its fields." That often
    means the API owns more of the protocol (e.g. a resume option takes the
    full input and seeks internally rather than the caller slicing by a field).
    Only when a brand-new exported symbol genuinely cannot be made behavioral,
    name that single symbol minimally (a new type/function the test must call by
    that exact name) and nothing more; never its field schema.

Common quality-check failure: a test asserts that unaffected modes such as `prepend`/`append`, non-editable installs, normal parsers, or legacy fallbacks still work, but `instruction.md` only describes the target mode. Fix by adding one natural sentence like "Keep `<mode A>` and `<mode B>` behavior unchanged for the same layout" or remove that preservation test.

## Docker Rules

`environment/Dockerfile` must:

- Use `FROM ...@sha256:<digest>` on every stage.
- Use a **canonical Terminal-Bench base image** for the final runtime stage when
  one matches the task's language (all under `public.ecr.aws/docker/library/`,
  exact digest required): `python:3.13-slim-bookworm@sha256:01f4…24fb`,
  `node:22-bookworm-slim@sha256:f3a6…2383`, `golang:1.24-bookworm@sha256:1a6d…77ac`,
  `rust:1.85-slim@sha256:9f84…cb36`, `eclipse-temurin:21-jdk-jammy@sha256:25d1…4b14`,
  `gcc:13-bookworm@sha256:930f…ac5c`, `ruby:3.3-slim-bookworm@sha256:e767…e3df`,
  `maven:3.9.9-eclipse-temurin-21@sha256:3a4a…211e`, `debian:bookworm-slim@sha256:4724…655d`,
  `ubuntu:24.04@sha256:0d39…e932`. (Full digests live in `docs/creating-tasks/dockerfile-best-practices.md`.)
  A non-canonical base is allowed only with a brief, credible justification in the
  `Dockerfile` or task `README.md`; missing/vague justification is blocked.
  - **Reviewer reality (Terminal-Bench 2.0):** a review demanding
    `ghcr.io/laude-institute/t-bench/*` over the digest-pinned
    `public.ecr.aws/docker/library/*` images is a known **FALSE POSITIVE** —
    push back with citations rather than switch registries (AGENTS.md §9;
    inventory-purl 2026-07-18: the public.ecr.aws digest-pinned image IS the
    sanctioned one). To pre-empt the flag, put a brief justified comment
    **directly above the `FROM` line in the Dockerfile** (canonical
    digest-pinned base per the sanctioned list; pinned for reproducibility;
    consistent with the rest of the suite). A justification the reviewer can
    see in-file resolves the warning; one buried elsewhere does not.
- Never include a `# syntax=docker/dockerfile:1` line — platform build nodes
  cannot pull the BuildKit frontend, so it fails as "Oracle failed". Likewise
  no `RUN --mount=type=bind`; convert mounts to a plain `COPY` plus `rm -rf`
  in the same layer.
- Install `tmux` and `asciinema`.
- For cloned-repo tasks, `git init` the task workdir after the final source
  `COPY` (`RUN git init -q && git config user.email task@example.com && git
  config user.name task && git add -A && git commit -q -m "initial task
  state"`). Agents often apply edits via `git apply` and self-check with `git
  diff`; if `/app` is not a git repo (cloned `.git` stripped, and excluded from
  the build context), patches silently fail to land and otherwise-correct agents
  score 0 ("Some tests not passed by any agent run"). Runs in the image, so it
  does not trip the `.git`-in-context hygiene warning; oracle/nop unaffected.
- Pin language dependencies exactly.
- Keep verifier dependencies out of the agent image. Bake them with exact pins
  into the separate `tests/Dockerfile`; never fetch packages at verifier runtime.
- Keep `environment/` under 100 MiB total and each file under 50 MiB.
- Include `.dockerignore` for non-trivial environments, and always start from
  the standard clutter/secrets exclusion set (reviewers flag a thin `.dockerignore`
  that omits these) — then add any task-specific build outputs (e.g. `numfmt`,
  `*.o`, a Rust `target/`):

  ```gitignore
  .git
  .gitignore
  **/.git
  .env
  solution/
  tests/
  **/.DS_Store
  **/._*
  **/__pycache__/
  **/*.pyc
  **/.pytest_cache/
  **/.mypy_cache/
  **/.ruff_cache/
  **/node_modules/
  ```

  `solution/`, `tests/`, and `.env` are mandatory: omitting them passes local
  harbor (NOP=0, Oracle=1) but gets reviewer-returned — grep-verify all three
  before zipping (`scripts/preflight.sh` FAILs on each).
- Avoid heredocs for source files; store files on disk and `COPY` them.
- Pin downloaded binaries by version and checksum; avoid `curl | sh`.
- Order Dockerfile layers from stable dependencies to volatile task source.
- Extract copied archives during build and remove the archive in the same stage.
- Avoid broad recursive `chmod -R` or `chown -R`; use `COPY --chmod` or
  `COPY --chown` for targeted metadata.
- Keep `.git`, `.env`, credentials, package caches, build outputs, and
  AI-framework scaffolding filenames such as `CLAUDE.md` or `skills.md` out of
  `environment/`.

`tests/Dockerfile` must digest-pin every `FROM`, install `pytest`,
`pytest-json-ctrf`, and verifier packages with exact pins, `COPY . /tests/`,
and create parent directories for every top-level artifact path.

Do not put verifier dependency wheels in `tests/`. The `tests/` directory should
contain verifier scripts and fixtures only; install verifier dependencies during
Docker build.

## Verifier Rules

Tests must:

- Be Python pytest tests, even for non-Python tasks.
- Run in the isolated verifier and read only declared artifacts.
- Test behavior, not source-code strings.
- Have docstrings on every test.
- Cover every explicit and important implicit prompt requirement.
- Include boundary cases and at least one regression guard.
- Assert no internal crash/traceback when the task is about recoverable behavior.
- Pin the OUTPUT SHAPE, not just the values at expected positions. For a
  line/record-oriented CLI, assert the exact count of output lines equals the
  number of requests (and stdout ends cleanly) so a program that prints a banner,
  a debug line, or an extra/missing trailing line fails — indexing only the
  positions you expect silently lets stray output through.
- When the instruction requires source changes, declare the project directory
  as an artifact and rebuild it inside the verifier with a toolchain baked into
  `tests/Dockerfile`. When the deliverable itself is a binary, declare and test
  that binary directly. Never assume the agent container remains reachable.
- Keep the verifier and the prompt SYMMETRIC on reject cases and on ordering.
  If `instruction.md` says an invalid input "writes nothing useful to stdout,"
  assert `proc.stdout == b""` for reject cases, not only `returncode != 0`
  (else a "print garbage then exit 1" shortcut passes; KDL 2026-07). Conversely,
  do NOT require an output property the verifier cannot enforce: if you compare
  parsed VALUES (order-independent, e.g. to tolerate a `1000.0` vs `1000`
  float-repr gap), then sorted-key / key-ordering is ungraded — drop that
  requirement from the prompt/rubric/format-doc rather than leaving a
  never-checked clause (HOCON 2026-07).
- Protect the reward channel before any candidate code runs: create
  `/logs/verifier` with mode `0700`; merely creating it with the default mode is
  insufficient because a demoted candidate can still read or alter reward/CTRF
  state through surviving descendants.
- Execute every untrusted candidate in a fresh process group/session. On timeout
  and after normal completion, kill and reap the whole group so forked children
  cannot keep capture pipes open, survive into later cases, or touch verifier
  state. A direct `subprocess.run(..., capture_output=True, timeout=...)` without
  descendant cleanup is not acceptable isolation.
- Treat every promise in `instruction.md` and agent-visible contract documents
  as graded unless the sufficiency manifest explicitly records it as ungraded.
  In particular, an output-write failure promise needs a sentinel-preservation
  test, and a serialized key-order promise needs a raw-order assertion rather
  than parsed dictionary equality.

Avoid quality-check failures:

- do not assert source-code shape, private helper names, or exact implementation
- parse structured outputs semantically
- for floating-point or irrational NUMERIC results, assert an accuracy
  tolerance (`|got - trueRef| <= tol`) instead of exact string equality. Exact
  matching forces agents to reproduce one implementation's undocumented
  rounding (often a float64 artifact that is LESS correct than the true value),
  so a more-accurate agent fails unfairly. Pick `tol` so the oracle's own output
  clears it and a naive/buggy impl misses by orders of magnitude; for a
  `precision`-parameterised API set `tol` to that floor (precision=10 -> 1e-10).
  Keep exact string match only for genuinely exact results (integer powers,
  defined truncations, edge-case zero/error)
- when the instruction mandates a REFACTOR of an EXISTING interface/signature
  (not just new behavior), behavioral tests alone let an agent add a parallel
  interface and skip the refactor. Add two guards: (a) a compile-time
  interface-satisfaction assertion (`var _ pkg.Interface = (*Probe)(nil)` where
  `Probe` has the new method signature) so the verifier only compiles if the
  EXISTING interface was actually changed; this checks a public type-system
  contract the instruction requires, not private implementation; and (b) a
  separate `go build ./...` test, since `go test ./_verifier_test/` compiles
  only transitively-imported packages, not sibling subpackages with their own
  call sites of the changed interface
- include docstrings explaining the user behavior being tested
- keep randomization deterministic
- ensure `nop` fails for the intended behavior, not setup/tooling

## tests/test.sh

Use this shape:

```bash
#!/bin/bash
set -uo pipefail

install -d -m 700 /logs/verifier
echo 0 > /logs/verifier/reward.txt
python3 -I -m pytest -p no:cacheprovider --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

exit 0
```

Do not use `set -e`; pytest failure must reach the reward block. The trailing
`exit 0` is deliberate because Harbor grades from `reward.txt`, not the script
status. If the published Terminus 3 skeleton differs, the skeleton wins.

Do not run runtime setup, `apt-get`, `npm install`, or network downloads in
`tests/test.sh`. Bake verifier dependencies into the Docker image; `test.sh`
should run the verifier and write `/logs/verifier/reward.txt`, not install
packages.

## Oracle Rules

`solution/solve.sh` must:

- Start with `set -euo pipefail`.
- Be deterministic and self-contained.
- Avoid network access.
- Apply a real fix, not write hardcoded expected outputs.
- Contain ONLY the hunks relevant to the task. When the patch is generated from
  an upstream PR or a multi-concern diff, strip every file/hunk unrelated to the
  stated instruction (a separator fix should not also bundle a regexp/string
  refactor). Bundled changes create a hidden requirement that widens the agent's
  scope beyond instruction.md and misaligns the oracle with the goal (review
  flags "Solution Patch Contains Unrelated Changes"). After stripping, confirm
  the build step in `solve.sh` still passes; if an unrelated hunk turns out to
  be load-bearing for the build, that is a signal the snapshot is inconsistent,
  not a reason to keep the refactor.
- Rebuild or regenerate artifacts when the verifier invokes a built binary.

## Final Checks

Run, when available:

```bash
stb harbor run -a oracle -p <task-folder>
stb harbor run -a nop -p <task-folder>
stb harbor check <task-folder>
stb harbor run -m @openai/gpt-5.6 -k 4 -p <task-folder>
stb harbor run -m @anthropic/claude-opus-5 -k 4 -p <task-folder>
```

For submission ZIPs, compress the contents of the task folder, not the folder itself.
Generate rubrics through the platform UI before reviewer submission: check
"Generate Rubric(s)" while "Send to Reviewer" is unchecked, wait for the
generated rubric, edit it for accuracy, then uncheck "Generate Rubric(s)" before
checking "Send to Reviewer" so the edited rubric is not overwritten.
Rubrics must be trace-focused. Every criterion line starts with `Agent` and
ends with `, +/-N`; allowed values are only 1, 2, 3, or 5; do not use 4; and
positive scores must carry an explicit leading `+` (write `+3`, not `3`) —
unsigned positives are sent back for revision.
Use a flat list, 10-40 total positive points, and at least one negative
criterion. Rubrics grade trace-evidenced engineering behavior, not the final
pytest result; make each line task-specific and diagnostic. Do not
reference tests, verifier logic, `test.sh`, `test_outputs.py`, `/tests/`,
hidden tests, CI, reward files, pytest, or final test results.

Quality preflight:

- top-level `artifacts`, isolated verifier mode, exact taxonomy pair, current
  difficulty tier, 3-6 tags, and all four explanation/experience fields are present
- `languages` excludes verifier-only Python
- reviewer-facing submission explanations in `task.toml` contain no unsupported
  claims or agent/AI meta language
- `tests/Dockerfile` is digest-pinned, installs all verifier dependencies,
  copies `/tests`, and creates artifact landing directories
- no root-level `pyproject.toml`
- final runtime base image is canonical for the task's language (or non-canonical with a credible justification)
- no `.ruff_cache`, `.pytest_cache`, `__pycache__`, `.DS_Store`, `._*`, `__MACOSX`, reports, logs, or submissions in the ZIP
- no dependency wheels in `tests/`
- no `tests/` or `solution/` copied into the Docker image
- no `privileged: true`, no `SYS_ADMIN`/`NET_ADMIN`/`SYS_MODULE` capabilities,
  no `/var/run/docker.sock` mounts; compose volume mounts must not shadow the
  reserved paths `/logs/artifacts`, `/logs/verifier`, `/tests`, `/solution`
- no runtime dependency setup in `tests/test.sh`
- no end-to-end solution generator in `tests/`; golden data, parsed output,
  sealed truth, and spec-derived invariants are allowed
- whenever the task promises configurable input, a mutation re-run proves that
  the verifier reads the config dynamically rather than restating its values
- no rubric or instruction references to tests, verifier logic, `test.sh`,
  `test_outputs.py`, `/tests/`, hidden tests, CI, reward files, pytest, or final
  test results
- no unverified downloads, `curl | sh`, stale copied archives, broad recursive
  permission rewrites, or cache-hostile Dockerfile layer ordering
- no hidden solution walkthroughs, procedural hints, or prompt-bypass
  instructions in environment files, comments, README, configs, scripts, TODOs,
  `spec.md`, or architecture docs
- oracle passes, nop fails, and failures are behavioral rather than infrastructure
- for any corpus-graded verifier, the per-case pass-table pre-audit has run
  before zipping (see `task-clone` Quality Preflight / `task-local-solve-probe`):
  re-score the stored blind-probe diffs per-case and confirm (1) every case has
  ≥1 probe passer, (2) the best union still fails >0 cases, (3) every feature
  cluster keeps a soft representative a majority of runs pass

If the platform returns the task with `❌ Some tests not passed by any agent
run` (blocking 0/N coverage flag), do not improvise — follow the decision tree
in `.agent/skills/task-revise-flag-remediation/SKILL.md` (Step 1.5 first:
suspect the oracle before pruning; Step 1.75: single-lever fingerprint → DROP).
