# Task-batch 3 (stopped 2026-09-26): reference only, do not submit

Four optimisation tasks. Each one passes when its plan costs no more than a target, and each target is the best plan the author found over hours of search. The agent gets 5,400 s on 2 CPUs.

| Task | State when stopped |
|---|---|
| tbrain-newspaper-ad-layout | ZIP built; local probe 0/2; local panel pass |
| tbrain-airport-gate-assignment | ZIP built; local probe 0/2 (0.09–0.9 % over target); correct_reference exception carried |
| tbrain-ward-nurse-rostering | fallback; local probe 1/2 |
| tbrain-bottling-line-lot-sizing | in progress; search killed |

Why they were stopped: `tbrain-press-shop-scheduling` has the same target shape. On the platform it failed the `solvable` quality check twice with tight targets (v3, v4), then measured BASE at 8/8 once the targets were loosened (v5). No task of this shape has been accepted. See the AGENTS.md §2 entry "Best-known-target optimisation fails the platform either way".

Reusable parts: the constraint checkers, the generators and `solution/search.py` in each task. The batch scripts are in `workspace/reports/batch-task-batch-5/`, the evidence in `workspace/reports/<slug>/`, and the probes in `workspace/local-solve-probes/`.
