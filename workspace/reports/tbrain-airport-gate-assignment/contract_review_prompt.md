You are the contract reviewer for a Terminus 3 benchmark task. Work in the current
directory, which holds only what the solving agent will see: `instruction.md` (the
task prompt) and `environment/` (the files copied into the agent's container under
`/app`). You have not seen the tests or the reference solution and must not look for
them. Do not edit any file. Do not run long searches; reading files and running the
supplied tools for a few seconds is fine.

The task: for four operating days, the agent writes stand-allocation plans that obey
`environment/app/docs/stand-rules.md` and cost no more than the targets in
`environment/app/days/targets.json`. The grader runs its own copy of
`tools/check_plan.py` on the four plan files, with its own copies of the days and
targets.

Review the contract a solver sees, and report findings with a severity each
(Blocking / Should-fix / Advisory), a citation (file:line), and the smallest fix:

1. Is every rule the checker enforces stated in the rules document, and does the
   rules document state anything the checker does not enforce (or enforces
   differently)? Compare `docs/stand-rules.md` against `tools/check_plan.py` line by
   line: occupancy and buffer, size, international, wingtip clashes (boundaries,
   whether the buffer applies), cost terms, the file format (duplicates, unknown ids,
   missing turns, extra keys, order).
2. Is anything a competent engineer would need left undecided or ambiguous (for
   example, boundary cases at equal minutes, a turn clashing with itself, transfers
   whose two turns are on the same stand, remote-to-remote walks)?
3. Work out 6-10 concrete witnesses by hand from the text alone (small hypothetical
   plans or plan fragments on the supplied days, with the verdict or cost the rules
   imply), then check each one with `tools/check_plan.py` where you can. Report any
   disagreement between the text and the tool.
4. Is the instruction consistent with the environment (paths, day names, what is
   graded, the Python-only constraint), and is the goal achievable in principle (the
   shipped planner's plans are valid)?
5. Anything in the environment that would let a solver pass without doing the work
   the task intends, or that misleads.

Write your report as Markdown with a `## Findings` list and a final
`## Verdict` line: `accept`, `accept with fixes`, or `reject`.
