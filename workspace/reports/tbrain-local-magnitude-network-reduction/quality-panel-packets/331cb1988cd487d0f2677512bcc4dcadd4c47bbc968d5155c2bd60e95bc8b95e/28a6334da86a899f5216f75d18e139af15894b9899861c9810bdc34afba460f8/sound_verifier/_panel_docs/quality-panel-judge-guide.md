# Quality Panel Judge Guide

The quality panel reviews your Terminus 3 task before difficulty is measured and before human review. It checks whether the task is clearly specified, your reference solves it, grading rewards the right behavior, protected answers stay protected, and repeated grading is stable.

This guide is for **expert contributors writing and revising tasks**. Start with the result table if you have feedback to address; use the five checklists before submitting. The [worked examples](/portal/docs/testing-and-validation/quality-panel-examples) show realistic failure patterns, repairs, and checks. They are illustrative composites, not published contributor submissions or recorded judge runs.

> **Updated panel:** five axes, numbered findings, and execution evidence when a defect is reproduced. Read **Blocking severity** as well as **Overall severity**: a `protected_ground_truth` Minor and findings explicitly marked `Advisory` do not block by themselves. An unfinished review is not a confirmed task defect.

<div id="1-how-the-review-works"></div>

## How the review works

Two models independently review each axis. For contract, reference, and verifier review, the panel first lists the contract's requirements and checks them one by one against the relevant files. Findings include evidence and file citations. A third model adjudicates different severity ratings. The report presents the reasoning behind the resulting verdict; it does not necessarily show every model's separate review.

For flagged reference, verifier, or ground-truth issues, an additional execution step can test the claim with the task's own grader. A proven defect receives `Major`. Read the [execution evidence section](#what-execution-evidence-proves) for what those results establish.

| Axis shown in the report | What it asks | Findings that block |
|---|---|---|
| [`coherent_contract`](#axis-1--coherent_contract) | Can a candidate determine every rule used to grade the task? | `Minor`, `Major` |
| [`correct_reference_solution`](#axis-2--correct_reference_solution) | Does the reference satisfy the documented task? | `Minor`, `Major` |
| [`protected_ground_truth`](#axis-3--protected_ground_truth) | Can candidate code obtain or control the answer the grader trusts? | `Major` only |
| [`sound_verifier`](#axis-4--sound_verifier) | Does grading reject wrong solutions and accept contract-valid ones? | `Minor`, `Major` |
| [`deterministic_execution`](#axis-5--deterministic_execution) | Does the same submission receive stable grading on repeated runs? | `Minor`, `Major` |

The reviewers receive different views of your package on purpose. Contract, ground-truth, and verifier review use the candidate-visible contract/environment and the tests, without the reference solution. Reference review uses the contract/environment and reference, without the tests. Determinism review can inspect all three. Agreement between your reference and your tests is useful evidence, but both can agree on the same mistake.

### Read the result before making changes

| Result | Meaning and next action |
|---|---|
| `None` | No defect found on that axis. This is not a guarantee that every possible defect was ruled out. |
| `Minor` | A narrower issue. Address it on contract, reference, verifier, or determinism; on ground-truth protection alone, it is reported without blocking. |
| `Major` | A serious, concrete defect under that axis's criteria. It blocks on every axis. Read the evidence and repair or contest the specific claim. |
| `Advisory` | A recommendation explicitly excluded from the blocking decision. For example, a requirement may have only one easy case exercised, without a demonstrated incorrect outcome. |
| `Unsure` / `not finished` | No decisive result for that axis. It does not itself count as a blocking defect, and it does not mean the axis passed a completed review. |

**Overall severity** summarizes the axis ratings; **Blocking severity** applies the thresholds above. For example, `Overall severity: Minor` with `Blocking severity: None` is possible when the only issue is a ground-truth Minor. Passing the quality panel lets the task continue to the remaining evaluation stages; it does not mean the task has been accepted by a human reviewer.

`PANEL INCOMPLETE` means some review work did not finish. Findings on axes that did finish can still block. `PANEL DEGRADED` means a configured reviewer was replaced or lost; the report may still contain a usable decision and explain when it rests on a single review. If evaluation is stuck or reports an execution error, provide the submission identifier and report to support. Do not change a valid requirement just to address a model timeout. See [After Submission](/portal/docs/submitting-tasks/after-submission) for the rest of the workflow.

## Reading and responding to feedback

Read **every numbered finding** in the displayed report. One axis can contain several distinct issues; fixing the opening paragraph's example may leave another finding unresolved. Findings marked `Advisory` are separate from the blocking findings.

This shortened, illustrative excerpt shows the report's structure. The paths, line numbers, and rewards below are examples, not a recorded run:

```text
Overall severity: Major
Blocking severity: Major

[sound_verifier] Major
  Exploit proven by execution: the grader accepted a submission that returns a constant report for every input (reference reward 1.0, mutated reward 1.0).
  The verifier accepts a fixed report without processing the supplied transactions.

  Findings (1):
    1. (Major) [4] A fixed report passes without processing new transactions.
       The contract requires aggregating the supplied CSV, but every graded run uses the same rows.
       Cited: instruction.md:12-16, tests/test_outputs.py:40-58
```

The actionable claim is that the grader accepts a fixed answer for an input-dependent task. In that excerpt the aggregation rule **is** the task, so the right move is to back it: add distinct inputs whose correct totals differ and check the complete required result. Then show that the reference still passes and that the fixed-answer implementation fails. More assertions about the original CSV alone would not establish that the program processes new inputs. If the flagged behavior had been extra scope the task did not need, removing that promise would have been equally valid — see [Decide before you add](#decide-before-you-add).

### Decide before you add

A finding is not a to-do to grow the task. It means a promise you made is not backed, or a test does not check what it claims to check. Ask first whether that feature belongs in the task at all.

> **Does this thing earn its place in the task?**

Two responses are equally valid:

- **Make it true.** If the behavior is core to what you are testing, fix the contract, the reference, and an isolating case — even if that is work. Named domain rules that remain in the instruction still need isolating cases; see [Writing Tests](/portal/docs/creating-tasks/writing-tests).
- **Stop promising it.** If it is not core, delete the instruction sentence, the matching tests, and any extra modes. The finding goes with the promise.

Contesting with evidence remains valid when the citation does not support the claim; see [Defending Your Submission](/portal/docs/reviewing-tasks/defending-your-submission).

This is intended, not a workaround. The panel enforces every promise you make. We want the high-level behavior that matters to be correct and well-defended, not exhaustive coverage of extra edges. Hundreds of tests accumulated across revisions are a symptom of the add-only loop, not a quality bar.

**Cut breadth. Keep the hard thing.**

The **hard thing** is what [`difficulty_explanation`](/portal/docs/understanding-tasks/task-components) already asks for: the expert crux — domain judgment, interacting constraints, diagnosing a plausible-wrong result. See [Designing for Expert Reasoning](/portal/docs/understanding-tasks/difficulty-guidelines#designing-for-expert-reasoning). Named rules that *are* that crux stay.

**Breadth** is a promise whose removal would not change that crux: extra lifecycle modes, extra error catalogs, extra output formats, extra independent edges the problem was never about.

Heuristic: if a competent solution of the hard thing would still be a correct task after this sentence is deleted, it is breadth. If deleting it would make `difficulty_explanation` false, keep it and back it.

**Do not cut into difficulty.** New submissions must still fail at least 3 of 8 solver runs. If a cut drops the task under that gate, do not re-add independent promises. Deepen the remaining crux — harder instances of the same rules, interacting constraints, hidden inputs of those rules. See [Making a Task Harder](/portal/docs/understanding-tasks/difficulty-guidelines#making-a-task-harder--and-what-doesnt-work). Trimming until solvers pass 6–8 of 8 swaps a panel failure for the difficulty gate.

**Signs you are in the add-only loop:** hundreds of tests; findings that move from one axis to another each round; ten or more rounds without clearing. As of 22 Sep 2026, tasks in that pattern did not converge: pass rate by round went from about 2% at round 1 to about 13% at round 20. If you are stuck, try the reverse: take the flagged non-core promise out, then see what the next panel run says. A worked cut is in [E-3](/portal/docs/testing-and-validation/quality-panel-examples#e-3--remove-a-non-core-promise).

For each finding:

1. **Read the cited files in the submitted version.** Identify the requirement, the affected behavior, and the evidence supporting the claim.
2. **Decide: keep or cut.** If it is the hard thing, keep it. If it is breadth, remove the promise and its tests. If the citation is wrong, contest it.
3. **If you keep it, construct the smallest relevant case.** For a verifier issue, show an incorrect submission accepted or a contract-valid submission rejected. For a reference issue, show the input and the expected versus actual output.
4. **Repair the responsible component, or drop the non-core promise.** Clarify a genuinely missing rule, fix incorrect reference logic, or correct the grader. If you keep the behavior, back the intended crux; do not add extra promises to silence the panel.
5. **Verify both sides.** The correct solution must pass; the specific wrong behavior must fail. Keep the input, output, command, and result so the reviewer can reproduce your conclusion. After a cut, confirm Oracle still passes and the remaining named rules still have isolating cases.
6. **Summarize each resolution.** State the finding, whether you backed it or removed it, the changed files, and the evidence. If you dispute a finding, provide the same level of detail and post it in [`#terminus-3-submissions`](https://snorkel-team.enterprise.slack.com/archives/C0BLQ26GN2W), not only in your revision note — the panel does not read the note.

### What execution evidence proves

Execution evidence connects a finding to an observed result from the task's own grader. It can appear for three kinds of claim:

| Report wording | What was observed | What to investigate |
|---|---|---|
| `Exploit proven by execution` | A submission with the described defect was accepted. In a full-credit example, both reference and altered submission earn `1.0`. | Which required behavior or answer-protection boundary the grader failed to enforce. |
| `Defect proven by execution` | The grader rejected a submission described as contract-valid. For example, the reference earns `1.0` and a valid alternative earns `0.0`. | Whether the grader enforces an undocumented restriction, ordering, format, or implementation choice. |
| `Reference failure proven by execution` | The shipped reference was not accepted by the task's own grader. | The reference, declared artifacts, contract, and verifier together. A failed reward alone does not identify which one is wrong. |

A proof may raise an axis from `Minor` to `Major`. It demonstrates the tested behavior, not exhaustive coverage of the entire task. If the claimed contract validity or reachability is wrong, you can still contest it with evidence.

**No execution line does not clear a finding.** A defect can be established by reading the files. An unsuccessful or unfinished reproduction leaves that finding unchanged, and those attempts are not displayed as proof. Contract and determinism findings do not use this execution stage. You still need the normal [Oracle](/portal/docs/testing-and-validation/oracle-agent), [NOP](/portal/docs/testing-and-validation/nop-agent), and [CI checks](/portal/docs/testing-and-validation/ci-checks-reference).

### When a Previous review section appears

If the previous verdict was supplied to the new review, the report can carry earlier findings forward as `P1`, `P2`, and so on. This section is conditional; its absence does not mean an old finding was resolved.

| Status | How to read it |
|---|---|
| `closed` | The reviewing model or models consider the earlier finding addressed. |
| `STILL OPEN` | At least one reviewing model still identifies the issue. Check the current finding and cited files. |
| `not_a_defect` | The earlier claim was rejected on reinspection. |
| `mixed` / `unanswered` | The history did not get a single resolved answer. These labels alone do not prove that your repair failed. |

These are statuses of earlier findings, not replacements for the current axis verdicts. A revision can close an old issue and uncover a different one. Include a short, explicit response to each earlier finding in your revision notes; see the [worked response example](/portal/docs/testing-and-validation/quality-panel-examples#e--responding-to-a-review).

---

<h2 id="axis-1--coherent_contract">Axis 1 — <code>coherent_contract</code></h2>

**The question:** could two competent people follow the available instructions and produce different answers that your grader scores differently?

Common gaps include unstated tie-breaks, rounding rules, boundary behavior, output paths, or conflicting sources of truth. A hidden fixture can supply a new input; it cannot be the only place that defines what makes an answer correct. A specific candidate-visible file may define a rule when the contract identifies it as authoritative and it fully determines the graded behavior.

**Before submitting:**

- [ ] For every grading rule, identify the sentence or authoritative candidate-visible artifact that defines it.
- [ ] Specify the permitted input domain and the behavior at **boundaries the task actually needs**. Extra promised edges (every invalid input, every lifecycle mode) become new findings; see [Decide before you add](#decide-before-you-add).
- [ ] Compare the rendered `instruction.md`, declared artifacts, and verifier output paths. Remove broken template text and accidental test sentinels.
- [ ] Confirm that examples support the stated rules. If inferring a rule is explicitly the task, check that the available examples determine the intended result.

**Example:** a payment reconciliation task asks for the "latest transaction" but never defines how equal timestamps are resolved. If the grader requires the larger sequence number, disclose that tie-break and include a case where it changes the result. See [contract examples](/portal/docs/testing-and-validation/quality-panel-examples#a--contract).

<h2 id="axis-2--correct_reference_solution">Axis 2 — <code>correct_reference_solution</code></h2>

**The question:** does `solution/solve.sh` and the code it produces actually satisfy the contract, including its boundary cases?

An Oracle pass shows that the reference passes your current tests. It cannot establish a requirement those tests never check. Watch for stale loop state, reused identifiers treated as unique, lost precision, incorrect tie-breaks, and crash-recovery steps performed in the wrong order.

**Before submitting:**

- [ ] Trace at least one ordinary case and each relevant boundary through the actual reference logic.
- [ ] Check output bytes for required widths, precision, padding, delimiters, and paths.
- [ ] Check every branch that updates state, including deletion, expiry, replacement, and identifier reuse.
- [ ] Verify that recovery and durability claims hold at the documented interruption points.

**Example:** a fixed-width banking export requires an eleven-digit field. The reference copies a ten-digit input unchanged, and its goldens repeat the error. Pad according to the contract, regenerate the expected outputs, and assert the field width. See [reference examples](/portal/docs/testing-and-validation/quality-panel-examples#b--reference).

<h2 id="axis-3--protected_ground_truth">Axis 3 — <code>protected_ground_truth</code></h2>

**The question:** can candidate-controlled code obtain or change what the grader treats as the expected answer, earning credit without doing the task?

The evidence must connect something the candidate controls or can access to a trusted grading decision. A golden file existing under `tests/` is normal; a candidate process being able to read that golden and return it as its answer is a defect. A `Major` blocks; a `Minor` on this axis is reported without blocking by itself.

**Separate verifier containers do not protect goldens from candidate code executed inside the verifier.** If your tests rebuild and run the submitted program, check what that process can read and write. Dropping its privileges only helps when the resulting permissions and process restrictions enforce the boundary.

**Before submitting:**

- [ ] Keep expected answers and live reference implementations inaccessible to candidate code, including code your verifier executes.
- [ ] Check privileged reads of candidate-influenced paths for symlink and path-traversal escapes.
- [ ] Compute expected values independently of the submitted artifact. A candidate-provided checksum cannot certify that artifact's correctness.
- [ ] Avoid exposing hidden outcomes through filenames, arguments, working directories, or environment variables.
- [ ] Keep grading results in a trusted channel; candidate stdout or an early successful exit must not impersonate completed verification.
- [ ] Test the access boundary from the same execution context as the candidate program. Confirm another test really defeats a suspected shortcut before treating it as harmless.

**Example:** a document classifier is passed `/fixtures/reject/case-07/input.json`. The path reveals the expected label before the program reads the document. Use neutral paths, vary the inputs, and verify that a label-from-path stub cannot pass. See [verifier and ground-truth examples](/portal/docs/testing-and-validation/quality-panel-examples#c--verifier) and [Writing Tests](/portal/docs/creating-tasks/writing-tests).

<h2 id="axis-4--sound_verifier">Axis 4 — <code>sound_verifier</code></h2>

**The question:** does the grader distinguish solving the documented task from plausible wrong behavior, while accepting valid alternatives?

Both directions matter. A report that merely exists may contain wrong totals; an exact string comparison may reject correct JSON with a different key order. Findings need a concrete mechanism. Advice to exercise more cases is different from showing that a required behavior is never tested or that the tests enforce the wrong behavior.

**Before submitting:**

- [ ] Map each required behavior to an assertion that would fail if that behavior were missing or reversed.
- [ ] Check the full core result: values, membership, uniqueness, and required outputs, not just file existence, keys, or row count.
- [ ] For each named domain rule, include a case whose outcome changes when that rule is wrong. General held-out variation must not be its only check.
- [ ] Try a plausible incorrect solution, such as ignoring reversals or rejecting every request. Confirm the verifier rejects it.
- [ ] Try contract-valid alternatives for unconstrained formatting, ordering, and implementation choices. Confirm the verifier accepts them.
- [ ] Enforce documented restrictions and lifecycle behavior, including failure handling, cleanup, and recovery when required.

**Example:** a financial aggregation grader checks that every account appears but never compares balances. A program writing zero for each balance passes. Add independently calculated expected balances and a case that isolates reversal handling. See [verifier examples](/portal/docs/testing-and-validation/quality-panel-examples#c--verifier).

Findings explicitly marked `Advisory` can recommend broader coverage without blocking. That label does not excuse an actual incorrect result or change the authoring requirements in [Writing Tests](/portal/docs/creating-tasks/writing-tests).

<h2 id="axis-5--deterministic_execution">Axis 5 — <code>deterministic_execution</code></h2>

**The question:** if the submission and task package stay the same, can an uncontrolled input or race change the grade?

Look for fresh random seeds, the current date or time, mutable remote data or dependencies, filesystem ordering, and timing assumptions. The issue is their effect on the graded result. A random temporary filename that cannot affect grading is different from a fresh random test corpus that sometimes exposes a bug and sometimes misses it.

**Before submitting:**

- [ ] Use fixed test fixtures or an explicit, stable seed for generated cases. Make important boundary cases guaranteed fixtures.
- [ ] Fix the evaluation clock when the task uses expiry dates or time windows.
- [ ] Pin dependencies and provide required inputs locally, following the task's environment requirements.
- [ ] Sort where the contract requires order; accept equivalent orderings where it does not.
- [ ] Wait for a defined readiness condition instead of assuming a short sleep is sufficient.
- [ ] Grade the same correct and deliberately incorrect submissions repeatedly from clean environments and check that their outcomes stay stable.

**Example:** an invoice parser's hidden generator chooses a new random seed on each run. A parser that mishandles leap days passes whenever no leap-day invoice is drawn. Use a fixed corpus that always includes the leap-day case, plus seeded variation. See the [deterministic execution examples](/portal/docs/testing-and-validation/quality-panel-examples#d--deterministic-execution).

## Master pre-submission checklist

1. **Contract:** every graded rule is available to the candidate and determines the expected behavior.
2. **Reference:** the shipped solution follows those rules, including relevant edge cases and exact output requirements.
3. **Ground truth:** candidate code cannot read, replace, or impersonate the grader's trusted answer or verdict.
4. **Verifier:** correct alternatives pass, and a plausible solution violating each core requirement fails.
5. **Determinism:** the same package and submission receive stable grading from clean runs.
6. **Evidence:** retain Oracle, NOP, CI, and targeted regression results. Passing those checks does not replace reviewing the contract and assertions.

## FAQ

**Does every Minor block?**

No. `Minor` blocks on contract, reference correctness, verifier soundness, and deterministic execution. Ground-truth protection blocks only on `Major`. A finding explicitly separated as `Advisory` does not contribute to the blocking result. Use the report's `Blocking severity` and the evaluation status.

**What if I think a finding is wrong?**

Quote the exact requirement, the cited implementation or assertion, and the concrete input or output that resolves the disagreement. If the finding assumes candidate access, show the actual staging and permissions. If it assumes an allowed input, check that input against the documented domain. Include a reproduction where useful; an Oracle pass alone does not disprove a coverage gap. See the [worked response](/portal/docs/testing-and-validation/quality-panel-examples#e--responding-to-a-review) and [Defending Your Submission](/portal/docs/reviewing-tasks/defending-your-submission).

**Should I resubmit unchanged until the panel passes?**

Model judgments can vary. Address a supported finding, or when you disagree, post your evidence in [`#terminus-3-submissions`](https://snorkel-team.enterprise.slack.com/archives/C0BLQ26GN2W) — the panel does not read revision notes. See [Defending Your Submission](/portal/docs/reviewing-tasks/defending-your-submission). A different rating on an unchanged task does not explain or repair the original issue.

**Does fixing the listed findings guarantee the next panel pass?**

No. Each resubmit is a **new** review. Closing one issue can uncover a different one, especially if you added surface to satisfy the last report. Act on **Blocking severity**; do not rewrite the whole prompt to chase `Advisory` nits, and do not add tests or promises only to silence the panel. Make a core finding true, or stop promising a non-core one — see [Decide before you add](#decide-before-you-add). Contest unsupported findings with evidence.

**Can I delete the behavior the finding is about?**

Yes, when it is not the hard thing. Remove the instruction, the matching tests, and any extra modes. Named rules that remain must still be backed. The task must still fail at least 3 of 8 solver runs; if a cut makes it too easy, deepen the remaining crux rather than re-adding independent promises. See [Difficulty Guidelines](/portal/docs/understanding-tasks/difficulty-guidelines).

**Does `Unsure` mean I must rewrite the task?**

No. It means that axis has no decisive result, not that a defect was established. Check the other axes and the evaluation status. An evaluation with no readable result may require a retry or support; a readable partial report may already contain actionable findings. No automatic human-routing outcome is implied by this label.

**Does execution prove the whole task is correct?**

No. It tests a particular claim. A reference failure shows disagreement with the grader; an accepted wrong submission shows a gap on the exercised path. Neither replaces reviewing the other requirements. Absence of an execution proof does not dismiss a supported finding.

**Will every revision show Previous review?**

Only when the earlier verdict is available to that review. Keep your own finding-by-finding revision notes. If the section is absent, do not treat earlier findings as automatically closed.

**Is this the same as CI, Agent Review, or human review?**

No. The panel evaluates task quality and gates the difficulty stage according to the thresholds above. Static CI checks, Oracle/NOP runs, Agent Review, difficulty measurement, and the human [Reviewer Checklist](/portal/docs/reviewing-tasks/reviewer-checklist) serve different purposes. A panel pass is one part of submission review.
