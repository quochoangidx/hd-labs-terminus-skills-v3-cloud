# After Submission

What happens after you submit your task, and how to handle feedback.

## Review Timeline

| Stage | Timing |
|-------|--------|
| Automated checks | Begin after submission |
| Quality panel | Before difficulty measurement |
| Difficulty measurement (8 runs) | After the quality panel passes |
| Peer review assignment | After difficulty measurement |
| Initial review | Typically 1-7 business days |
| Follow-up reviews | Typically 1-7 business days |

## Review Process

### 1. Automated Checks

Immediately after submission, your task goes through:
- CI checks (syntax, structure, dependencies)
- LLMaJ checks (quality, completeness)
- **Expertise check** (`difficult`, blocking) — judges whether the task requires genuine domain expertise, independent of its tier. A task that fails here needs deeper domain reasoning, not a lower pass rate. See [Difficulty Guidelines](/portal/docs/understanding-tasks/difficulty-guidelines).
- Oracle agent run
- **Quality panel judge** — five axes on contract, reference solution, protected ground truth, verifier soundness, and deterministic execution. Axis verdicts of `Minor` or `Major` block, except on `protected_ground_truth`, where only `Major` blocks. Findings explicitly marked `Advisory` do not block. A finding is a keep-or-cut decision, not a to-do to grow the task; see [Decide before you add](/portal/docs/testing-and-validation/quality-panel-judge-guide#decide-before-you-add).

`Unsure` or incomplete evidence is not a confirmed task defect. Check the evaluation status and report, requesting support if evaluation remains unfinished. Passing the panel allows difficulty measurement; acceptance still requires the remaining evaluation and human review.

### 2. Agent Evaluation

Once the quality panel passes, your task is run against:
- Claude Opus 5 with Claude Code (4 runs)
- GPT-5.6 with Codex agent (4 runs)

Pass rate across all 8 runs sets the difficulty tier. For a new submission to proceed, at least **3 runs must fail**; no more than 5 may pass. Tasks already on the platform by the morning of Sep 11, 2026, including later revisions of those tasks, retain the prior one-failure gate.

> **This is the only measurement, and it is final.** There is no shorter platform check before it and nothing re-runs after acceptance. The tier recorded here is the one your reviewer sees.

### 3. Peer Review

A qualified coding expert reviews:
- Task clarity and correctness
- Solution validity
- Test coverage
- Anti-cheating measures
- Overall quality

The reviewer has your difficulty measurement and trial analysis in hand.

## Review Outcomes

### Approved ✓

Congratulations! Your task is accepted.

- Task added to benchmark suite
- Credit recorded in your profile

### Changes Requested

Reviewer identified issues that need fixing.

**What to do:**
1. Read feedback carefully
2. Understand each requested change
3. Make fixes locally
4. Re-run all checks
5. Resubmit / push updates

### Declined ✗

Task doesn't meet criteria. Common reasons:
- Too easy
- Unclear requirements
- Similar task already exists
- Fundamental design issues

**What to do:**
1. Review the feedback
2. Consider if it can be salvaged
3. Either significantly revise or start fresh
4. You can appeal if you disagree

## Addressing Feedback

### Read Carefully

Understand exactly what's being asked:
- Is it a minor fix or major revision?
- Does reviewer explain the reasoning?
- Are there specific lines/files mentioned?

### Make Targeted Changes

Don't rewrite everything. Fix only what's needed.
Use the [Reviewer Checklist](/portal/docs/reviewing-tasks/reviewer-checklist) to make sure all high-severity and medium-severity criteria are covered before resubmitting. One failed Medium is enough for revision.

### Explain Your Changes

When you resubmit:
**Platform:** Add a note with your revision summary.

This note is for your human reviewer. The quality panel does not read it — to contest a panel finding, post in [`#terminus-3-submissions`](https://snorkel-team.enterprise.slack.com/archives/C0BLQ26GN2W); see [Defending Your Submission](/portal/docs/reviewing-tasks/defending-your-submission).

### Re-request Review

After pushing changes, let the reviewer know:
**Platform:** Update submission status

## Disagreements

If you disagree with feedback:

1. **Respond politely** with your reasoning
2. **Provide evidence** for your approach
3. **Be open** to compromise
4. **Escalate** to Slack if needed

Remember: Reviewers want to help. Most disagreements are resolved through discussion.

## Tips for Faster Acceptance

1. **Run all checks locally** before submitting
2. **Follow the checklist** exactly
3. **Write clear documentation** in `instruction.md`
4. **Address feedback promptly** 
5. **Ask questions** if feedback is unclear

---

## Need Help?

- Slack: `#terminus-3-submissions`
- [FAQ](/portal/docs/reference/faq)
- [Troubleshooting](/portal/docs/reference/troubleshooting)
