# Welcome to Terminus 3

## Latest Updates

Recent announcements. **[See the full Changelog →](/portal/changelog)**

| Date         | Type   | Change |
| ------------ | ------ | ------ |
| Sep 7, 2026 | 🆕 New | **Platform preflight `verifier_interpreter_permissions`.** Saving and restoring both `/bin/bash` and `/usr/bin/bash` without `Path.resolve()` deduplication can leave Bash non-executable; Harbor then cannot collect verifier logs. Blocking on platform submit, before Oracle; not in `stb harbor check`. ***[See Writing Tests](/portal/docs/creating-tasks/writing-tests#preserve-interpreter-permissions)*** |
| Sep 4, 2026 | 🆕 New | **Quality Panel Judge Guide.** Four-axis automated review (`coherent_contract`, `correct_reference_solution`, `protected_ground_truth`, `sound_verifier`) being wired in as a blocking check before a human reviewer. **`Minor` and `Major` both block**, as does `Unsure`. Checklists on the main page; numbered synthetic cases in a separate appendix. ***[See Quality Panel Judge Guide](/portal/docs/testing-and-validation/quality-panel-judge-guide)*** |
| Sep 3, 2026 | 🔄 Update | **Isolating cases and grade-time keys.** A named domain rule is not tested if the only discriminating fixture is mixed held-out data, or if one coarse mutant (the shipped buggy code) is the only wrong solution you ran. Held-out must not be the sole enforcement of any stated rule. Hidden test inputs are fine; hidden requirements are not. Separate mode protects the verifier from the agent environment, not from code the verifier itself executes. Harbor defaults to **shared** if neither `environment_mode = "separate"` nor a `[verifier.environment]` table is set; Terminus CI requires the explicit key. See [Writing Tests](/portal/docs/creating-tasks/writing-tests) and [Dockerfile §8](/portal/docs/creating-tasks/dockerfile-best-practices#8-separate-agent-visible-runtime-from-verifier-only-assets). |
| Sep 2, 2026 | 🆕 New | **Cloud image builder rejects two Dockerfile patterns that work locally.** `COPY --chown=` must use numeric IDs (`0:0`, `1000:1000`), not names such as `root`. `COPY --from=` image refs must be digest-only — drop the `:tag`, keep `@sha256:…`. `FROM image:tag@sha256:…`, `COPY --from=builder`, and `RUN chown` are unchanged. A blocking preflight now flags the exact line at submit time. See [Dockerfile Requirements](/portal/docs/creating-tasks/dockerfile-best-practices#cloud-image-builder-syntax). |
| Aug 31, 2026 | 🆕 New | **CAD Task Guidelines for the Hardware category.** The five ways to establish geometry — direct measurement, invariant checking, symmetric difference, sampling, functional verification — with what each can and cannot see. Led by the trap that point-containment probes *bound* a dimension but never *determine* one, so a verifier can pass its own oracle and still accept a part wrong in every stated dimension. Plus: a parametric task has to test the recompute, not read a stored parameter back. ***[See CAD Task Guidelines](/portal/docs/creating-tasks/cad-task-guidelines)*** |
| Aug 24, 2026 | 🔄 Update | **`network_mode` is now set per phase, and `[environment]` must be `"public"`.** The agent harnesses install during the environment build, so a closed environment fails before the agent runs — this was stalling evaluations. Add `network_mode` to `[agent]` and `[verifier]` (`"public"` or `"no-network"`); an offline task keeps `[environment]` public and sets `[agent]` to `"no-network"`. **Applies to new tasks and tasks in progress**, and is enforced by a blocking static check. See [Task Requirements](/portal/docs/understanding-tasks/task-requirements). |
| Aug 19, 2026 | 🆕 New | **Named verifier exploit patterns from delivery review.** Extends the Aug 17 too-loose-verifier guidance with four anti-patterns in [Writing Tests](/portal/docs/creating-tasks/writing-tests): ground truth from agent-writable paths, symlink/copy staging leaks, instruction–verifier tolerance drift, and untested optimization objectives or tie-breaks, plus a short note on not loading agent code before fixed assertions. Ground-truth and symlink patterns fold into the existing **High** reject-wrong-solution criterion; tolerance drift and untested objectives get new **Medium** rows. [Submission Checklist](/portal/docs/submitting-tasks/submission-checklist) self-checks added. |
| Aug 17, 2026 | 🔄 Update | **Stronger guidance on verifiers that are too loose.** A task must **reject a wrong solution**, not just accept a right one — run a deliberately wrong solution against your own verifier before submitting. Adds concrete shortcut vectors to [What Makes a Good Task](/portal/docs/understanding-tasks/what-makes-a-good-task), three anti-patterns to [Writing Tests](/portal/docs/creating-tasks/writing-tests) (proxy checks, grading an unrebuilt binary, artifacts the agent controls both sides of), and a **Correct, Not Just Passing** principle to [Writing Oracle Solution](/portal/docs/creating-tasks/writing-oracle-solution) — a passing oracle does not prove the reference is right. [Difficulty Guidelines](/portal/docs/understanding-tasks/difficulty-guidelines) now reads `near_miss` from the failure pattern across runs. |
| Aug 13, 2026 | 🆕 New | **The Terminus 3 task skeleton is available.** [Download it here](/Terminus-3-Prod/default-template.zip) — a complete working task to rename and replace, with every field you must fill in marked `REPLACE`. ***[See Platform Submission](/portal/docs/submitting-tasks/platform-submission)*** |
| Jul 31, 2026 | 🆕 New | **Terminus 3 is now live.** Terminus 2nd Edition has concluded. The docs now cover Terminus 3: a new task category taxonomy, four empirical difficulty tiers, and a verifier that runs in a separate container. Milestone tasks are no longer part of the program. ***[Start with What's New](/portal/docs/getting-started/whats-new)*** |

## What is Terminus 3?

Terminus 3 is Snorkel's expert-authored dataset targeting **Terminal-Bench 3.0**, a benchmark for evaluating AI coding agents on genuinely difficult, domain-grounded work.

Earlier editions asked agents to perform a difficult terminal or software task. Terminus 3 asks for something harder: tasks where the agent must **understand a specialized domain, manipulate the right system inside it, and produce a result that satisfies several interacting constraints at once** — verified against checks it cannot see.

Your job is to create those tasks.

> **Your work matters.**
>
> Every accepted task directly advances the development of AI coding agents by revealing their current limitations and pushing them to improve.

## Your Role as a Coding Expert

1. **Design tasks** grounded in a real domain, that challenge frontier models
2. **Write oracle solutions** that demonstrate correct completion
3. **Build verifiers** that check semantics, not appearance
4. **Iterate on feedback** from automated checks and peer review

## Difficulty Tiers

Difficulty is **measured, not declared** — from accuracy across GPT-5.6 and Claude Opus 5 (average pass@1 over 8 runs, 4 per model):

| Tier | Accuracy | Share of suite |
|---|---|---|
| **Frontier** | < 20% | 20–30% |
| **Advanced** | 20% – < 50% | 25–35% |
| **Core** | 50% – < 80% | 30–40% |
| **Base** | 80% – < 100% | 5–15% |

See [Difficulty Guidelines](/portal/docs/understanding-tasks/difficulty-guidelines).

## Evaluation Process

Each task goes through:

1. **Automated CI checks** — structure, manifest, dependencies, verifier isolation
2. **LLM-as-Judge (LLMaJ)** — quality evaluation
3. **Peer review** — human expert verification
4. **Agent evaluation** — run against Claude Opus 5 and GPT-5.6, 4 trials each after acceptance

## Quick Links

| Resource | Description |
|---|---|
| **[Quick Start Guide](/portal/docs/getting-started/quick-start)** | Get set up |
| **[Task Skeleton](/Terminus-3-Prod/default-template.zip)** | Starter files — a complete working task to rename and replace |
| **[What's New in Terminus 3](/portal/docs/getting-started/whats-new)** | Everything that changed |
| **[What Makes a Good Task](/portal/docs/understanding-tasks/what-makes-a-good-task)** | What a strong task looks like |
| **[Task Components](/portal/docs/understanding-tasks/task-components)** | Required files and structure |
| **[Task Taxonomy](/portal/docs/understanding-tasks/task-taxonomy)** | Categories and subcategories |
| **[FAQ](/portal/docs/reference/faq)** | Common questions |
| **[Snorkel Expert Platform](https://experts.snorkel-ai.com/)** | Submit and track your work |
| **[Glossary](/portal/docs/reference/glossary)** | Project terms explained |

## Need Help?

| Resource | Link |
|---|---|
| **Slack** | [`#terminus-3-submissions`](https://snorkel-team.enterprise.slack.com/archives/C0BLQ26GN2W) |
| **Announcements** | [`#terminus-3-announcements`](https://snorkel-team.enterprise.slack.com/archives/C0BLN0YUNQN) |
| **Office Hours** | See the [Office Hours page](/portal/docs/reference/office-hours) |

---

**Ready to dive in?**
**[Start with the Quick Start Guide](/portal/docs/getting-started/quick-start)**
