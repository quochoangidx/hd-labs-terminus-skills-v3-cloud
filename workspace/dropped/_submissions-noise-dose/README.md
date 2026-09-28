# tbrain-occupational-noise-dose-survey (retired 2026-09-28 at `base`): reference only, do not submit

Platform task `12e6eda4-8ced-4dcd-928d-7abc22b133a9`. This slot earlier held gnu-sed and then local-magnitude.

The agent repairs a hearing-conservation survey package (`noisedose`) so its worker and group dose, TWA and status report follows the programme's manual, HC-4. The package has nine departures from the manual:

- 90/5 criterion and exchange rate;
- strict 80 dBA threshold;
- counted-only sampled time;
- projection to 480 minutes;
- federal TWA formula;
- truncated TWA;
- 85/90 status bands;
- strict 140 dBC impulse;
- group mean of TWAs.

It also has two restraint traps where the manual is silent:

- T3: a survey below three quarters of its shift keeps today's 480-minute scaling, worked from the manual's sampled time;
- T4: a reading above 115 dBA stays counted at the ceiling level.

## What is here

- `tbrain-occupational-noise-dose-survey.zip`: the last uploaded bytes, rev13 (sha256 `ca750008…feef`), identical to `workspace/revision/12e6eda4-…/revisions/tbrain-occupational-noise-dose-survey-rev13.zip`.
- `SUBMISSION-…md`: note and rubric for rev13.
- `../tbrain-occupational-noise-dose-survey/`: the rev13 task tree.

## History

| Upload | Blocking stage | Findings (all Sound Verifier) |
|---|---|---|
| v11 (first upload) | quality panel | 4 Major, 2 Minor: late impulse peak, group inherits ceiling, group flag keys, rounded dose within tolerance, TWA tolerance, static-corpus lookup |
| v12 (rev10) | quality panel | 1 Major (survey-wide run budget; did not reproduce, disputed) and 1 Minor (driver swap through a writable `/app/tools`) |
| v13 (rev11) | quality panel | 1 Major: survey-name length guard |
| v14 (rev12) | quality panel | 1 Major: shift-dose cap at 102,400% |
| rev13 | difficulty | Quality panel passed; difficulty measured `base`, so the task is retired (reported by the user 2026-09-28; the per-run breakdown was not saved here) |

The other four panel axes were clean on every upload.

## Why it was stopped

`base` means fewer than 3 of 8 platform runs failed. The task is not grandfathered: its first evaluation was 2026-09-27. The grading flow says stop at `base`, not harden.

The local signal predicted this:

- The builder probe was 1/2 on Opus 5, and the one miss was trap T3 (`probe-verdict.json`).
- Trap T4 was kept in 2/2 runs.
- Re-scoring the stored diffs after rev10 gave the same 1/2, with the same T3 miss.

So the difficulty rested on a single trap that one of two local runs already handled. That is the same shape as local-magnitude, which was retired the day before.

## Lessons

- **The single-trap rule applies to tasks already in flight.** The rule ("require at least two independent traps that some local runs miss") was written for local-magnitude on 2026-09-27. This task was already uploaded then and was never re-checked against it. Four more Sound Verifier rounds (v11–v14) then went into a task whose difficulty could not hold. Before answering a panel return, check the local trap signal. If only one trap is ever missed, say so and propose a replacement before paying for more rounds.
- **A spec-conformance repair with positively stated rules is easy for frontier models.** All nine departures are explicit in HC-4, and neither local run missed any of them. Only the silence traps carry difficulty.
- **Passing the panel is not the goal.** Each Sound Verifier round cost a full revision, and every repair was tests-only and correct, but none of them could change the tier.
- **Reusable verifier techniques, all cleared by the panel:**
  - An accept/reject dose band graded at the midpoint (v11 f4).
  - Exact TWA equality (v11 f5).
  - A metamorphic relabel pass: fresh name and ids, shuffled workers, split runs, and five survey-name forms. It blocks lookup tables without a model in `tests/` (v11 f6, v13).
  - Sealing `/app` against writes by the candidate's user after installing the verifier's driver (v12 f2, `revision-v12/f2/driver_swap_probe.sh`).
  - Linear-scaling extreme doses derived from a sealed row (v14).

## Evidence

- `workspace/reports/tbrain-occupational-noise-dose-survey/`: `revision-v11/` to `revision-v14/` (receipts, sweeps, repro), `revision-ledger.json` and `quality-panel/`.
- `revision-v12/dispute-f1.md`: the run-budget dispute, never posted.
- Probes: `workspace/local-solve-probes/tbrain-occupational-noise-dose-survey-cycle-*`.
- Platform returns: `workspace/revision/12e6eda4-8ced-4dcd-928d-7abc22b133a9/v11`–`v14`.
