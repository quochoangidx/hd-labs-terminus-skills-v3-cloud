# Defending Your Submission

How to respond to review feedback and appeal decisions.

## Quality panel findings

A quality-panel finding should identify a specific contract passage, code location, or test and explain the failure. Axis verdicts of `Minor` or `Major` block on contract, reference solution, verifier soundness, and deterministic execution; for `protected_ground_truth`, only `Major` blocks. Findings explicitly marked `Advisory` do not block. If the citation does not support the claim, or the proposed input falls outside the stated contract, respond with the exact passage and a reproducible counterexample.

Use the report's evidence: a deliberately wrong solution that passes your verifier supports a soundness finding; a runner failure or an unsuccessful proof attempt does not establish that the task is sound. `Unsure` or incomplete evidence is not a confirmed task defect. Check the evaluation status and report, and request support if evaluation remains unfinished. When resubmitting, connect each fix to the original finding and include the relevant test result; do not assume the next review automatically has the prior report. See the [Quality Panel Judge Guide → FAQ](/portal/docs/testing-and-validation/quality-panel-judge-guide#faq) and [worked examples](/portal/docs/testing-and-validation/quality-panel-examples).

## Responding to Feedback

### Read Carefully

Before responding:
1. Read each comment fully
2. Understand what's being asked
3. Consider if the feedback is valid
4. Check if you missed something

### Acknowledge Valid Points

If the reviewer is right:
```
"You're right, the test on line 45 uses brittle string matching. 
I've updated it to check for the presence of required fields instead."
```

### Explain Your Reasoning

If you disagree or need clarification:
```
"I chose to use exact string matching here because the output format
is strictly specified in the instructions (line 12). The agent is told
to output exactly 'status: success' - would checking for 'success' 
alone be acceptable, or should I clarify the instructions?"
```

### Ask Questions

If feedback is unclear:
```
"Could you clarify what you mean by 'tests are too strict'? 
Are you referring to the format checking or the value validation?"
```

## Making Changes

### Be Thorough

Address every point raised, not just some.

### Be Explicit

When you push changes, explain what you did:
```
Addressed review feedback:
- Line 45: Changed string match to field check
- Line 67: Added docstring to test_output
- instruction.md: Clarified output format requirement
```

### Don't Over-Engineer

Fix what's asked. Don't rewrite unrelated code.

## Disagreements

### When to Push Back

It's okay to disagree if:
- You have a valid technical reason
- The feedback misunderstands your approach
- The requested change would break something

### How to Push Back

Be respectful and provide evidence:

**Don't:**
```
"That's wrong. My approach is fine."
```

**Do:**
```
"I understand the concern about test brittleness, but in this case
the exact format is critical - the task specifically requires JSON
with these exact keys. Here's why I think the current test is 
appropriate: [explanation]. Would you like me to add a comment
explaining this, or do you still think I should change it?"
```

### Escalation

If you can't resolve disagreement with the reviewer:

1. **Document your position** clearly in the submission
2. **Reach out on Slack** to `#terminus-3-submissions`;

Snorkel make final decisions on disputes.

## Appeals

### When to Appeal

Appeal if:
- Task was declined but you believe it meets criteria
- Feedback is incorrect or unfair
- There's a misunderstanding about requirements

### How to Appeal

1. **Reply to the decision** with your reasoning
2. **Provide specific evidence** for your position
3. **Be professional** - appeals are reviewed by seniors
4. **Accept the outcome** - final decisions are final

### Appeal Template

```
I'd like to appeal this decision. Here's my reasoning:

**Reviewer said:** [quote feedback]

**My response:** [your explanation]

**Evidence:** [specific examples, references, etc.]

I believe this task should be [accepted/reconsidered] because [reason].
```

## Tips for Smooth Reviews

### Before Submission

- Run all checks locally
- Self-review against guidelines
- Have a colleague look at it

### During Review

- Respond promptly (within 1-2 days)
- Be collaborative, not defensive
- Ask questions early

### If Declined

- Take feedback seriously
- Consider if the task can be salvaged
- Learn from it for next time
- It's okay to start fresh

---

## Remember

Reviewers are on your side. They want tasks to succeed. Most feedback is meant to help you improve your submission, not reject it.

A collaborative attitude leads to faster acceptance.
