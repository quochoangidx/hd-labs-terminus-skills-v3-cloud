# Welcome to Project Terminus

## Latest Updates

The five most recent announcements. **[See the full Changelog →](/portal/changelog)**

| Date         | Type      | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------ | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Jul 17, 2026 | 🆕 New | **Changelog and Task Category Status now live in the top menu.** The full changelog moved from the Welcome page to its own [Changelog](/portal/changelog) section, and the new [Task Category Status](/portal/category-status) page shows which categories and policies are currently open or blocked at a glance. The Welcome page keeps the five most recent entries. |
| Jul 17, 2026 | 🔄 Update | **FAQ refreshed with 8 new entries** covering recent policy updates: blocked categories, `allow_internet = true`, optional `gpus`/`gpu_types`/`docker_flags`, canonical base images, verifier logic in tests, gallery task-idea flexibility, post-claim skeleton downloads, and the rubric `+` sign rule. ***[Go to FAQ](/portal/docs/reference/faq)*** |
| Jul 13, 2026 | 🔄 Update | **`allow_internet = true` tasks are welcome — the setting just has to match the task.** Both `allow_internet = false` (default) and `true` are acceptable: use `false` for tasks fully solvable offline, and `true` only when the task genuinely requires internet — retrieving current/external information, interacting with web-based resources, or downloading an external model/resource that can't be bundled (e.g., a HuggingFace model). An eval checks whether internet is actually required, so `true` without a genuine need may be rejected. ***[See Dockerfile Best Practices](/portal/docs/creating-tasks/dockerfile-best-practices)*** |
| Jul 10, 2026 | 🔄 Update | **The `data-processing` category is currently blocked.** Data Processing & Scripting is paused — not accepting new submissions, and it has been removed from the task gallery. Do not submit new tasks under this category until this note is removed. Tasks already in your revision queue or awaiting review are exempt and continue through to Accepted as normal. ***[See Task Taxonomy](/portal/docs/understanding-tasks/task-taxonomy)*** |
| Jul 9, 2026  | 🔄 Update | **`gpus`, `gpu_types`, and `docker_flags` in `task.toml` `[environment]` are optional.** Tasks will not be sent back for omitting these or leaving them blank — TB2 tasks are not required to use GPU. Both the full and minimal `[environment]` blocks are valid. ***[See Dockerfile Best Practices](/portal/docs/creating-tasks/dockerfile-best-practices)*** |


## What is Project Terminus?

Project Terminus is a benchmark for evaluating AI coding agents on real-world engineering tasks. Your job is to create tasks that challenge today's best models—tasks that require genuine engineering reasoning, multi-step problem solving, and practical skills.

Unlike simple code completion benchmarks, Project Terminus tests:

- **Multi-step reasoning** — Tasks require chaining multiple commands
- **Environment interaction** — Agents work in real Docker containers
- **Practical skills** — Real debugging, configuration, and development tasks

> **Your work matters.**
>
> Every accepted task directly advances the development of AI coding agents by revealing their current limitations and pushing them to improve.

> **Explore existing tasks:** [Browse our Task Gallery](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/tasks)
>
> *Note: While this project is NOT affiliated with the official Terminal-Bench project, we closely mimic its style.*

## Your Role as a Coding Expert

As a Coding Expert, you will:

1. **Design tasks** that challenge frontier AI models
2. **Write oracle solutions** that demonstrate correct completion
3. **Create tests** that verify task completion
4. **Iterate on feedback** from automated checks and peer review

Task Difficulty Targets

Testing your task on AI agents on GPT-5.5 and Claude Opus 4.8 yields pass rates for the task you create. According to how many times it fails or succeeds, your task falls into the following difficulty tiers:


| Difficulty | Threshold                                                             | Description                                   |
| ---------- | --------------------------------------------------------------------- | --------------------------------------------- |
| **Hard**   | Accuracy ≤ 20% on the **best** model, OR ≤ 20% on the **worst** model | Requires deep expertise, multi-step reasoning |
| **Medium** | 20% < accuracy ≤ 60% on the **worst** model                           | Moderate complexity, some domain knowledge    |
| **Easy**   | 60% < accuracy ≤ 80% on the **worst** model                           | Straightforward but still non-trivial         |


> **Important:** Tasks where the **worst** model scores above 80% will **NOT** be accepted. See [Difficulty Guidelines](/portal/docs/understanding-tasks/difficulty-guidelines) for the full breakdown.



Evaluation Process

Each task undergoes a rigorous 4-step review:

1. **Automated CI checks** — Technical requirements (syntax, structure, etc.)
2. **LLM-as-Judge (LLMaJ)** — Quality evaluation using GPT-5.5
3. **Peer review** — Human expert verification
4. **Agent evaluation** — Run against GPT-5.5 and Claude Opus 4.8 (5 times each)



Estimated Time

- **Per task:** 2-5 hours
- **Includes:** Design, development, testing, and iteration



## Quick Links


| Resource                                                                              | Description                                 |
| ------------------------------------------------------------------------------------- | ------------------------------------------- |
| **[Quick Start Guide](/portal/docs/getting-started/quick-start)**                     | Get up and running in 10 minutes            |
| **[What Makes a Good Task](/portal/docs/understanding-tasks/what-makes-a-good-task)** | Learn to create high-quality tasks          |
| **[Task Components](/portal/docs/understanding-tasks/task-components)**               | Understand the required files and structure |
| **[FAQ](/portal/docs/reference/faq)**                                                 | Common questions answered                   |
| **[Download Task Skeleton](/Terminus-EC-Training-stateful/Terminus-2nd-Edition/default-template.zip)** | Starter template for a new task             |
| **[Snorkel Expert Platform](https://experts.snorkel-ai.com/)**                        | Submit and track your work                  |
| **[Slack community](https://snorkel-team.enterprise.slack.com/archives/C09MNJL1203)** | Questions, announcements, and support       |
| **[Glossary](/portal/docs/reference/glossary)**                                       | Project terms explained                     |


## Need Help?


| Resource          | Link                                                                                    |
| ----------------- | --------------------------------------------------------------------------------------- |
| **Slack Channel** | `#terminus-2nd-edition-submission`                                                      |
| **Office Hours**  | Daily sessions during the week to answer questions, or get live help from Snorkel staff |


---

**Ready to dive in?**
**[Start with the Quick Start Guide](/portal/docs/getting-started/quick-start)**
