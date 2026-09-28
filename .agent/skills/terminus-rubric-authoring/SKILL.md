---
name: terminus-rubric-authoring
description: Author or review Terminus 3 platform rubrics for a task folder or exact submission ZIP. Use when criteria must cover the full agent-visible contract, map to discriminating verifier witnesses, avoid unsupported claims and double penalties, and read like task-specific engineering judgments instead of a repeated scoring template. Review-only unless the user explicitly asks to edit the rubric.
---

# Terminus Rubric Authoring

Build the rubric from the task's contract and evidence, not from a preferred number
of positive or negative lines. The rubric is a platform UI artifact stored locally in
`workspace/submissions/SUBMISSION-<slug>.md`; never put it in the task ZIP. The packet holds only the title `# SUBMISSION — <slug>` with one-line Task, Category and ZIP entries, then `# Relevant Experience`, `# Metadata` and `# Rubrics`; the explanations stay in `task.toml`, so this skill writes no explanation sections.

## Workflow

1. Fix the review target. For a ZIP, inspect a full extraction of that exact archive;
   do not substitute a workspace task with the same slug. Read `instruction.md`, all
   agent-visible contract documents, the public interfaces, and the verifier cases.
2. Build the contract-witness matrix described in
   [references/contract-witness-matrix.md](references/contract-witness-matrix.md).
   Include every requested output, public field, state transition, error behavior,
   preservation promise, supported mode, and important interaction.
3. Require a discriminating witness for every contract row. A test name, comment,
   easy fixture, or value merely emitted by the driver is not a witness. If a row is
   uncovered or only partially covered, report the task/verifier gap and do not hide
   it by narrowing the rubric. Editing the task or verifier requires explicit user
   authorization.
4. Group covered rows into independently judgeable semantic criteria. Use separate
   criteria when a partial implementation can satisfy one behavior without the
   other. Keep an interaction together only when its witness genuinely exercises
   the combined behavior.
5. Derive negative criteria from distinct, observable failure modes or shortcuts.
   Do not force a fixed count. One negative line is fine for one coherent failure;
   several independent corruption or shortcut modes deserve separate lines. Avoid
   deducting twice for the same root failure merely because its positive criterion
   was not earned.
6. Assign scores from `+1`, `+2`, `+3`, `+5`, `-1`, `-2`, `-3`, and `-5`. Positive
   points must total 10–40 and at least one negative criterion is required. Weight
   architectural correctness, data integrity, and required interactions above
   minor compatibility or polish.
7. Write each criterion as one physical line beginning with `Agent`. Name the
   observable behavior, concrete API/state/artifact, and important boundary when it
   helps distinguish a partial fix. Never mention tests, hidden checks, pytest,
   verifier internals, rewards, or implementation-only source shape.
8. Perform a cold style pass. Vary verbs, sentence length, clause shape, criterion
   count, negative count, and score distribution according to this task's topology.
   A portfolio that repeatedly ends with one catch-all `-5` is a warning even when
   every individual file passes policy. Do not vary prose by adding unsupported
   facts.
9. Run the mechanical checker:

   ```bash
   python3 .agent/skills/terminus-rubric-authoring/scripts/check_rubric.py \
     workspace/submissions/SUBMISSION-<slug>.md
   ```

   Pass several packets together to detect repeated portfolio topology. Treat
   mechanical warnings as review prompts, not automatic rewrite orders.

   In `task-batch`, also bind the completed matrix and current packet into the
   handover receipt:

   ```bash
   python3 .agent/skills/terminus-rubric-authoring/scripts/check_rubric.py \
     workspace/submissions/SUBMISSION-<slug>.md \
     <accepted-portfolio-submission-files...> \
     --coverage-matrix workspace/reports/<slug>/rubric-coverage.md \
     --output workspace/reports/<slug>/rubric-check.json
   ```

10. Re-read every final criterion against the matrix. Report one of:
    - `ready`: every contract row has a discriminating witness and rubric coverage;
    - `rubric-ready, task-blocked`: the prose is valid but task/verifier gaps remain;
    - `not ready`: rubric format, leakage, scoring, overlap, or coverage still fails.

## Seeded-departure repair tasks (accepted shape)

Six platform-accepted repair tasks used 12–16 lines with one shape, adapted per
task rather than copied:

- one positive line per departure group (usually `+2`), naming the book's rule and
  the behaviour, not the file;
- one line per counted restraint trap (usually `+3`), naming the silent input in
  the book's domain words and the shipped behaviour kept;
- one line for code already right under the book that an expert might "improve"
  (a rounding rule, a remembered textbook formula) when a wrong path tests it;
- `+1` for the frozen surface when it is graded;
- one negative line per **named natural over-repair** (`-3`), phrased as the
  concrete wrong fix ("takes the whole turnout log out of the water tested against
  the intake limit"), not "breaks X";
- `-5` for editing the authority or hardcoding figures.

**Regenerate the rubric whenever a trap is dropped, flipped or moved to the
"left entirely open" tier.** A line rewarding behaviour on an input the
instruction now leaves open contradicts the contract: royalty's human reviewer had
to fix two such lines by hand, and rebill's and moving-average's submission notes
still carried rubric lines for dropped traps. Diff every trap line against the
current `fix.patch` and silence clause before each upload.

## Non-negotiable Boundaries

- Rubric prose cannot repair a verifier blind spot.
- A smaller rubric must not conceal an instruction/verifier mismatch.
- Raw test count does not prove semantic coverage.
- Oracle=1 and NOP=0 do not prove that every promised mode is discriminated.
- Network-only or packaging-only task changes do not require rubric rewriting unless
  the observable contract changed.
- In review mode, do not modify the packet, task, verifier, ZIP, or evidence files.
