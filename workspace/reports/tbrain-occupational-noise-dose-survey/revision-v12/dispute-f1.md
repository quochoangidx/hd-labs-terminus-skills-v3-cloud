Task 12e6eda4-8ced-4dcd-928d-7abc22b133a9 (tbrain-occupational-noise-dose-survey), v12 panel, Sound Verifier finding 1 (Major): contest.

Claim: an otherwise correct reducer that processes only the first 1,500 runs across the survey passes.

Contract: manual HC-4 1.4 ("a worker's log holds from 0 to 1,500 runs") is a per-log limit, and it is graded that way already.

Counterexample, on the exact submitted bytes (snapshot de85f241...): tests/expected/limits_logs.jsonl is one survey, HC4-0036, with three workers in order: L-1500 (1,500 runs), L-2880 (two 1,440-minute runs at 88.0 and 81.0 dBA) and L-PEAKS (2 runs, 500 peaks). A survey-wide budget of 1,500 runs therefore drops all of L-2880's and L-PEAKS's runs after L-1500. L-2880's expected dose is non-zero, so the full-report comparison fails.

Three variants of the described implementation, scored against the submitted verifier, all got reward 0 on test_section_one_limits_reached:
- runs truncated after the first 1,500 across the survey;
- workers omitted once the survey total passes 1,500 (the "or omits B" variant);
- the budget counted over readings only.

Receipts: revision-v12/repro/f1-survey-wide-run-budget.json, f1b-workers-dropped-after-budget.json, f1c-budget-over-readings.json.
