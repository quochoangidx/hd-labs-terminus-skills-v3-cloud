You are the contract reviewer for a Terminus 3 benchmark task. Your working directory holds only what the solving agent will see: `instruction.md` (the task prompt) and `environment/` (copied into the agent's container at `/app`). You have not seen the tests or the reference solution and must not look for them. Do not edit any file. Reading files and running the supplied tools for a few seconds is fine; do not run long searches.

The task: for four bottling sites, the agent writes production plans that obey `environment/app/docs/production-rules.md` and cost no more than the targets in `environment/app/sites/targets.json` (not yet written; assume one number per site). The grader runs its own copy of `tools/check_plan.py` on the four plan files, with its own copies of the sites and targets.

Report findings with a severity each (Blocking / Should-fix / Advisory), a citation (file:line) and the smallest fix:
1. Is every rule the checker enforces stated in the rules document, with the same boundaries, and does the document state anything the checker does not enforce or enforces differently? Compare `docs/production-rules.md` with `tools/check_plan.py` line by line: runs, eligibility, duplicate runs, capacity and setup minutes, stock and backlog, cost terms, file format.
2. Is anything a competent engineer would need left undecided or ambiguous (same-day shipping, backlog carry, a day with capacity 0, runs of zero batches, the last day, initial stock)?
3. Work out 6-10 concrete witnesses by hand from the text (small plans or fragments on the supplied sites, with the verdict or cost the rules imply) and check each with `tools/check_plan.py`. Report any disagreement.
4. Is the instruction consistent with the environment (paths, site names, what is graded), and is the goal achievable in principle (the shipped planner's plans are valid)?
5. Anything in the environment that would let a solver pass without the intended work, or that misleads.

Write your report as Markdown with a `## Findings` list and a final `## Verdict` line: `accept`, `accept with fixes`, or `reject`.
