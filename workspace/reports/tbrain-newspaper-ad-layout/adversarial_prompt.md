You are the adversarial verifier reviewer for a Terminus 3 benchmark task. The current
directory holds `instruction.md` (the agent's prompt), `environment/` (what the agent
sees under `/app`) and `tests/` (the grader: `test_outputs.py` plus its own copies of
the checker, editions and targets). You have not seen the reference solution and must not
look for it.

Your job is to find work the grader accepts but should reject, or rejects but should
accept. Write layout files, do not edit anything outside `submissions/`.

1. Write 10-15 WRONG layouts. Each one is a JSON layout for one edition that breaks exactly one
   rule of `environment/app/docs/makeup-rules.md` (or the file format it states) while
   being otherwise sound, and is shaped to slip past the checker if the checker has a
   hole: off-page and overlapping ads, ads not resting across their full width,
   the front-page strip and page limits, competitors on facing pages (page 1, the last
   page), a booked ad left out, floats/strings/booleans as positions, unknown ids,
   wrong JSON types, extra keys, NaN, huge files, and anything else you suspect. Start from the
   shipped planner's layout (`python3 environment/app/planner/plan_edition.py
   environment/app/editions/<edition>.json out.json`) and change it. Save each as
   `submissions/wrong-<short-name>/<edition>.json` and write one line in
   `submissions/wrong-<short-name>/WHY.txt` saying which rule it breaks.
2. Write 1-2 VALID alternatives that a strict or naive grader might wrongly reject
   (for example an ad ending exactly on the page foot, a page exactly at its ad limit, extra keys), saved as
   `submissions/valid-<short-name>/<edition>.json` with a WHY.txt.
3. For each submission, run the grader's validity test yourself:
   `cd tests && AD_LAYOUTS=../submissions/<name> python3 -m pytest -q test_outputs.py -k "<edition>_layout_is_valid"` and record the outcome.

Finish with a Markdown report: a table of submissions (name, edition, rule broken or why
valid, expected verdict, observed verdict) and a `## Findings` list of every case where
the observed verdict differs from the expected one, with the smallest fix.
