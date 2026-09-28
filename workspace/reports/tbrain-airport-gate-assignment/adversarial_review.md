Completed the adversarial verifier review.

- Created **15 wrong plans** and **2 valid alternatives** under `submissions/`.
- Ran the requested per-day pytest validity test for every submission.
- Recorded individual outcomes in each submission’s `RESULT.txt`.
- Full table and fixes: `submissions/REPORT.md:1`

**Findings**
- Invalid JSON containing `NaN` is accepted because Python’s decoder permits non-standard constants: `submissions/REPORT.md:31`.
- A valid JSON plan is rejected by the unstated 2,000,000-byte limit: `submissions/REPORT.md:32`.
- All other 15 cases produced the expected verdict.