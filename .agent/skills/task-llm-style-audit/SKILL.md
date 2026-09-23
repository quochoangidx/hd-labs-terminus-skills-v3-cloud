---
name: task-llm-style-audit
description: Use before freezing a counted Terminus probe and again after writing submission prose, or when a reviewer flags LLM-generated writing. Audits task-visible prose first, then external rubric/explanations after probes, preserving technical facts and instruction/test symmetry. Style-only gate; packaging and verifier coverage stay with task-client-feedback-review.
---

# Task LLM-Style Audit

Reviewers now explicitly reject tasks whose prose "reads LLM-generated" — this is a
detection axis on its own, separate from hint leakage. Confirmed returns: June 2026
trial batch ("prompts should not be LLM generated", quality-guidelines.md), and the
2026-07-07 scrabble-clock return where the environment doc was flagged as "too clean,
every section the same shape... write it like a person" and the explanations as
"still 2-3 LLM sentences each, ask was 4-6 real human ones".

Run two phases. Before counted probes, audit every task-tree prose surface and
freeze `task-style-preflight.json`; any rewrite then happens before solver
sessions are spent. After probes, audit only external rubric/submission prose
and write schema-2 `style-audit.json`. A post-probe task-tree edit invalidates
the counted snapshot and returns the workflow to pre-freeze validation.

For `task-batch` under `campaign_ready`, do not create a separate style agent. The consolidated
auditor performs semantic realism, folder/manual review, and this task-tree
style pass in one pre-freeze session, producing three separate receipts backed
by one real transcript/provenance record. Reuse that same auditor identity in a
new post-probe turn for the final submission and ZIP; use a new transcript that
binds the exact final surfaces.

## Surface inventory

Audit every file a human reviewer reads, not just what the agent sees. Build the
inventory first, then score each surface:

| Surface | Where | Extra constraint while rewriting |
|---|---|---|
| Instruction | `instruction.md` | keep every value/threshold the tests assert (symmetry); 1 sentence–3 paragraphs; no emojis, minimal markdown |
| Environment docs | `environment/**/*.md`, specs, READMEs | must read like a real engineering doc (API contract, schema, RFC), never a prompt extension |
| Environment code comments | `environment/**` source | comments must not point at bugs or narrate the fix; when in doubt, delete the comment |
| Rubric text | platform textbox draft / `*-rubics.txt` | flat `Agent ...` lines; vary phrasing across criteria |
| Submission explanations | `workspace/reports/<slug>/submission-explanations*.md` | audit all four fields; keep the three technical explanations distinct and Relevant Experience factual |
| Test/solution comments, Dockerfile comments | `tests/`, `solution/`, `Dockerfile` | reviewer-visible even though agent-invisible; same prose rules |
| Filenames | whole tree | no AI-scaffolding names: `CLAUDE.md`, `AGENTS.md`, `skills.md`, `.cursor/` |

## Structural tells — fix by deletion or relocation, not rewording

These are the tells a reviewer catches at a glance. Rewording sentences does NOT fix
them; the structure itself is the signal. Each fix below is the confirmed remedy.

1. **Environment doc narrates the reduction/algorithm.** A spec that walks the reader
   from problem to solution is a solution guide wearing a spec costume
   (scrabble-clock 2026-07-07: "gives away the whole reduction"). Fix: cut the
   walkthrough entirely. The rules live in code and tests; the doc defines only what
   the schema/protocol/contract IS.
2. **Worked examples that duplicate test fixtures with answers attached.** Both an
   answer leak and an LLM tell (LLMs pad specs with fully-worked examples). Fix:
   replace with input-only examples that are NOT in any fixture, or drop them. See
   memory `agent-facing-examples-must-be-input-only`.
3. **Instruction repeats what the spec/environment already defines** (schema, rule
   list). Reviewers read it as generated filler. Fix: instruction states the symptom
   and the expected output only; delete the repeated material.
4. **Every section has the same skeleton.** Same heading depth, same bullet count,
   same paragraph length, every section ending in the same shape (e.g.
   Overview→Rules→Example ×N). Fix: restructure — merge two sections, turn one into
   a single paragraph, drop a heading, let one section be three times longer than
   its neighbor. Real docs are lumpy.
5. **Balanced lists everywhere.** Every list exactly 3 items, every field explained
   with one bold-label bullet. Fix: fold minor items into prose, leave one list
   ragged.
6. **Explanations written as 2–3 uniform sentences per field.** The ask is 4–6
   sentences that read like a person explaining their own task: concrete file/value
   references, one opinion or aside, different rhythm across the three technical explanations, and
   zero mentions of LLM/AI/model/agent/guidelines (anti-llm rules 16, 18, 20, 21).
7. **Instruction hand-holds discovery that is already trivial** — naming the exact
   file to edit when it is the only source file (scrabble-clock: "main.go is the
   only source file anyway so there is nothing to find"). Fix: drop the pointer.
8. **Reverse-engineered prompt.** A sentence only makes sense if the author already
   knew the fix ("would a real user know this?" — June 2026 trial report). Fix:
   delete the sentence; if the tests then become unfair, the missing value belongs
   in the instruction as a requirement, not as a mechanism narration.

## Prose tells — rewrite with the anti-llm rules

For sentence-level style, apply the `anti-llm` skill's rewrite rules to each risky
surface. The tells that show up most in task returns:

- template openers/closers ("Overall", "In summary", "Note that", "It's important")
- hedging ("slightly", "potentially", "appears to") where the doc should state fact
- em dashes and ` - ` used as em dashes → comma or two sentences (rule 19)
- formal connectors ("furthermore", "additionally", "thus", "moreover")
- LLM vocabulary: "comprehensive", "robust", "seamless", "leverage", "ensure that",
  "delve", "hygiene", abstract nouns instead of concrete references (rule 4, 14)
- 3+ consecutive sentences or bullets opening with the same imperative verb
  (rule 15) — common in rubric drafts where every criterion starts "Agent correctly…"
- identical tone/length/structure across sections and across the three explanation
  fields (rules 11, 17)

Hard constraints during any rewrite:

- Technical facts are frozen: every number, threshold, path, identifier, command,
  and schema field present before the rewrite must survive it byte-identical.
- Never delete a value the verifier asserts (instruction/test symmetry) to make a
  sentence shorter — restyle the sentence around the value.
- Never introduce verifier vocabulary while rewriting: test, verifier, grader,
  reward, CI, pytest, hidden checks.
- Environment docs stay WHAT-only. If a rewrite is drifting toward explaining how
  a rule interacts with another rule step by step, you are re-creating tell #1.

## Procedure

1. Inventory: list every surface from the table above that exists in the task.
2. Score each surface `verified` or `at-risk`, quoting the specific tells found
   (structural tell number and/or anti-llm rule number). Read each doc COLD, top to
   bottom, asking one question: "would I believe a busy engineer typed this?"
3. Fix structural tells first (delete/relocate/restructure), then run the prose
   rewrite on what remains. Structural fixes may shrink files a lot — that is the
   point.
4. Verify each fixed surface before marking it:
   - extract all numbers, paths, identifiers, and commands from before/after and
     diff them — the sets must match (minus content that was deliberately deleted
     as a leak, which you list explicitly);
   - re-check symmetry: every tested value still stated where the docs require it;
   - re-check for newly introduced verifier vocabulary and guideline references;
   - re-read the final text cold once more; if two sections still share a skeleton,
     it is not verified.
5. If any file was deleted, moved, or had examples swapped, re-run oracle and nop.
6. Report.

## Report shape

```text
Task: <name>
Surfaces audited: N

instruction.md            — verified (rewritten: tells #3, rule 15)
environment/spec.md       — verified (deleted reduction walkthrough, tell #1; examples replaced, tell #2)
environment code comments — verified (no changes needed)
rubric draft              — verified (rewritten: rule 15)
explanations (3 fields)   — verified (expanded to 4-6 sentences each, tell #6)

Deleted as leak (listed for the record): <content removed under tells #1/#2/#8>
Re-validation: oracle PASS / nop FAIL (rerun because spec.md examples changed) | not needed
```

Every surface must end `verified` before `task-zip-submit`. If a surface cannot be
made human-sounding without breaking symmetry or fairness, stop and redesign that
surface via `terminus-regular-task-authoring` instead of shipping a compromise.

For `task-batch`, inventory every UTF-8 reviewer-visible task file before the
counted snapshot and generate the schema-1 task receipt after the real audit:

```bash
scripts/python3 .agent/skills/task-batch/scripts/evidence.py task-style-receipt \
  workspace/tasks/<slug> \
  --transcript workspace/reports/<slug>/consolidated-pre-freeze-audit.md \
  --runtime <actual-runtime> --model <actual-model> \
  --session-id <actual-session-id> \
  --output workspace/reports/<slug>/task-style-preflight.json
```

After probes, audit the final external submission and generate schema-2
`style-audit.json`. It hash-reuses the unchanged pre-freeze task receipt rather
than pretending the submission auditor reread every task file:

```bash
scripts/python3 .agent/skills/task-batch/scripts/evidence.py style-receipt \
  workspace/tasks/<slug> \
  --submission workspace/submissions/SUBMISSION-<slug>.md \
  --transcript workspace/reports/<slug>/style-audit-transcript.md \
  --runtime <actual-runtime> --model <actual-model> \
  --session-id <actual-session-id> \
  --output workspace/reports/<slug>/style-audit.json
```

Both commands record hashes; neither performs an audit. Preserve each raw
transcript beside its receipt. Never update hashes without rereading the changed
surface.

## Out of scope (route elsewhere)

- Unpinned git commit dates in the Dockerfile (nondeterministic builds),
  wrong `category`, wrong `difficulty` in `task.toml` → `terminus-regular-task-authoring`
  / `task-client-feedback-review`.
- Verifier blind spots (e.g. fuzzer that only ever generates one player, so
  ownership transfer is never tested) → `terminus-hard-python-verifier` /
  `task-revise-flag-remediation`.
- Packaging, wheels, canary strings, reward-file shape → `task-zip-validator`.
- Reviewer notes you write on OTHER people's tasks → use `anti-llm` directly.
