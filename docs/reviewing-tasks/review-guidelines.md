# Review Guidelines

Guidelines for peer reviewers evaluating submitted tasks.

## Reviewer Checklist
As a helpful tool to use while reviewing, we have a comprehensive reviewer checklist that covers all aspects that should be looked at during a review. This includes descritions of what we are looking for qualitatively, as well as assigns a severity level that establishes if an error for a given aspect of a submission should result in an Accept still, or if it always requires the submission to be sent back for revisions when encountered.

**Go to [Reviewer Checklist](/portal/docs/reviewing-tasks/reviewer-checklist)**


## Review Philosophy

As a reviewer, you're ensuring quality for the benchmark. Your goal is to:
- Catch issues before they enter the dataset
- Help contributors improve their tasks
- Maintain consistency across submissions

> **Remember:** Each review you conduct should be comprehensive and catch ALL present errors and issues with the task. Do not simply find the first error you come across and then immediately send it back for revision. Instead, **find all issues** during your review and give feedback on all elements found.

_If the EC addresses your comments, the task should be ready for acceptance, assuming no new issues appear. In other words, your feedback should be always clear, complete, and actionable._

> **A green run is where a review *starts*, not where it ends.** A passing oracle, a clean-looking setup, or a green automated check is *material for* your review — not the review itself. Accept each point because **you confirmed it holds**, not because the eval passed or the doc says so. When your reason to accept is an assumption (the tests cover the contract, the answer's protected, the difficulty fits, the solution matches the spec), do the thing that confirms or breaks it before you sign off.
>
> **Don't repost unverified output as your review.** The Agent Review summary, the quality-check output, the **quality panel** report, and the difficulty trial-analysis are inputs to *help* you review — copying their claims (or an earlier reviewer's notes) back into your review says nothing about whether the task is sound. If you rely on any of it, **verify it first.** Your review should briefly say **what you checked and what convinced you** — "looks solid," a restatement of the design, or "Oracle / NOP / CI pass" is not a review. The [Quality Panel Judge Guide](/portal/docs/testing-and-validation/quality-panel-judge-guide) is written for EC Submitters; treat a panel `Major` as a lead to confirm, not as the review itself.

## Review Checklist

### 1. Read the Task Description

### Authentic Prompt Styling

We have overhauled the way instructions are written. In Terminus 3, the `instruction.md` file should index on **realistic prompts** that real users and engineers would use when interacting with coding agents in their daily life, and be as succinct as possible.

The instructions for every task should adhere to these six general principles:
1. Task instructions **must be concise.**
2. Task instructions **must be well specified.**
3. Task instructions **must be interesting.**
4. Task instruction **must not give answers, hints.**
5. Task instruction **must be unique.**
6. Task instruction **must use absolute paths.**

**Consult the [Prompt Styling Guide](/portal/docs/understanding-tasks/prompt-styling) for further details on each core principle.**

### 2. Review Tests

- [ ] Every requirement has a corresponding test
- [ ] Required output paths/names match between the instruction and verifier
- [ ] Tests have informative docstrings
- [ ] Tests verify behavior, not implementation
- [ ] Tests vary the stated input domain enough to reject hardcoded shortcuts
- [ ] Any stated lifecycle/resilience behavior is exercised
- [ ] Required delivered artifacts are validated, not inferred correct from a separate rebuild
- [ ] No brittle string matching
- [ ] No hardcoded thresholds (or thresholds are reasonable)

### 3. Use the Test-Quality Eval to Double-Check Your Work

There is an automated **test-quality** eval on submissions that flags common gaps so you can double-check. **It is a helper, not a replacement:** still do a full test review, and **verify every flag** — the eval will miss some issues and sometimes flag acceptable tests.

| Flag | Meaning |
|------|--------|
| `req-gap` | Instruction requires something, but no test asserts it. |
| `weak-assertion` | A test exists but is too loose to catch wrong solutions. |
| `phantom-spec` | Tests enforce behavior not described in the instruction. |
| `flaky-execution` | A correct solution can fail due to timing, non-determinism, or infra. |
| `vacuous-test` | Test can pass no matter the output (e.g. empty loops, always-true checks). |

**How to use it:** Complete your normal test review, then go through any eval flags you might have missed.

### 4. Check Solution

- [ ] Solution demonstrates the process (not just outputs answer)
- [ ] Commands are deterministic
- [ ] Works in the provided environment
- [ ] Oracle is correct, not just passing

**Correct, not just passing.** The oracle passing the tests is **necessary but not sufficient**. In practice the tests and the oracle are written together and tuned until the oracle passes, so a passing oracle mainly shows that the task runs, not that the reference is correct. A wrong oracle is worse than a broken one: the tests encode its output as the answer key, so a *correct* agent solution fails verification, and difficulty is measured against a bad truth.

Spot-check the oracle against the **spec**, not against its own tests — independently work out the expected result on a few hard or edge inputs the fixtures don't already cover. Send the task back if the oracle omits a documented requirement, encodes an unsupported assumption, or rejects another contract-compliant implementation. See [Writing Oracle Solution → Correct, Not Just Passing](/portal/docs/creating-tasks/writing-oracle-solution#4-correct-not-just-passing) and the matching High row on the [Reviewer Checklist](/portal/docs/reviewing-tasks/reviewer-checklist#verifiers).

### 5. Verify Metadata

- [ ] Difficulty uses a **current tier name** (`frontier` / `advanced` / `core` / `base`). A retired name (`hard` / `easy` / `medium`) is a finding. Declared vs measured mismatch is not — see *Don't request changes for these*.
- [ ] Category is appropriate
- [ ] Time estimates are realistic
- [ ] Timeout is sufficient but not excessive

### 6. Watch Agent Runs

**Solvable vs. passing a run:** *Passing a run* means all unit tests pass in a single run. *Solvable* (for the task) means that **across the 8 runs**, each individual test passes at least once—so a task can have no full pass in any run and still be solvable if the agent only ever “partially” succeeds.

On the task viewer:
- Watch the terminal recording
- If agent fails, is it failing for a **good reason**?
- Check the analysis for identified issues
- Read the debug pane

### Comprehensive Reviewer Checklist
 - You can also use this [Reviewer Checklist](/portal/docs/reviewing-tasks/reviewer-checklist) for a more comprehensive and detailed checklist

## Common Issues to Flag

### Task Description Problems

| Issue | What to Look For |
|-------|------------------|
| Ambiguous requirements | "Make it better", "fix the issues" |
| Missing output specs | Tests check files not mentioned |
| Relative paths | `./data/file.txt` instead of `/app/data/file.txt` |
| Implicit assumptions | Assumes knowledge not in instructions |

### Test Problems

| Issue | What to Look For |
|-------|------------------|
| Brittle tests | Matching at the wrong specificity — pinning a format the instruction never stated. Exact matching is *required* when the instruction pins the output; see [Writing Tests](/portal/docs/creating-tasks/writing-tests) |
| Missing coverage | Requirements without tests |
| Order dependency | Tests that must run in sequence |
| Implementation testing | Parsing source code |

### Solution Problems

| Issue | What to Look For |
|-------|------------------|
| Hardcoded answers | `echo "42" > result.txt` |
| Passes tests but wrong vs spec | Oracle omits a documented rule, encodes an unsupported assumption, or would reject another contract-compliant implementation |
| Non-deterministic | Uses random without seed |
| Incomplete | Missing steps |
| Over-complex | Unnecessarily convoluted |

## Specific Things to Watch

### Testing Behavior

> It is almost always better to test a behavior by actually running the code than trying to statically analyze it.

**Flag:** Tests that grep through source code looking for patterns.

### Tool Specifications

> Task instructions shouldn't mention specific tools unless there's a way to verify they were used.

**Flag:** "Use vim to edit the file" (can't verify vim was used).

### Randomness

> Tasks involving randomness MUST NOT assume the solution matches that same random order.

**Flag:** Tests that depend on specific `np.random.seed` values.

### Test Complexity

> Long test files are almost always wrong since more tests means more opportunities for error.

**Flag:** test_outputs.py with 20+ tests for a simple task.

### Data Formats

> Be especially paranoid about specifying data formats.

**Flag:** "Output a CSV" without specifying whether it needs headers.

### Anti-Cheating

Think about how agents could cheat:
- Decompile programs to find hidden answers
- Replace programs with dummy versions
- Delete or modify tests
- Access newer git commits

## Review Actions

### Approve

Task is ready. No issues found.

### Request Changes

Issues need fixing before acceptance. Be specific:
- What's wrong
- Where it is
- How to fix it

**Good feedback:**
> The test `test_output_format` on line 45 asserts an exact string, but `instruction.md` never specifies the output wording. Please check the required fields instead, so the test grades what the instruction actually states.

**Bad feedback:**
> Tests need work.

**Extra things you can include**
- Point the submitter where can they found how to fix the issue or a place where they can see they are mistaken

> Check the [Rubrics](/portal/docs/understanding-tasks/rubrics) section in the training site

### Don't request changes for these

These come up often but are **not** valid revision reasons — usually they're unverified Agent Review output copied into a review. Confirm before you send anything back:

- **`task.toml` "is incorrect."** CI runs the structure check on every submission, and a task only reaches you once CI is passing — so the manifest in front of you has already passed it. **Confirm the static check actually fails** before flagging — an Agent Review "toml wrong" is usually a false positive (a common one: flagging fields as "top-level" that are correctly under `[metadata]`).
- **Difficulty value / tier mismatch** (declared `frontier`, measures `core`, etc.). **The measured tier is already final when the task reaches you**, and it is what gets recorded — the declared value is the author's estimate, and a mismatch is not a revision trigger or worth your time. *Still flag:* a **retired tier name** (`hard` / `easy` / `medium` — must be `frontier` / `advanced` / `core` / `base`), or a task that is **genuinely too trivial** (that's a quality issue, not a label).
- **Instruction length** ("too many paragraphs / bullets"). The 2-paragraph / 20-bullet figure is **guidance, not a hard cap** — complex tasks may need more room. Don't flag on length; flag only if the instruction **leaks implementation steps or the answer**.

### Decline

Fundamental issues that can't be easily fixed:
- Too easy (100% accuracy averaged across both models provides no signal; 90% is acceptable, 100% is not). You see all 8 runs, so this is directly checkable — though a task at 100% should not have reached you
- Essentially duplicate of existing task
- Core concept is flawed

Explain clearly why, and whether revision could salvage it.

---

## Next Steps

- [Reviewer Checklist](/portal/docs/reviewing-tasks/reviewer-checklist) — Full high/medium/low acceptance criteria for reviews
- [Reviewer Training](/portal/docs/reviewing-tasks/reviewer-training) — Training videos and materials for reviewers
- [Rubrics](/portal/docs/understanding-tasks/rubrics) — How to write and review rubrics for evaluating agent traces
- [Quality Guidelines](/portal/docs/reference/quality-guidelines) — Required quality standards for all tasks
- [Common errors to watch for](/portal/docs/reviewing-tasks/common-errors)
