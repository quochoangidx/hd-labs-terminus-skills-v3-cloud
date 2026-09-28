You are the contract reviewer for a Terminus 3 benchmark task. Work in the current
directory, which holds only what the solving agent will see: `instruction.md` (the
task prompt) and `environment/` (the files copied into the agent's container under
`/app`). You have not seen the tests or the reference solution and must not look for
them. Do not edit any file. Do not run long searches; reading files and running the
supplied tools for a few seconds is fine.

The task: for four hospital wards, the agent writes four-week nurse rosters that obey
`environment/app/docs/roster-rules.md` and have a penalty no higher than the targets in
`environment/app/wards/targets.json`. The grader runs its own copy of
`tools/check_roster.py` on the four roster files, with its own copies of the wards and
targets.

Review the contract a solver sees, and report findings with a severity each
(Blocking / Should-fix / Advisory), a citation (file:line), and the smallest fix:

1. Is every rule the checker enforces stated in the rules document, and does the
   rules document state anything the checker does not enforce (or enforces
   differently)? Compare `docs/roster-rules.md` against `tools/check_roster.py` line by
   line: cover and grades, leave, rest between days, consecutive days, rest after
   nights (runs ending on the last day), each penalty term (weekends, lone days at
   the edges, requests, hours, nights), the file format (missing or unknown nurses,
   row length, codes, extra keys).
2. Is anything a competent engineer would need left undecided or ambiguous (for
   example, where the week starts, how a night relates to the next day, what counts
   as a weekend worked, what happens on the first and last day)?
3. Work out 6-10 concrete witnesses by hand from the text alone (small hypothetical
   rosters or roster rows on the supplied wards, with the verdict or cost the rules
   imply), then check each one with `tools/check_roster.py` where you can. Report any
   disagreement between the text and the tool.
4. Is the instruction consistent with the environment (paths, ward names, what is
   graded, the Python-only constraint), and is the goal achievable in principle (the
   shipped planner's plans are valid)?
5. Anything in the environment that would let a solver pass without doing the work
   the task intends, or that misleads.

Write your report as Markdown with a `## Findings` list and a final
`## Verdict` line: `accept`, `accept with fixes`, or `reject`.
