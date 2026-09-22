# Difficulty Guidelines

Two different things are called "difficulty" in Terminus 3, and every task is judged on both.

## Difficulty Has Two Parts

**The expertise floor.** Every task must require genuine domain expertise to solve — graduate-level knowledge or several years of professional experience in the field. A task that someone without that background could work through in a few days does not qualify, whatever its pass rate. An automated check judges this on the task itself, before agents ever run on it, and a task that fails comes back to you. It applies at every tier.

**The tier.** How often frontier agents solve the task, measured across 8 runs. This decides where your task sits on the suite's difficulty curve: Frontier, Advanced, Core, or Base.

These are independent. Agents know a great deal, so a task can demand years of human expertise and still be solved by agents most of the time. That task can be **Base by tier and clear the floor**. For new submissions, the separate minimum-failure gate below must also be met; Base remains in the taxonomy for grandfathered tasks and the existing suite.

> **Base does not mean easy.** Base means agents usually solve it. It does not mean a person could. A grandfathered Base task is still expert work, and the floor is not waived for it.

What clears the floor is covered next, under [Designing for Expert Reasoning](#designing-for-expert-reasoning). Everything from [The Metric](#the-metric) down covers the measured tier and the separate proceed-to-review gate.

In `difficulty_explanation`, describe the expert knowledge and reasoning the task requires of a human — not the pass rate you measured. The pass rate determines the tier; the explanation describes the problem itself.

## Designing for Expert Reasoning

Tasks clear the expertise floor when success depends on domain judgment, not on following a long procedure. The floor is not met by obscure facts, a long checklist, or sheer volume of work. It is met by substantive domain reasoning, which reliably comes from three places:

- **Choosing between valid methods under real constraints.** More than one approach works in principle; the specifics of the task decide which is right, and the wrong choice produces a result that looks fine and isn't.
- **Diagnosing plausible-but-wrong results.** The output has the right shape and passes a surface check. Knowing it's wrong takes knowing what a correct one must satisfy.
- **Reasoning about interactions and edge cases a generic approach misses.** Each constraint is simple alone; the domain knowledge is in how they interact.

Do not add obscure facts, unrelated steps, or more data volume merely to make a task harder. Those may raise effort or lower agent pass rate, but they do not establish the expertise floor. Raising the tier is a different job — see [Making a Task Harder](#making-a-task-harder--and-what-doesnt-work).

## The Metric

**Accuracy = average pass@1 across 8 runs — 4 per model, over both GPT-5.6 and Claude Opus 5.**

Accuracy is the mean pass rate across all 8 runs, not a best-model or worst-model figure.

Difficulty is measured **once**, in a single 8-run stage, and the result is final:

| | |
|---|---|
| **When** | After your task passes the [quality panel](/portal/docs/testing-and-validation/quality-panel-judge-guide), before it reaches a reviewer |
| **Runs** | 4 per model × 2 models = **8** |
| **What it decides** | The tier recorded for your task, and whether a new submission clears the minimum-failure gate to proceed |

**For new submissions, at least 3 of the 8 platform runs must fail.** No more than 5 may pass, so the maximum measured accuracy that can proceed is **62.5%**. Previously, one failure was enough. Fix a task that misses this gate by making the underlying challenge harder, not by narrowing a grading threshold.

Tasks already on the platform by the morning of **Sep 11, 2026** are grandfathered under the prior one-failure rule. Later revisions of those existing tasks remain grandfathered.

There is no separate iteration measurement, and nothing runs after acceptance — the tier a reviewer sees is the one your task keeps.

## Difficulty Tiers

| Tier | Accuracy | Target share of suite |
|---|---|---|
| **Frontier** | < 20% | 20–30% |
| **Advanced** | 20% – < 50% | 25–35% |
| **Core** | 50% – < 80% | 30–40% |
| **Base** | 80% – < 100% | 5–15% |

Set the resulting tier in `task.toml`:

```toml
[metadata]
difficulty = "advanced"
```

> **The tier bands are unchanged, but the proceed gate is separate.** The tiers still describe measured accuracy across the suite. For a new submission, 6–8 passes do not clear the gate, so it cannot enter review with a Base result or a 75% Core result. Base remains a valid tier for grandfathered tasks and for describing the existing suite.
>
> The gate is measured across both models together, not per model. One model may go 4/4 only if at least 3 of the other model's runs fail, giving no more than 5 passes overall.

The target shares describe the shape of the **whole suite**, not a quota you personally must hit. They tell you where submissions are most valuable: Frontier and Advanced tasks are the scarcest and hardest to author well.

## Designing for a Tier

Difficulty does not come from obscurity or volume of work. It comes from **how much has to be true simultaneously** for the result to be correct.

**Frontier (< 20%)** — the specification itself must be inferred from domain evidence, the output must be a semantically correct native artifact, and several correctness axes interact. Success requires the agent to build a correct model of the domain before it can write anything useful.

**Advanced (20–<50%)** — the goal is clear but the path is not. Multiple constraints interact, state must be handled correctly across steps, and a plausible-looking result can still be wrong.

**Core (50–<80%)** — a well-specified problem with real depth: multi-step, some domain knowledge, edge cases that punish careless work.

**Base (80–<100%)** — genuinely solvable by a competent agent, but still multi-step and non-trivial. Base tasks anchor the low end of the existing curve; under the Sep 15 gate, this tier is available only to grandfathered tasks.

## Making a Task Harder — and What Doesn't Work

This section is about the tier — moving agent pass rate down. For the expertise floor, see [Designing for Expert Reasoning](#designing-for-expert-reasoning).

**Works:**

- Require the agent to *infer* the contract from domain evidence rather than stating it.
- Demand a native, structurally valid artifact rather than something that merely looks right.
- Add a second correctness axis that interacts with the first (performance under determinism; safety under state consistency).
- Verify against hidden variations that test whether the agent understood the contract, not whether it passed one example.

**Doesn't work:**

- Piling on unrelated independent requirements — that is length, not difficulty.
- Ambiguity or under-specification. A task that is hard because it is unclear is a broken task, not a Frontier task.
- Obscure trivia with no reasoning behind it.
- Anything that makes runs non-deterministic.

## Measuring Your Task

Run against both models before submitting:

```bash
stb harbor run -m @openai/gpt-5.6 -p <task-folder> -k 4
stb harbor run -m @anthropic/claude-opus-5 -p <task-folder> -k 4
```

`-k 4` mirrors the platform's measurement, so it gives you the best local read on where your task will land. Fewer runs are fine for a rough signal while you iterate.

> **Your local runs are an estimate, not the measurement.** Different seeds and different days move results. The platform's 8-run measurement sets the tier, and it is the only one — there is no shorter platform check that can differ from it.

Then check *why* agents failed. Failures caused by unclear instructions, environment defects, or flaky tests are **bugs**, not difficulty — fix them and re-measure. Only failures that come from the actual challenge of the task should count toward your tier.

## Reading the Trial Analysis

The difficulty check ends with a **trial analysis** section reporting six criteria. Each returns **PASS**, **FAIL**, or **NOT_APPLICABLE** — a criterion is *flagged* when it returns FAIL. `NOT_APPLICABLE` is not a problem; it means there wasn't enough evidence to judge.

You see this before you submit, and reviewers see the same output. Resolving a flag now is far cheaper than having the task returned for it.

**Two flags mean the task must change:**

| Flag | What it means | What to do |
|---|---|---|
| `task_specification` | Your tests require something `instruction.md` never states — an exact parameter name, file format, return value, or structure the agent had to guess. | Specify it in the instruction, or relax the test. |
| `reward_hacking` | The agent reached its reward illegitimately — editing tests, writing the reward file directly, or reading `solution/`. | Close the hole. See [Writing Tests](/portal/docs/creating-tasks/writing-tests). |

**Four flags need you to look, and often mean the task is measuring the wrong thing:**

| Flag | What it means | What to do |
|---|---|---|
| `difficulty_crux` | The agent failed for a reason unrelated to the challenge you described in `[metadata].difficulty_explanation`. | Either the task carries unintended difficulty, or your explanation doesn't describe the real crux. Fix whichever is wrong. |
| `near_miss` | The agent produced a substantively working solution that fell just short. | Look at **which** tests fail across the runs — see the note below. |
| `refusals` | The agent aborted on a content or safety policy instead of attempting the task. | Review the framing and content — a refused trial measures nothing. |
| `low_timeout` | The agent was still making real progress when the timeout hit. | Raise `[agent].timeout_sec`. Difficulty should come from the problem, not from running out of time — see [Task Requirements](/portal/docs/understanding-tasks/task-requirements). |

> **Reading a `near_miss`.** Look at which tests fail across the runs. If the runs keep failing the **same one or few tests**, look at those tests and the instructions — a check that every capable agent fails is usually the source of the error rather than real difficulty. If the runs fail **different tests each time**, the agent is genuinely close but slipping in different places, which is a more acceptable near-miss and closer to real difficulty. In neither case should you raise the difficulty only because near-complete runs count as failures.
>
> Keep `near_miss` about difficulty. If the failing check enforces something the instruction never states, that belongs under `task_specification` instead.

A flag is not automatically fatal, but it does need an answer. Reviewers send a task back when a flag's reason holds up, so it is worth resolving — or being able to explain — before you submit.

---

## Next Steps

- [Task Requirements](/portal/docs/understanding-tasks/task-requirements)
- [What Makes a Good Task](/portal/docs/understanding-tasks/what-makes-a-good-task)
