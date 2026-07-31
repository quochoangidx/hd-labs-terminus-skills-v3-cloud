# Welcome to Project Terminus

## Latest Updates

The five most recent announcements. **[See the full Changelog →](/portal/changelog)**

| Date         | Type      | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------ | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Jul 30, 2026 | 🆕 New | **Submissions are open again — all categories, for the final push.** The Jul 27 pause is lifted and **every category is accepting net-new tasks until further notice**. The category classifier check has also been loosened. New milestone tasks remain blocked. Revisions continue as normal. ***[See Task Category Status](/portal/category-status)*** |
| Jul 27, 2026 | 🔄 Update | **All net-new submissions are paused, effective immediately.** Brand-new task submissions are blocked across every category. **Revisions continue as normal** — keep working through your Revision Queue, since clearing your existing revisions remains the most direct path to getting your submissions to **Accepted**. Tasks already in your revision queue or awaiting review are unaffected. ***[See Task Category Status](/portal/category-status)*** |
| Jul 24, 2026 | 🔄 Update | **Submissions are temporarily limited to three categories: `machine-learning`, `games`, and `system-administration`.** All other categories are blocked for net-new submissions while we balance the benchmark's category distribution; new milestone tasks remain blocked too. Tasks already in your revision queue or awaiting review continue through to Accepted as normal. ***[See Task Category Status](/portal/category-status)*** |
| Jul 21, 2026 | 🔄 Update | **Difficulty checks may now run only one model.** Checks run Claude Opus 4.8 first; if it already rates your task **Hard** (≤ 20% accuracy), the GPT-5.5 run is skipped, since a Hard result from either model already settles the rating. Results from only one model on a Hard-rated task are expected — not a bug, and no need to flag it. Nothing changes about how you author or submit tasks. ***[See Difficulty Guidelines](/portal/docs/understanding-tasks/difficulty-guidelines)*** |
| Jul 21, 2026 | 🔄 Update | **Quick Start now installs the Snorkel CLI (`snorkelai-stb`) and authenticates via `stb login` / `stb keys refresh`.** The retired Harbor `promptfix` wheel and the manual `OPENAI_API_KEY` / `OPENAI_BASE_URL` exports are gone — the CLI manages AI credentials for agent runs. ***[See Quick Start](/portal/docs/getting-started/quick-start)*** |


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
4. **Agent evaluation** — Run against Claude Opus 4.8 and GPT-5.5 (5 times each; if Opus 4.8 already rates the task Hard, the GPT-5.5 run is skipped)



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
