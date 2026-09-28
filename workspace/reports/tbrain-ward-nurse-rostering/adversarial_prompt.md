You are the adversarial verifier reviewer for a Terminus 3 benchmark task. The current
directory holds `instruction.md` (the agent's prompt), `environment/` (what the agent
sees under `/app`) and `tests/` (the grader: `test_outputs.py` plus its own copies of
the checker, wards and targets). You have not seen the reference solution and must not
look for it.

Your job is to find work the grader accepts but should reject, or rejects but should
accept. Write roster files, do not edit anything outside `submissions/`.

1. Write 10-15 WRONG rosters. Each one is a JSON roster for one ward that breaks exactly one
   rule of `environment/app/docs/roster-rules.md` (or the file format it states) while
   being otherwise sound, and is shaped to slip past the checker if the checker has a
   hole: cover by grade (seniors counted as registered, HCAs not), leave, rest
   between days and after nights (runs touching the first or last day), consecutive
   days, lower-case or other shift codes, rows of the wrong length or type, missing or
   unknown nurses, wrong JSON types, extra keys, NaN, huge files, and anything else
   you suspect. Start from the
   shipped planner's roster (`python3 environment/app/planner/plan_ward.py
   environment/app/wards/<ward>.json out.json`) and change it. Save each as
   `submissions/wrong-<short-name>/<ward>.json` and write one line in
   `submissions/wrong-<short-name>/WHY.txt` saying which rule it breaks.
2. Write 1-2 VALID alternatives that a strict or naive grader might wrongly reject
   (for example unusual key order, extra top-level keys, a roster exactly at a limit), saved as
   `submissions/valid-<short-name>/<ward>.json` with a WHY.txt.
3. For each submission, run the grader's validity test yourself:
   `cd tests && WARD_ROSTERS=../submissions/<name> python3 -m pytest -q test_outputs.py -k "<ward>_roster_is_valid"` and record the outcome.

Finish with a Markdown report: a table of submissions (name, ward, rule broken or why
valid, expected verdict, observed verdict) and a `## Findings` list of every case where
the observed verdict differs from the expected one, with the smallest fix.
