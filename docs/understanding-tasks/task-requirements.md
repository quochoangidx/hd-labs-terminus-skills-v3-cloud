# Task Requirements

Every Terminus 3 task must satisfy all of the following. See [Task Components](/portal/docs/understanding-tasks/task-components) for the file structure these rules apply to.

## Novel

Avoid **any** variation of an existing task in the Terminal-Bench 2.1 or Terminal-Bench 3.0 repositories, or in Snorkel's prior Terminus editions. Each task must introduce a new setup, definition, and data.

Reskinning — the same computation behind a different cover story, different variable names, or a different language — is not novelty. Near-duplicates are detected automatically using embedding similarity, and a task can be returned for duplication even when it is individually well built.

## Multi-Step

Tasks must require chaining commands, with intermediate state to handle and real reasoning along the way — error recovery, branching, or reacting to what the previous step produced. A task solvable with a single command, or a single straight-line burst of commands, does not qualify.

You will see **"at least 5 agent steps"** used as shorthand for this. It is a **heuristic for complexity, not a number anyone counts** — nothing tallies steps, and there is no threshold to clear. It exists to rule out tasks that are trivially short. In practice, a task sized for the 30-minute minimum runtime will run well past five steps without you thinking about it.

The question to ask is not *"how many steps is this?"* but *"could an agent finish this in one shot, without reacting to anything along the way?"* If the answer is yes, the task is too simple.

## Requires Expertise

Every task must require genuine domain expertise to solve — graduate-level knowledge or several years of professional experience in the field. A task that someone without that background could work through in a few days does not qualify.

This is judged on the task itself, independently of how often agents solve it, and it applies at every difficulty tier. A [Base](/portal/docs/understanding-tasks/difficulty-guidelines) task is one agents usually solve; it is still expected to be expert work.

The floor is not met by obscure facts an agent already knows, a long checklist, or sheer volume of work. It is met by substantive domain reasoning: knowing which method applies, recognizing plausible but wrong results, and reasoning about interacting constraints. See [Difficulty Guidelines](/portal/docs/understanding-tasks/difficulty-guidelines) for what raises a task's difficulty and what only makes it longer.

## Testable

Each task must be fully specified and self-contained, solvable without ambiguity, and accompanied by tests that deterministically measure the **final state of the environment** to decide whether the task was completed correctly.

## Standalone

The task must run to completion without human input after start. All parameters are supplied via files, flags, or environment variables — no interactive prompts, no mid-run decisions.

All tasks are validated with the Harbor framework: single-container tasks in Daytona, multi-container tasks in a Docker environment.

## Runtime

Set `[agent].timeout_sec` to a **minimum of 1800 seconds (30 minutes)**, with a ceiling of 18000 seconds (5 hours).

The minimum is a floor, not a target. Terminus 3 tasks are expected to involve substantial multi-step work — inferring a specification, operating a system, and validating the result — and most should land in the **60–90 minute** range. If your task genuinely completes in under half an hour, that is usually a signal it isn't deep enough for this edition.

Set the timeout to what the work actually needs. Padding a short task doesn't make it harder, and starving a long one causes failures that look like difficulty but are really budget.

## Internet Access

Network access is set **per phase**. Each of the three phases carries its own `network_mode`:

```toml
[environment]
network_mode = "public"

[agent]
network_mode = "no-network"

[verifier]
network_mode = "no-network"
```

**`[environment].network_mode` must be `"public"`.** This is required on every task, offline tasks included. The environment phase is where the image is built and the agent harness is installed, and that installation needs the network. A task that closes the network at this phase fails before the agent ever runs.

**All three phases must declare `network_mode`.** An omitted phase is not a default — it silently inherits the baseline, so the agent and verifier end up running on a policy nobody chose. The static check reports each missing one, and it blocks submission.

**For a single-container task, the value on `[agent]` and `[verifier]` is yours to choose** — `"public"` or `"no-network"` on each, according to what the task needs:

| If the task… | `[agent]` | `[verifier]` |
|---|---|---|
| Should be solved offline | `"no-network"` | `"no-network"` |
| Genuinely requires the internet to solve | `"public"` | `"no-network"` |

Air-gapped is the stronger and more common choice for both. **You do not need to open the network for the agent's own tooling** — the platform grants the harness its gateway access separately, so a task never has to allow hosts on its behalf.

**Making a task offline no longer means closing `[environment]`.** Keep the environment public so the build succeeds, and set `"no-network"` on `[agent]` — that is what stops the agent reaching the network while it works.

> **Compose exception:** If `environment/docker-compose.yaml` (or another `docker-compose*.yml` / `.yaml`) is present, `[environment]`, `[agent]`, and `[verifier]` must all declare `network_mode = "public"`. The runner cannot apply separate phase network policies to a Compose environment. `check_compose_networks` blocks any Compose task with a non-public agent or verifier. If the task must be solved offline, package it as a single container.
>
> ⚠️ **`"allowlist"` is not a supported value**, and `allowed_hosts` is rejected with it. Production sandboxes have no network-allowlist capability, so a task using it is refused at creation and the difficulty check reports `Oracle ran 0 trials` — an infrastructure refusal that reads like a task defect.
>
> **`network_mode` at the top level is ignored.** Harbor drops unrecognised root keys, so a top-level setting looks correct and does nothing. It belongs inside `[environment]`, `[agent]` and `[verifier]`. The legacy `allow_internet` field is also rejected — it cannot express a per-phase policy.

Whatever you choose, your task's dependencies must still be baked into the image at build time, and `tests/test.sh` must never fetch from the network at trial time. A public `[verifier]` is not licence to install at grade time.

## Compute Limits

Tasks must **not require a GPU**, and oracle solutions must run successfully within:

| Resource | Limit |
|---|---|
| Memory | ~8 GB |
| CPU | 2 cores |
| Storage | ~10 GB |

GPU-adjacent work is still authorable — see the [`Kernels` subcategory](/portal/docs/understanding-tasks/task-taxonomy) for the CPU-simulated and compile-only patterns.

## Languages

This dataset targets languages under-represented in other benchmarks:

**Python · C · C++ · JavaScript · TypeScript · Java · Go · Rust · C#**

**Multi-language tasks are preferred.** Record the primary language(s) in `task.toml`:

```toml
[metadata]
languages = ["python", "c"]
```

`languages` records the **primary implementation language(s)** of the task — the language the agent
mainly works in. It does not have to list every tool involved.

**Domain-specific toolchains are welcome even when they are not on the list.** A proof assistant, an
HDL, a CAD scripting language, or a query language can absolutely appear in a task; they just may not
be what the task as a whole is written in. Use `languages` for the primary work and let the domain
tooling live in the environment.

The list is not meant to be restrictive. If you think a language belongs on it, say so in
[`#terminus-3-submissions`](https://snorkel-team.enterprise.slack.com/archives/C0BLQ26GN2W) — we are
open to expanding it.

> **Changed from Terminus 2nd Edition:** the rule requiring Python tasks to be HARD no longer
> applies. Difficulty tiers are language-independent.

## No Canary Strings

Tasks must not include canary strings in **any** component — instruction, environment, solution, tests, or metadata. Canary strings exist to keep benchmark data out of training corpora; this is a training dataset, so they are excluded. If you adapt an existing task as a structural starting point, remove any canary lines it carries.

## Instruction Prompts

Aim for **around 2 short paragraphs or a list of up to 20 bullets**; more complex tasks may need more room. State the goal; do not enumerate the intermediate steps. Prompts must not be LLM-generated — they should read like the way people actually talk to coding agents, and are automatically screened for AI-generated text. See [Instruction Prompt Styling](/portal/docs/understanding-tasks/prompt-styling).

## Dependency Pinning

Every `FROM` image must be digest-pinned with `@sha256:<digest>`, and Python packages pinned to exact versions. Verifier tooling must be baked into `tests/Dockerfile`, never installed at trial time. See [Dockerfile Requirements](/portal/docs/creating-tasks/dockerfile-best-practices).

## Rubrics

Every task ships with a rubric giving clear, deterministic criteria that map to measurable outcomes and align with the oracle solution.

> Generate and edit your rubric in the platform submission UI. Snorkel adds the `rubrics.txt` file during packaging — you don't author or ship it. See [Rubrics](/portal/docs/understanding-tasks/rubrics).

---

## Next Steps

- [Difficulty Guidelines](/portal/docs/understanding-tasks/difficulty-guidelines)
- [Writing Tests](/portal/docs/creating-tasks/writing-tests)
