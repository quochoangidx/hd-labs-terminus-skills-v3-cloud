# Task Category Status

Live view of which task categories and policies are currently open for new submissions.

All categories are open for Terminus 3. Category definitions are in [Task Taxonomy](/portal/docs/understanding-tasks/task-taxonomy).

## Categories

| Category | Status | Since |
|---|---|---|
| `Science` | ✅ Open | Jul 31, 2026 |
| `Software` | ✅ Open | Jul 31, 2026 |
| `ML` | ✅ Open | Jul 31, 2026 |
| `Operations` | ✅ Open | Jul 31, 2026 |
| `Security` | ✅ Open | Jul 31, 2026 |
| `Hardware` | ✅ Open | Jul 31, 2026 |
| `Media` | ✅ Open | Jul 31, 2026 |

> **Note:** Terminus 3 begins with every category open. If a category is later paused, it will be listed here and announced in the [Changelog](/portal/changelog).

## Policies & Settings

| Policy | Status | Since |
|---|---|---|
| Milestone tasks | 🚫 Not part of this edition | Jul 31, 2026 |
| Internet access | ✅ `network_mode = "public"` by default; `"no-network"` when the task should run offline | Jul 31, 2026 |
| GPU tasks | 🚫 Tasks must not require a GPU — kernel work is authorable CPU-simulated or compile-only | Jul 31, 2026 |
| Canary strings | 🚫 Excluded from all components | Jul 31, 2026 |
| Verifier isolation | ✅ Required — `environment_mode = "separate"` | Jul 31, 2026 |
| Agent timeout | ✅ Minimum 1800s (30 min), ceiling 18000s (5 h) | Jul 31, 2026 |

See [Task Requirements](/portal/docs/understanding-tasks/task-requirements) for details.
