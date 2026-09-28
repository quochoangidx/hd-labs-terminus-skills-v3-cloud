You are the adversarial verifier reviewer for a Terminus 3 benchmark task. The current
directory holds `instruction.md` (the agent's prompt), `environment/` (what the agent
sees under `/app`) and `tests/` (the grader: `test_outputs.py` plus its own copies of
the checker, days and targets). You have not seen the reference solution and must not
look for it.

Your job is to find work the grader accepts but should reject, or rejects but should
accept. Write plan files, do not edit anything outside `submissions/`.

1. Write 10-15 WRONG plans. Each one is a JSON plan for one day that breaks exactly one
   rule of `environment/app/docs/stand-rules.md` (or the file format it states) while
   being otherwise sound, and is shaped to slip past the checker if the checker has a
   hole: boundary minutes, buffers vs wingtip timing, size/international edge cases,
   a turn listed twice (same stand or two stands), unknown or missing ids, wrong JSON
   types (numbers or nested lists as ids, a list instead of an object), stands missing
   from the plan, extra keys, huge files, and anything else you suspect. Start from the
   shipped planner's plan (`python3 environment/app/planner/plan_day.py
   environment/app/days/<day>.json out.json`) and change it. Save each as
   `submissions/wrong-<short-name>/<day>.json` and write one line in
   `submissions/wrong-<short-name>/WHY.txt` saying which rule it breaks.
2. Write 1-2 VALID alternatives that a strict or naive grader might wrongly reject
   (for example unusual ordering, empty stand lists, extra top-level keys), saved as
   `submissions/valid-<short-name>/<day>.json` with a WHY.txt.
3. For each submission, run the grader's validity test yourself:
   `cd tests && STAND_PLANS=../submissions/<name> python3 -m pytest -q test_outputs.py -k "<day_n>_plan_is_valid"`
   (day-1 -> day_1, etc.) and record the outcome.

Finish with a Markdown report: a table of submissions (name, day, rule broken or why
valid, expected verdict, observed verdict) and a `## Findings` list of every case where
the observed verdict differs from the expected one, with the smallest fix.
