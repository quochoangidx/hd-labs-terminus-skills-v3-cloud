# Final review: tbrain-occupational-noise-dose-survey

Snapshot: `packets/tbrain-occupational-noise-dose-survey-final/`. I confirmed that `instruction.md` and `environment/` are byte-identical to the r3 packet.

## Evidence gathered

- **Independent re-derivation.** I wrote my own reference from HC-4 and the r3 contract, without looking at `model.py`. It uses `math.fsum` and `Decimal` half-up and has no shared code. It reproduces every one of the 36 sealed surveys (432 workers plus group rows) and all 11 differential pairs, within the verifier's own tolerances.
- **Real verifier run.** I built `tests/Dockerfile` and ran `tests/test.sh` with the oracle-patched `/app`: 22/22 passed, reward 1. The unpatched package gives 20 failed / 2 passed (the isolation and driver tests), reward 0. `setpriv` is present at `/usr/bin/setpriv`.
- **Roster.** The SHA-256 of every `tests/expected/*.jsonl` matches ROSTER, and the row counts match.
- **Shipped copy.** `tests/shipped/app` is byte-identical to `environment/app/src` and the driver.
- **Mutants.** I scored 21 one-rule mutants of my reference against the sealed files (table in §4). One contract-wrong mutant survives, and I confirmed it survives the real verifier too (reward 1).

## Findings

### F1 (should-fix; borderline blocking): the kept short-survey step's sampled time is never discriminated

**The contract.** The instruction says to keep today's step "from the figures the manual does define". `solution_explanation` says the kept step is "worked from the manual's sampled time and measured dose". The manual's sampled time (2.4) counts every reading of 40.0 dBA or more.

**The gap.** Every graded worker below three quarters of the shift has only counted readings (>= 80 dBA) or only 0.0 runs:
- X1–X3 and Y1–Y6 in `below_three_quarters`;
- A1, A3 and B1 in `measured_nothing`;
- every differential pair.

So a legacy branch that divides by today's counted-only minutes (the r2 "reading B") gives identical outputs. That branch is `sampled = sum(m for m, lv in log if lv >= 80.0)` before `if sampled == 0`.

**Mutant.** `vr/m6` is the oracle with that one line added to `shift.py`. **It scores 22/22, reward 1, in the real verifier.** It is a plausible partial fix: a solver that leaves `measure()` returning counted minutes and computes the 2.4 sampled time separately only for the 2.5/3.3 tests lands exactly here.

**Failing input to add.** Shift 480, log `[[120, 88.0], [120, 70.0]]`: sampled 240, below 360.
- Contract: dose 100.0, TWA 85.0, "action".
- Mutant: 200.0, 88.0, "over".

**Fix.** Add this worker (and ideally one with a 0.0 run mixed in, e.g. shift 480 `[[60, 0.0], [200, 90.0], [40, 60.0]]`) to `below_three_quarters`, and re-seal. Update the toml text, whose claim of "one named test per ... kept step" currently overstates coverage of that step.

It is not blocking in the sense of rejecting a correct solution. But it leaves a stated contract clause unwitnessed and lets a wrong submission score 1.

### F2 (polish): the "ceiling makes a worker over" part of 5.3 cannot be discriminated within the limits

A reading above 115.0 contributes at least 100 × 1 × 2^10 / 480 = 213% of measured dose. A shift dose is never scaled below the measured dose within the limits, so every ceiling-flagged worker already has TWA >= 88.3, which is "over". A mutant that drops `ceiling` from the status rule is equivalent on the whole domain. This is inherent, not a suite defect; no action needed. The impulse → over path is discriminated (IM-1 A2, ST-1 U1, MN-1 A3).

### F3 (polish): the test enforces an exact key set that the instruction does not state

`_row` and `compare` assert `set(actual) == keys` at the top level and per row. The README lists what each object "holds" but never says "and nothing else". The instruction lists only the values compared. A report with an extra diagnostic key would be rejected. This is low risk, since solvers edit an existing `build_report` that already emits exactly these keys. Optional: add "and nothing else" to the README, or relax the assertion to a subset check.

### F4 (polish): differential survey names and ids are constant per kind

HC4-7001/7002 are always the short-survey pairs, 7003/7004 the ceiling pairs and 7005/7006 the nothing-measured pairs, with ids X1/Y1/N1. The sealed families use neutral sequential names. This cannot be exploited, because the pairs are also covered by sealed families and a candidate cannot see them, but it mildly contradicts "no family label reaches the package" in `seal.py`. Optional: randomise the names.

### Items checked and found sound

**(1) Assertion-to-source coverage.** Every promise has a discriminating witness except F1 and the inherent F2:

| Promise | Witnesses |
|---|---|
| Threshold 79.9 / 80.0 / 80.1 | `threshold` |
| 40.0 readings in sampled time | SA-2 B2 |
| 0.0 runs | `paused_runs` |
| Partial at exactly 3/4 | TQ: 450/600, 360/480, 45/60, 1080/1440, 458/610 |
| One minute below 3/4 | Y5 457/610, Y2 67/90 |
| Whole shift / longer | `whole_shift` |
| Short-survey s >= 480 unprojected | Y1 500/720 |
| Levels above ceiling to 140.0 | Z1, Z2 115.1, Y1 118.5, Y2 131.2 |
| Ceiling 115.0 not flagged | `ceiling_level`, L-1500 |
| Impulse 139.9 / 140.0 | IM-1 |
| Bands 81.9 / 82.0 / 85.0 / 85.1, and unrounded 81.95+ / 85.0x / 85.05+ | ST-1 |
| Rounding on both sides | RO-1 |
| Null TWA | TW-1 A2, quiet members |
| Quiet member included | QM-1, QM-2 |
| Nothing-measured member included as 0.0 | MN-2 group 94.494 → 84.8 action |
| Group without flags | MN-1 G2 (impulse member, group "below") |
| Group code order | RO-2: `0`, `9A`, `A`, `A1B2C3D4`, `AB`, `ZZ` |
| Section 1 limits | 300 workers / 40 codes / 1,500 runs / 2,880 minutes / 500 peaks / shifts 60–1,440 / 8-character codes / 12-character ids |

No test asserts anything outside the contract apart from F3. Every graded survey is checked in-test against 1.4 and against the trap inputs its family declares.

**(2) Oracle correctness.** Checked three ways:
- `model.py` is independent of the package and matches the manual rule by rule. `counted_at` keeps the 115 cap only above the ceiling. `shift_dose` puts the kept branch only under 3/4, fed by 2.4 sampled time. `mean` covers all members. `Decimal(value)` gives exact half-up.
- `fix.patch` agrees on every sealed survey. Its `floor(10x + 0.5)` differs from exact half-up only within float noise of a .x5 value, and `near_rounding_edge` excludes those (margin 1e-7 dB).
- Hand spot-checks:

| Case | Input | Result |
|---|---|---|
| Y3 | shift 60, `[[1, 99.0]]` | measured 5.29133 × 480 = 2539.84, TWA 99.0 |
| Y5 | 457/610 (1828 < 1830) | kept branch × 480/457 = 317.48 |
| TQ B2 | 458/610 | projected × 610/458 = 403.46 |
| Z1 | 1,440-minute shift | 213.33 (140.0 counted at 115) + 149.90 = 363.23, TWA 90.6 |
| Z2 | | 64000 + 78.745 = 64078.75, TWA 113.0 |
| MN-2 G1 | | (0.0 + 188.988) / 2 = 94.494, TWA 84.8, "action" |
| QM-2 G1 | | (0 + 0 + 200) / 3 = 66.667, TWA 83.2, "action" |
| ST-1 T1 | unrounded 85.0x | 85.0 "action"; T2 → 85.1 "over" |

**(3) Boundaries and equivalence.**
- Range ends are hit as listed in (1).
- Tolerances match the instruction exactly: relative 1e-6 for doses >= 1 and absolute 1e-6 below; `twa` within 1e-6 of the tenth.
- Contract-valid alternatives pass: my fsum/Decimal reference; `round()`, which differs only at exact binary halves and is excluded by the seal; a log10-based TWA; any key order or whitespace (the output is parsed as JSON); integer `dose` or `twa` (accepted).
- Equivalent mutant noted: kept branch `<=480` versus `<480` gives the same value at s = 480.

**(4) Mutation geometry.** Mutants scored against the sealed files:
- **Killed:**
  - short-survey projection to the shift, or zero when nothing was sampled;
  - short survey left unprojected;
  - kept branch comparing against the shift, or targeting the shift;
  - kept branch scaling down when s >= 480;
  - clamp dropped;
  - 0.0 runs counted as sampled time;
  - floor rounding;
  - threshold `>80`;
  - impulse `>140`;
  - group excluding members without a TWA, or only members with no readings;
  - group mean of TWAs;
  - bands `>=85` over or `>82` action;
  - 3/4 test strict;
  - ceiling flag `>=115`;
  - group inheriting flags.
- **Survived:** the counted-only sampled time in the kept branch (**F1**, contract-wrong), plus the equivalent mutants `<=480` and drop-ceiling-from-status (F2).

**(5) Preservation-side differentials.** All three pair kinds encode obligations the contract actually imposes:
- the kept branch ignores `shift_minutes` (every pair is below 3/4 on both sides);
- a reading above the ceiling counts exactly like one at 115.0;
- a survey with nothing measured gives 0.0 regardless of shift.

The shipped-equality precondition holds for each. The differentials are redundant with the sealed families and add no independent coverage of F1 (no quiet readings in any pair).

**(6) Harness and isolation.** All sound:
- Candidate runs are demoted to uid 65534 via `setpriv --no-new-privs --clear-groups`, in their own session, with a clean env and `python3 -I -S`, from fresh temp directories, on a file always named `survey.json`.
- The process group is killed after each run.
- `/tests` and `/logs/verifier` are 0700 root.
- The shipped copy is 0700, owned by uid 65533.
- The isolation test has a positive control.
- The driver bytes are recorded at import, before any candidate run; the verifier's copy is installed with `os.replace`, re-checked in-test, and `cmp`-ed again in `test.sh`.
- The expected files are SHA-pinned.
- It is deterministic: seeded generation, sealed data, 2.2 s runtime.
- A candidate grandchild that calls `setsid` could outlive `killpg`, but it has nothing reachable to tamper with: the stage directories are root 0755/0644 and the expectations are unreadable. Not exploitable.

**(7) task.toml and folder.**
- The counts are accurate: 22 tests, 21 sealed families, 36 surveys, 432 workers, 11 pairs.
- There are no model pass rates. The "Oracle 1 / unfixed 0" statement matches my run.
- The 19 wrong-submission and 28-mutant claims cannot be checked from the folder. Their implied coverage is contradicted in one respect by F1, so the "per kept step" wording should be tightened after the fix.
- Operations / Compliance is a good fit (a regulatory noise-exposure compliance report). The difficulty and solution explanations match the files and the patch.
- `solve.sh` applies the patch correctly (`cd /`, `-p1`).
- The authoring tools (`jobgen.py`, `seal.py`, `model.py`) sit under `solution/`, which the agent never sees. That is acceptable.
- The instruction and README style is clean and task-specific.

## Verdict

**Accept with fixes.** The oracle, model, harness and isolation are correct; I reproduced every sealed expectation independently; the natural over-repairs of both kept steps are killed. One required fix (F1): add a worker below three quarters of the shift with a sub-threshold reading (and optionally a 0.0 run), re-seal, and adjust the toml coverage wording. Without it, a solver who divides the kept step by today's counted-only minutes scores 1. F2–F4 are optional polish.

## Recheck (repaired task at workspace/tasks/tbrain-occupational-noise-dose-survey)

I read only that folder. `instruction.md` and `environment/` are byte-identical to the final snapshot.

The diff against the snapshot is confined to:
- `tests/expected/below_three_quarters.jsonl`, which gains one row;
- that file's ROSTER line;
- `test_outputs.py`: the `TRAP_INPUTS` entry and the subset key checks;
- `jobgen.py`: a new survey named "LATE" and the family's trap-input set;
- `seal.py`: late numbering, so no earlier survey name or expectation moves;
- `task.toml` `verification_explanation`.

**(a) F1: closed.** The new survey HC4-0037 contains:

| Worker | Input | Sealed answer | Hand check |
|---|---|---|---|
| V1 | shift 480, `[[120, 88.0], [120, 70.0]]` | 100.0 / 85.0 / action | my witness |
| V2 | shift 720, `[[200, 90.0], [100, 0.0], [100, 65.0]]` | 211.653473596 / 88.2 / over | sampled 300 (below 540); 132.2834 × 480/300 = 211.6535; TWA 88.245 → 88.2 |

My independent reference reproduces all 37 sealed surveys and the 11 pairs.

In the rebuilt verifier (`tests/Dockerfile` plus `test.sh`, on disposable copies):
- oracle: 22/22, reward 1;
- unfixed package: 20 failed, reward 0;
- counted-minutes mutant (`sampled` = minutes >= 80 in the kept branch): now fails `test_survey_below_three_quarters_keeps_todays_projection`, reward 0;
- new kept-branch mutant counting 0.0 runs: also fails only that test, reward 0.

**(b) F3: closed.** `_row` and `compare` now use `set(actual) >= keys`.
- An oracle variant adding a worker key `"note"` and a top-level key `"edition"`: 22/22, reward 1.
- An oracle variant dropping `"impulse"`: 20 failed, reward 0.
- The values and types of the listed keys are still compared exactly.

**(c) Counts: correct.** 22 tests, 21 sealed families, 37 surveys, 434 workers and 11 pairs match the files. The new wording (further keys ignored, a test for each kind of figure left to today's code, counted-minutes variant) matches the suite. The 20 wrong-submission, 29-mutant and 4-alternative claims cannot be checked from the folder, but they are consistent with my runs.

**(d) No regressions.**
- The ROSTER hashes all verify, and only the one ROSTER line changed.
- `model.py`, `fix.patch`, `solve.sh`, `tests/Dockerfile`, `test.sh` and the shipped copy are unchanged.
- Widening `below_three_quarters` to allow 0.0 runs is correct, because V2 carries one.
- F2 and F4 remain optional polish.

**Recheck verdict: accept.**
