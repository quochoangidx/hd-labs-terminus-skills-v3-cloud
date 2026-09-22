# Submission Checklist

Run through this before every submission.

---

## Task Design

- [ ] Goal is clear and unambiguous; requirements are inferable from the materials provided
- [ ] Instruction is as concise as the task allows (around 2 short paragraphs or 20 bullets), and not LLM-generated
- [ ] Uses absolute paths (e.g. `/app/output.json`)
- [ ] Output files and formats are specified
- [ ] Not solvable in a single command or a straight-line burst — requires chaining, intermediate state, and reacting along the way
- [ ] Novel — not a variation of an existing task or a reskin of your own earlier work
- [ ] Exactly one `category` and one `subcategory` from the taxonomy
- [ ] No canary strings in any component

## Required Files

- [ ] `task.toml` — all required fields present
- [ ] `instruction.md`
- [ ] `environment/Dockerfile` — builds successfully; dependencies pinned; every `FROM` digest-pinned; `COPY --from=` image refs are digest-only (no `:tag@sha256`)
- [ ] `environment/docker-compose.yaml` (if present) — no top-level or per-service `networks:`, no per-service `network_mode:`
- [ ] `solution/solve.sh` — deterministic, human-written
- [ ] `tests/Dockerfile` — verifier image with dependencies baked in; same `COPY --from=` rule as the environment Dockerfile
- [ ] `tests/test.sh` — verifier entrypoint
- [ ] `tests/test_outputs.py` — Python pytest tests with docstrings

> `rubrics.txt` and `README.md` are added by Snorkel during packaging — you don't ship either. The README is built from your `task.toml` explanation fields.

## Verifier

- [ ] `[verifier].environment_mode = "separate"`
- [ ] `artifacts` is a **top-level** key and lists every path the verifier needs
- [ ] Parent directories for those artifacts exist in the verifier image
- [ ] `solution/` and `tests/` are absent from the agent image
- [ ] Tests are deterministic — no network, no wall-clock dependence, no unseeded randomness
- [ ] Tests check semantics, not appearance
- [ ] Every required output path/name in `instruction.md` is the same path/name the verifier reads
- [ ] Verification covers every stated core requirement and the full required output — values, fields, rows/files, ordering, uniqueness, types, and formatting where required, not just presence or a partial sample
- [ ] Tests vary inputs meaningfully across the stated domain so fixed sizes, values, ordering, paths, formats, or business rules cannot be hardcoded
- [ ] Any stated lifecycle behavior (restart/recovery, idempotency, invalid input, concurrency, existing output, reset) is exercised, not just the happy path
- [ ] `tests/` does not contain a callable end-to-end solver; expected results come from sealed goldens or spec-derived invariants
- [ ] If the task reads a variable config/input, mutate it and re-run to prove the solution does not hardcode the shipped values
- [ ] If source and a built/package/report artifact are both required, tests rebuild from source **and** validate the required delivered artifact and their correspondence
- [ ] Goldens and held-out fixtures are baked into the verifier image (`tests/Dockerfile`), not read from agent-writable paths (`/app`, mutable corpus, agent-delivered trees)
- [ ] If tests rebuild and run the agent's program, drop uid before that exec and probe that it cannot read goldens or `/logs/verifier` — separate mode does not hide those files from that process
- [ ] Agent outputs are declared as top-level `artifacts` in `task.toml` — don't stage agent directories yourself
- [ ] Any numeric tolerance stated in `instruction.md` matches what the tests enforce
- [ ] When the spec defines an optimization objective or tie-break, tests reject a feasible plan that optimizes the wrong quantity
- [ ] Walked all five axes in the [Quality Panel Judge Guide](/portal/docs/testing-and-validation/quality-panel-judge-guide): requirements are disclosed, the reference solution satisfies them, goldens stay protected, wrong solutions fail, and grading is reproducible under the stated environment

## Configuration

- [ ] `[agent].timeout_sec` is at least **1800** (30 min) and reflects the time the task actually needs
- [ ] `[verifier].timeout_sec` and `[environment].build_timeout_sec` set
- [ ] `[environment].network_mode = "public"` — required on every task
- [ ] `[agent].network_mode` and `[verifier].network_mode` are **both present** — single-container tasks use `"public"` or `"no-network"` as needed; Compose tasks must use `"public"` on all three phases
- [ ] No GPU required; runs within ~2 CPU cores, ~8 GB memory, ~10 GB storage
- [ ] Descriptive fields are under `[metadata]`, not at the top level
- [ ] 3–6 `tags`; `languages` and `expert_time_estimate_hours` set
- [ ] `author_name` and `author_email` set (`"anonymous"` is fine)
- [ ] `difficulty_explanation`, `solution_explanation`, `verification_explanation`, and `relevant_experience` written
- [ ] `difficulty_explanation` says why the task is inherently a challenge for a human expert — not the pass rate you measured

## Rubric

- [ ] Rubric generated and edited in the platform submission UI
- [ ] Maximum cumulative score is 10–40 points
- [ ] **At least one** criterion assigns a negative reward
- [ ] Every line starts with "Agent" and ends with `, ±N`; positives carry an explicit `+`
- [ ] Only ±1, 2, 3, 5 used — no 4s
- [ ] Checkbox unchecked before sending to reviewer

---

## Automated Checks

```bash
stb harbor run -a oracle -p <task-folder>
```

- [ ] Oracle agent PASSES
- [ ] `stb harbor check` clean — all errors resolved, warnings fixed unless a reviewer approved an exception

---

## Difficulty Measurement

```bash
stb harbor run -m @openai/gpt-5.6 -p <task-folder> -k 4
stb harbor run -m @anthropic/claude-opus-5 -p <task-folder> -k 4
```

- GPT-5.6 pass rate: ____%
- Claude Opus 5 pass rate: ____%
- **Accuracy** (average across both): ____%

| Tier | Accuracy |
|---|---|
| **Frontier** | < 20% |
| **Advanced** | 20% – < 50% |
| **Core** | 50% – < 80% |
| **Base** | 80% – < 100% |

- [ ] For a new submission, the local 8-run estimate includes at least **3 genuine task-driven failures** — 6–8 passes will not clear the platform gate. Tasks already on the platform by the morning of Sep 11, 2026 remain grandfathered, including later revisions
- [ ] `difficulty` in `task.toml` set to the tier your local runs point at — the platform's own 8-run measurement is what gets recorded, so this is your best estimate, not a value a reviewer checks
- [ ] Failures reflect genuine task difficulty — not unclear instructions, environment defects, or flaky tests
- [ ] **Checked which tests the failing runs miss.** If they keep missing the same one or few tests, the check or the instructions are likely the problem — fix that check, or state the requirement in the instruction. If they miss different tests each time, the difficulty is genuine. Either way, don't leave the difficulty rated higher just because near-complete runs count as failures
- [ ] **Ran a deliberately wrong or incomplete solution against your own verifier and confirmed it fails.** One mutant that breaks several rules at once (including the shipped buggy code) is not enough — for each **named** domain rule, a case should exist that would fail if **that rule alone** were wrong. Held-out must not be the only enforcement of any stated rule.

---

## Self-Check

1. Would a first-time reader understand what is being asked?
2. Can the agent obtain everything it needs from the environment?
3. Could a plausible-but-wrong solution pass my tests?
4. Do my tests check semantics rather than appearance?
5. Is everything deterministic?

---

## Submit

- [ ] ZIP contains the task **files**, not the enclosing folder
- [ ] All required files included
- [ ] Submitted under the **`Terminus-3-Prod`** project

---

## Need Help?

- Slack: [`#terminus-3-submissions`](https://snorkel-team.enterprise.slack.com/archives/C0BLQ26GN2W)
- [Reviewer Checklist](/portal/docs/reviewing-tasks/reviewer-checklist)
- [FAQ](/portal/docs/reference/faq)
