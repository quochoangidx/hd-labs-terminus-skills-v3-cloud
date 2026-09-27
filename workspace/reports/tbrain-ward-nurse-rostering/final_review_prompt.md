You are the final reviewer for a Terminus 3 benchmark task. Earlier you reviewed only
what the solving agent sees; your verdict from that turn is in
`prior/contract_review.md`, and how each of your findings was handled is in
`prior/contract-review-adjudication.md`. An adversarial reviewer later tried wrong
submissions against the grader; its report and the handling are in
`prior/adversarial_review.md` and `prior/adversarial-adjudication.md` when present.

This turn you see the whole task in the current directory: `instruction.md`,
`task.toml`, `environment/` (the agent's `/app`), `tests/` (the separate grader) and
`solution/` (the reference). Do not edit any file. Reading files and running the
supplied tools or the grader's checker for a few seconds is fine; do not run long
searches.

The task: for four wards the agent writes four-week nurse rosters that keep the hard rules of environment/app/docs/roster-rules.md and have a penalty no higher than the targets in environment/app/wards/targets.json; the grader checks the four roster files with its own copy of the checker, wards and targets.

Review the frozen snapshot and report findings with a severity each
(Blocking / Should-fix / Advisory), a citation (file:line), and the smallest fix:

1. Were your earlier findings resolved as the adjudication says? Check the text.
2. Contract against grader: is every rule the grader's checker enforces stated in the
   rules document, with the same boundaries, and nothing stated that it does not
   enforce? This includes the file-format rules (size limit, standard JSON, repeated
   names in one object, nesting depth, unknown ids, missing items, extra keys).
3. Is the grader's copy of the checker, inputs and targets the same as the agent's
   (`tests/` against `environment/app/`)? The grader keeps some inputs split into
   small files with a roster of counts and checksums; check it reassembles exactly.
4. Does the reference in `solution/` pass: run the checker on each reference file
   and compare each cost with its target in `tests/targets.json`. Is each target
   the reference's exact cost, and do the agent's and grader's targets agree?
5. Does grading reject wrong work and accept valid work: a file that breaks one
   rule, a valid file above target, a missing file, a file with the items in a
   different order or with extra top-level keys? Could anything the agent edits
   under `/app` (the checker, the inputs, the targets) change the grade?
6. Determinism and isolation: does anything depend on time, randomness, the network
   or test order; does the grader run any code from `/app`?
7. `task.toml`: are the category, subcategory and the explanation fields accurate
   and free of claims the files do not support?
8. Anything else a platform reviewer would flag: typos, stale wording, paths that
   do not exist, statements in `instruction.md` the environment contradicts.

Write your report as Markdown with a `## Findings` list and a final
`## Verdict` line: `accept`, `accept with fixes`, or `reject`.
