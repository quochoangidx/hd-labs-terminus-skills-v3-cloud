# tbrain-press-shop-scheduling (stopped 2026-09-26): reference only, do not submit

This task is a press-shop schedule that must cost no more than a best-known target. The ZIP here is rev3 (sha256 `9be2067a…`), which is the same file as `workspace/revision/f60dccff-203d-4d8c-a21e-6c733293dd9e/revisions/tbrain-press-shop-scheduling-rev3.zip`. The task tree is in `../tbrain-press-shop-scheduling/`.

## Why it was stopped

- **It fails either way.** When the targets were tight, v3 and v4 failed the blocking `solvable` check. When they were loosened, v5 measured BASE, with 8/8 runs meeting every target. Under the lead's rule, BASE means replacing the task, not hardening it again. The details are in the "Best-known-target optimisation fails the platform either way" entry, archived in `docs/history/agents-section2-archive-2026-09-26.md`.
- **It no longer has a platform slot.** Assignment `f60dccff…` was reused from v6 on for `tbrain-bakery-fleet-dispatch`.

## Evidence

- The evidence is in `workspace/reports/tbrain-press-shop-scheduling/`.
- The platform returns are in `workspace/revision/f60dccff-…/v1`–`v5`.
