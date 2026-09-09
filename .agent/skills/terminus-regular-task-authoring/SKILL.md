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
6. Write digest-pinned `tests/Dockerfile` plus Python `pytest` verifier tests in
   `tests/test_outputs.py`; create every artifact landing directory there.
7. Make `tests/test.sh` run pytest and always write `/logs/verifier/reward.txt`.
8. Collect the platform-visible unit IDs and pass the verifier architecture
   gate before writing the Oracle. Use 50–1000 units/at least six clusters for
   cheap deterministic tasks, or 20–80 scenarios/at least four clusters for
   expensive stateful tasks; require two cross-cluster units and two verifier
   shapes. A failed gate returns to design.
9. Write deterministic `solution/solve.sh`; prefer `fix.patch` for large codebases.
10. Run Oracle/NOP, bind the Oracle CTRF to the verifier matrix, then run V3
    inferability, mutation-backed semantic coverage, CI checks, and real-agent
    trials before packaging.

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
- Declare all three network policies. `[environment].network_mode` must be
  `"public"`; `[agent].network_mode` and `[verifier].network_mode` must each be
  `"public"` or `"no-network"` and match what that phase genuinely needs.
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
workspace/submissions/SUBMISSION-<task-slug>.md
```

Write the source draft only after the task behavior, oracle, verifier, and
available difficulty probes are stable. The source draft is the factual record;
`workspace/submissions/SUBMISSION-<task-slug>.md` is the canonical copy-paste packet for
the platform UI (same name/shape as `task-batch` and `task-clone` produce): the
four explanation fields PLUS the Metadata answers ("approved canonical base image?"
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

### Relevant Experience

State the concrete domain, toolchain, repository, or verifier-design background
that supports the task. Keep it factual, concise, and free of invented personal
credentials or policy-directed language.

### Human-Writing Pass

Apply the human-writing pass only after factual review:

- start with the task-specific point; remove template openings and conclusions
- prefer concrete behavior, numbers, paths, and API names over unsupported
  abstractions such as "robustness", "comprehensive coverage", or "confidence"
- vary sentence and paragraph shape instead of giving the three technical explanations the same
  problem/fix/test skeleton
- remove hedging when the evidence is conclusive
- do not cite submission guidelines, reviewer criteria, policy dates, or call
  the prose "LLM-like"
- do not mention LLMs, AI, models, agents, anti-LLM mechanisms, or detection
  avoidance in any of the four fields
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
mechanism leaks, goal clarity, and evidence inferability) still need a read.

**Mandatory V3 evidence-inferability gate:** before a full difficulty probe,
create `workspace/reports/<slug>/instruction-sufficiency.json` with
`schema_version: 3`, run exactly two fresh task-visible fairness reviews in
parallel, and validate
it with `scripts/sufficiency_manifest_check.py --require-v3`. Follow
[`references/instruction-sufficiency-gate.md`](references/instruction-sufficiency-gate.md)
exactly. Keep the goal/interface explicit, allow domain semantics to be inferred
from one or more visible sources, and forbid only arbitrary or unobtainable
hidden knowledge. A skeleton probe needs a lightweight goal/evidence audit, not
the full two-reviewer manifest. Oracle/NOP success, pass rates, or union coverage
never override a real ambiguity or impossible-information defect.

**Mandatory semantic coverage gate for counted probes:** after the complete
verifier and oracle are stable, follow
[`references/semantic-coverage-gate.md`](references/semantic-coverage-gate.md).
Create `semantic-coverage.json`, enumerate every promised public surface,
separate fixture rows into independent mechanisms and interactions, execute a
plausible partial-fix mutant for each node, and run
`scripts/semantic_coverage_check.py`. Use `--advanced-plus` for an
Advanced/Frontier shortlist. Freeze that snapshot before creating solve copies.
Any later instruction, environment, solution, test, metadata, verifier-matrix,
or mutation change invalidates the probe. Skeleton probes are exploratory only.

**Mandatory verifier architecture gate before Oracle work:** mining first
declares a profile and planned budget. As soon as the verifier skeleton is
collectable, create `workspace/reports/<slug>/verifier-matrix.json` and run:

```bash
python3 .agent/skills/terminus-regular-task-authoring/scripts/verifier_architecture_check.py \
  matrix workspace/reports/<slug>/verifier-matrix.json \
  --task-slug <slug> --allow-missing-ctrf
```

Do not write the Oracle, build Docker images, or run Oracle/NOP for a failed
matrix. After Oracle runs, add its raw CTRF path/hash and rerun without
`--allow-missing-ctrf`; exact CTRF IDs must match behavior plus declared
non-behavior IDs. Oracle=1 and NOP=0 prove executability, not breadth. Call the
suite a smoke suite until both this gate and semantic coverage pass.

**Mandatory pre-probe ordering gate:** before `probe.py prepare` in counted
mode, run strict Docker preflight without emitting a ZIP, complete the
folder-level client/manual review, and audit all task-visible prose. In
`task-batch`, one auditor independent of the builder performs semantic realism,
folder/manual, and task-style judgment in a single pre-freeze session; the
three receipts share its exact transcript provenance. Preserve
them as `probe-preflight.json`, `pre-freeze-review.json`, and
`task-style-preflight.json`, create `agent-session-budget.json`, then pass
`task-local-solve-probe/scripts/preprobe_check.py`. Package only after the
counted difficulty gate. Audit post-probe submission prose separately; a later
task-tree edit invalidates the frozen runs. Reuse the same auditor identity for
the post-probe submission and exact-ZIP review instead of spawning new agents.

**`instruction_check` — pass on the FIRST try. Two DIFFERENT checks share the word
"instruction" and pull in OPPOSITE directions, so blindly adding or cutting detail
ping-pongs between them. Identify which one failed, then pull the matching lever:**

| Failure | It complains that… | Usual cause | Lever |
|---|---|---|---|
| *"reads like a reference manual / design document"* (structural) | too much structure / enumeration | `##`/`###` headers, bullet or numbered rule lists, tables, step-by-step algorithm narration, function-signature / struct-field dumps, "pay attention to…", >~300 words | REMOVE structure → flowing prose; delegate the rule-set to the named standard |
| `task_specification` / V3 inferability | an exact success-surface value is missing, or the graded model cannot be derived from visible evidence | an undocumented output key/arbitrary constant, or a hidden policy with no supporting trace/spec/convention | state only the non-inferable interface fact; otherwise add authentic evidence, relax the assertion, or make the verifier accept semantic equivalents |

**#1 recurring cause of the structural FAIL:** writing `instruction.md` as a
reference manual with `## Input` / `## Output` / `## Rules` sections, nested
lists, tables, and long enumerations. Prefer flowing prose, but a concise flat
list of at most 20 bullets is valid when it sounds natural and states outcomes
rather than intermediate steps.

**Terminus 3 sweet spot** = a concise goal + exact deliverable/interface + pointers
to realistic evidence. State arbitrary task-specific decisions that no evidence
defines. Do not narrate the model the agent is supposed to reconstruct. A named
standard is useful only when it is genuinely the governing source and reachable
under the task's network mode.

**Non-inferable-value ladder:** use this only for exact schema/interface facts or
arbitrary conventions that the agent cannot derive. Do not use it to disclose a
domain inference merely because a blind run missed it.

1. **One flowing-prose sentence inline** (never a table/list/mapping chain — a long run
   of "X is Y, X is Y" mappings reads as a table even in prose). Right default for a
   single edge or constant. Embed examples at the operation definitions so they read as
   contract clarification, not enumeration.
2. **An authentic in-environment source** (a format schema, trace, drawing,
   config, protocol capture, labeled archive, or non-derivable standard table)
   plus a one-line declarative pointer in `instruction.md`. instruction_check judges ONLY
   instruction.md, so this can supply evidence without becoming a prompt extension.
   Rules: ship artifacts a real team would possess, never a synthetic answer key
   created only to teach the hidden tests; `COPY` the file before the image's
   `git add -A` initial commit; recheck
   build-context size after adding env files; keep the words
   "verifier"/"test" out of the file (bare-word scanner).
3. **Relax representation-specific verification** when an exact token/layout is
   not part of the user outcome. Parse semantically or accept an equivalence class.

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
- **Interface completeness is the point:** document representation choices the
  consumer must know (schema, required order, units, public names). Domain
  semantics may remain implicit when the supplied evidence or convention
  determines them. If multiple representations are equally valid, the verifier
  must accept the equivalence class instead of forcing the oracle's formatting.
- Verify every stated fact and example **against the oracle binary before writing
  it down** — never from memory; one confidently-wrong example poisons the task.
- Style: a realistic engineering artifact a team would keep in the repo — states
  what the system requires, never how to implement it, no trap-pointing ("note the
  tricky…"), no algorithm walkthrough (the env-docs rules below apply in full).
- Disclosure budget: state the goal and non-inferable success surface; preserve
  domain inference, root-cause discovery, and implementation choice. If a rule
  is arbitrary and unavailable, disclose it or relax the test. If it is
  evidence-supported, do not turn a solver miss into a new hint automatically.

Copyable prose skeleton (lists are also allowed when natural; ≤300 words):

> The program at `<path>` should `<objective, one sentence>`. It reads `<input>` from
> `<source>` and writes `<output>` to `<destination>`. Its behavior follows
> `<NAMED STANDARD>` exactly; treat that standard as the definition of correct behavior.
> `<One or two sentences for any tested edge an agent would miss, e.g. "a leading UTF-8
> BOM must be accepted and silently ignored">`. Build it with `<cmd>`; the output must be
> exactly `<format>` and nothing else.

Binary preflight (every box YES before running the check):

- no reference-manual heading tree, nested lists, or tables; any flat list has
  at most 20 items and states requirements rather than solution steps;
- no step-by-step algorithm, no function signatures / struct-field dumps;
- no "pay attention" / "note that" / "make sure" hint phrases; no PR/issue/test-name/rubric leakage;
- ≤ ~300 words of flowing prose;
- every arbitrary exact value/constant and public schema element appears in the
  instruction or a realistic visible source; evidence-derived edges need not be enumerated;
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

Before finalizing, run a V3 contract/evidence/test audit:

- list every exact string, flag, command, file path, output key, schema field,
  arbitrary constant, and representation guarantee asserted by tests; make
  these explicit when no realistic evidence defines them
- map semantic tests to one or more evidence/inference families instead of
  copying their derived rules into `instruction.md`
- state public preservation scope explicitly; keep held-out values, layouts,
  and sequences hidden when they exercise the same inferable invariant
- remove or relax tests that require oracle-only policy or unobtainable facts
- keep implementation symbols out of the prompt unless they are public API
- distinguish two kinds of things a test can pin (docs: prompt-styling.md gives
  the what not the how; `behavior_in_task_description` + `structured_data_schema`
  want asserted behavior and output schemas explicit; prompt-styling section 4
  "Overly Prescriptive Guidelines" calls listing exact function signatures /
  struct layouts BAD):
  - OUTPUT/INTERFACE VALUES (paths, keys, public schema, arbitrary thresholds,
    exact-match constants) must be explicit unless a realistic visible source
    defines them. A threshold derived from supplied data/config/domain evidence
    belongs in an inference family and need not be handed over as the answer.
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
- Keep every Dockerfile compatible with the cloud image builder:
  `COPY --chown=` must use numeric IDs (such as `0:0` or `1000:1000`), and
  external-image `COPY --from=` refs must be digest-only
  (`image@sha256:<digest>`, never `image:tag@sha256:<digest>`). Stage aliases
  remain valid, and `FROM image:tag@sha256:<digest>` remains required.
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

### Hardware / CAD verifier rules

Apply `docs/creating-tasks/cad-task-guidelines.md` in addition to the general
rules. Every dimension and repeated/through feature stated in the instruction
needs a geometry check that can actually observe it. Prefer direct B-Rep
measurement, invariants, symmetric difference, or functional checks; a sampling
bracket is only a measurement when its spacing is finer than the tolerance.
Measure the Oracle's built solid rather than trusting source constants, and
prove free pose/construction choices do not fail. When parametric behavior is
required, set a fresh driving value, recompute, assert no errors, and measure
the changed solid; reading a stored parameter back is insufficient.
- Expose enough individually reportable semantic resolution for the chosen
  verifier profile: 50–1000 meaningful units across at least six clusters for
  cheap deterministic tasks, or 20–80 scenarios across at least four clusters
  for expensive stateful tasks. Include at least two units that combine
  clusters and at least two verifier shapes. Do not count repeated fixtures as
  new mechanisms.
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
- Run every candidate-controlled build and runtime command as an unprivileged
  user distinct from the pytest/reward owner. Treat an agent-editable Makefile,
  package script, compiler wrapper, imported module, and produced binary as
  untrusted code. Copy source into a candidate-owned scratch directory before
  building; never grant the candidate write access to `/tests` or
  `/logs/verifier`. Reward-directory mode `0700` does not protect against a
  candidate that also runs as root.
- If privilege is dropped with `setpriv`, include `--no-new-privs` (or use an
  equivalent nosuid boundary). A UID/GID change alone can be undone by a
  candidate-supplied setuid executable. Keep every golden and hidden fixture
  outside directory trees passed to the candidate process and verify that the
  demoted process cannot read them or `/logs/verifier`; write protection does
  not prevent adjacent-directory reads.
- Execute every untrusted candidate in a fresh process group/session. On timeout
  and after normal completion, kill and reap the whole group so forked children
  cannot keep capture pipes open, survive into later cases, or touch verifier
  state. A direct `subprocess.run(..., capture_output=True, timeout=...)` without
  descendant cleanup is not acceptable isolation.
- Grade every promise in `instruction.md` and agent-visible normative documents.
  Map derived semantic checks to V3 inference families rather than restating
  them as prompt promises. An output-write failure promise needs a
  sentinel-preservation test, and a serialized key-order promise needs a
  raw-order assertion when order is genuinely part of the consumer contract.
- Invoke every documented command and mode in at least one discriminating test.
  Put the rule's hard instance in that test: a documented path merely named by
  the suite, or exercised only on a degenerate case where the rule cannot
  matter, is not covered.
- Prove that the verifier rejects a deliberately wrong, incomplete, or lazy
  solution before submission. A green Oracle proves executability, not
  rejection power. The semantic-coverage mutation campaign is the stronger
  local form of this portal requirement; keep at least one wrong-solution
  execution even outside Advanced+ campaigns.
- For every domain rule explicitly named by the contract, include an isolating
  fixture whose expected result changes when that rule alone is inverted. One
  coarse mutant that violates several rules is insufficient, and held-out data
  must not be the only enforcement of any stated rule.
- Bake goldens and held-out fixtures into the separate verifier image. Never
  derive expected truth from `/app`, a mutable corpus, or another agent-writable
  tree, and do not manually copy whole agent directories where symlinks can
  expose verifier-owned fixtures. Declare exact artifact paths and let the
  harness transfer them.
- Match assertion specificity to the written contract. Exact comparison is
  correct for byte-exact/pinned output and wrong for undocumented formatting.
  Enforce any stated numeric tolerance exactly, and add a discriminating case
  for every specified optimization objective or tie-break.
- If verifier Python temporarily changes interpreter permissions, resolve every
  target with `Path.resolve()`, deduplicate before recording original modes,
  wrap changes and test work in `try/finally`, and restore each target once
  while attempting all restorations. In particular, `/bin/bash` and
  `/usr/bin/bash` may be the same executable. Confirm the complete Oracle run
  still finishes reward and log collection; platform preflight
  `verifier_interpreter_permissions` is blocking and is not in `stb harbor check`.

Before submission, review the exact task against all four quality-panel axes:
`coherent_contract`, `correct_reference_solution`, `protected_ground_truth`,
and `sound_verifier`. `Minor`, `Major`, and `Unsure` all block or require human
routing; only `None` on every axis auto-accepts. Exact grading conventions need
a citable candidate-visible authority, but this does not require inferred
domain mechanisms to be restated when distributed visible evidence supports
them under the Terminus 3 epistemic contract.

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
```

Do not use `set -e`; pytest failure must reach the reward block. The trailing
`exit 0` is forbidden: end on the reward block's `fi` so pytest failure still
writes reward 0, while a failed reward write surfaces as infrastructure error.
If the published Terminus 3 skeleton differs, the skeleton wins.

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
- Be checked independently against the visible specification on hard or edge
  inputs not used to tune the fixtures. Oracle=1 is necessary but does not prove
  the reference is correct when the verifier's answer key was derived from it.

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
  copies `/tests`, creates artifact landing directories, and all Dockerfiles use
  numeric `COPY --chown=` IDs plus digest-only external-image `COPY --from=` refs
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
in `.agent/skills/task-revise-flag-remediation/SKILL.md`: classify infrastructure,
oracle/verifier defects, explicit-contract gaps, evidence-inferability gaps,
and legitimate semantic misses before changing prose or cases.
