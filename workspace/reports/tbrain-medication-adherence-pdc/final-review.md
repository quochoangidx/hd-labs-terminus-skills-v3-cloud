# Final review — tbrain-medication-adherence-pdc (frozen folder, r4 contract)

**Verdict: no blocking findings. Two should-fix items and a few polish items.**

What I checked by running code:
- **Sealed files.** I applied solution/fix.patch to a scratch copy of environment/app. Its report equals solution/model.py on all 62 claims files in tests/expected, including every differential side (compared with sorted-key JSON).
- **Random fuzz.** A 3,000-file random fuzz (seed 1; years 2000–2099; days supply 0/1/30/90/100/101/365/random; three drugs over two classes; stays; members outside the measure) found 0 differences between the patch and the model.
  - Classes rarely reached ten members in the measure in this fuzz, so the reportable path is covered mainly by the sealed files.

## Assertion-to-source coverage

| Rule / promise | Family (witness) | Discriminates shipped / over-repair |
|---|---|---|
| 3.1 start day | start_day (Jan 1, Feb 29, Dec 31) | yes |
| 3.2 carry-over, same-day file order, out-of-order export | carry_over C1–C4 | yes |
| 3.2 different drugs don't move | other_drugs D1–D4 | yes |
| 2.3 earliest fill date | index_order | yes |
| 2.1 zero-supply lines | adjustment_lines N1–N5 | yes (index, measure test, no row/class) |
| 2.4 distinct dates | measure_dates E1–E5 | yes |
| 2.4 2 Oct cutoff | index_cutoff (2023/2024/2000, Oct 1/2/3) | yes |
| 2.5 year-end period | year_end_period | yes |
| 2.6/3.4/4.1 stays | stays H1–H6 (single day, 60 days, 31 period days, PDC 0) | yes |
| 1.2 half-up | rounding (1.25, 33.75) and rates 6.25, 43.75 | yes (floor and half-even both fail) |
| 4.2 ≥80.0 and in measure | adherence J1–J5 | yes |
| 5.1/2.7 rate base | reportable_rate (30.0, 43.75) | yes |
| README ordering, digits before letters | report_order | yes |
| 1.3 limits | limits_members, limits_fills, plus year 2000/2099 and supply 0/365 spread across families | yes |
| kept: outside-measure span | outside_measure + 3 differential pairs | yes (year-end and stay-subtraction over-repairs fail) |
| kept: small-class divisor | small_class (37.5, 100.0, 0.0, 6.25, 2/7 → 28.6) | yes |
| kept: over-limit 100 days | over_limit + 3 differential pairs | yes (full supply and "no coverage" both fail) |
| driver byte identity | test_submitted_driver_unchanged + cmp in test.sh | yes |

Every test traces to a visible sentence of the spec, the README or the instruction.

## Findings

1. **SHOULD-FIX — instruction.md:5, "first fills on every day of the year".**
   - The sealed files contain a few dozen distinct first-fill days, not all 365/366.
   - Read literally, this promise about what will be measured is false. It is harmless to grading, but it overstates the tests.
   - Suggested repair: reword it to something like "first fills on any day of the year, including 1 January, 29 February, 2 and 3 October and 31 December". Alternatively, add a family with one member per day of a leap year.
2. **SHOULD-FIX (minor coverage gap) — tests/expected/05-adjustment_lines.jsonl.**
   - No file has a member with only zero-supply lines in a class that *other* members fill. The class STA of N4 is filled by nobody.
   - Rule 2.1 plus the README ("how many members have a fill of the class") governs the class `members` count here, but it is never exercised.
   - Counterexample: in 2026, member A fills class C on 01-01 and 03-01 (30 days each), and member B has one zero-supply line of class C.
     - Correct output: C `members` 1.
     - A candidate that counts every member with a line of the class gives 2. That candidate would also emit an extra member row, which N4 already catches, so the risk is small.
   - A one-line fix: add such a member to the third adjustment_lines file.
3. **POLISH — tests/test_outputs.py:106-127.** Candidate processes run with `start_new_session=True` and are killed with `killpg`. A candidate that double-forks with `setsid` escapes the kill and can keep running as uid 65534 for the rest of the run.
   - It cannot write /app (sealed) or read /tests, /logs/verifier or the shipped copy.
   - So at most it can carry state between its own jobs through /tmp or /dev/shm. That gives no path to expected values.
   - Not exploitable for reward. Optionally kill all processes of uid 65534 (`pkill -9 -u 65534`) after each job.
4. **POLISH — solution/jobgen.py:generated.** The seeded family is thin: 2 files of 2–7 members, every member in the measure, and no class reportable.
   - As a result, the relabel test re-checks only governed figures of small files. The named families carry the load.
   - Consider a third seeded file with ≥10 members in one class so that a rate is graded under fresh labels.
5. **POLISH — task.toml verification_explanation.**
   - "Forty-one one-edit mutants … Three contract-valid alternatives score 1" cannot be checked from the folder: no mutant harness is shipped. Keep it only if the evidence is recorded elsewhere.
   - All other numbers match the files:
     - 21 tests, 22 sealed files, 6 differential pairs;
     - PDC 1.25/33.75/80.0, rates 6.25/43.75;
     - index dates of 1/2/3 October in 2000/2023/2024;
     - 100 members, 40 class codes, 400 lines, 10 stays / 60 stay days, supply 0 and 365, years 2000 and 2099;
     - 31 period days (H5).
6. **POLISH — README key `fills` holds claim lines.** The README says so explicitly. No change is needed, but it is the one naming wrinkle left in the task-visible text.

## Comparator (semantic-equivalence policy)

- Key order is free, and extra keys at the top level and in rows are ignored.
- `pdc` and `rate` accept any JSON number equal to the reported tenth, so an int `80` is accepted as well as `80.0`.
- All other keys require an equal value of the same JSON type.
  - bool vs int is distinguished: Python `type(True) is bool`, so a `1` for `in_measure` is rejected, as the contract says.
- Row counts and order are enforced.

I found no contract-valid output that it rejects.

## solution/model.py and solution/fix.patch

**Rule by rule.** Both are correct against the r4 spec:
- start on the fill date, with carry-over per drug in (date, file position) order;
- zero-supply lines filtered, which is harmless in the patch's coverage: `start + 0` adds no days, and `after_last` can only move to a date that later fills are not before;
- index = minimum fill date;
- measure test = distinct dates ≥2 and index ≤ Dec 31 − 90 (= 2 October in every year);
- year-end period with stays removed from both terms;
- half-up rounding;
- adherent = in the measure and ≥ 80.0;
- a reportable class divides by in_measure.

**The three kept figures follow the shipped code exactly:**
- over-limit fills cover min(days, 100);
- members outside the measure keep the span from the index date to min(last covered day, 31 Dec), with stays kept in the period;
- a class below ten divides by `members`.

**Float half-up in the patch is safe.**
- Every exact half tenth reachable with ≤366 period days or ≤100 members is dyadic.
- Non-half values sit at least 1/732 away from a half.
- No PDC lies in [79.95, 80).

## Silent-case grading scope

Sound.
- **Members outside the measure:** `period`, `covered` and `pdc` are skipped outside their own families. Their `in_measure` and `adherent` (governed) are always compared.
- **Classes below ten:** the `rate` is skipped outside its own families. The counts are always compared.
- **Input gating:** `load()` refuses over-limit fills and zero-supply lines in families that do not grade them. So no governed figure elsewhere can depend on a kept step.
- **Differential pairs:** each pair differs only in a stay after coverage or in an over-limit supply value. A spec-correct candidate gives identical figures on both sides, so the pairs reject only over-repairs.

## Isolation and privilege

- **test.sh:**
  - initializes reward to 0 and closes /tests and /logs/verifier (mode 700);
  - makes /app readable;
  - runs pytest as root from a fresh mktemp directory;
  - rewards only if pytest passes *and* the driver on disk still equals the verifier copy.
- **test_outputs.py, before any candidate code runs:**
  - records the delivered driver's bytes;
  - `os.replace`s its own copy onto the path;
  - `lchown`s /app and removes group/other write, without following links.
- **Candidate and shipped runs:**
  - The candidate runs as uid 65534 with `setpriv --no-new-privs --clear-groups`, `env -i`, `python3 -I -S`, a fresh cwd and the same neutral file name for every job.
  - The shipped copy runs as uid 65533 in a 0700 directory.
- **Probe:** a probe test proves /tests, ROSTER, the shipped copy and /logs/verifier are unreadable, with a positive control.
- **Integrity:** expected files are pinned by SHA-256 and row count.
- **Verifier image:** separate, with no network.

The only gap is finding 3 (setsid escape), and it is not exploitable for reward.

## Determinism

- Sealed files use fixed seeds.
- The only run-time randomness is the relabel seed from `os.urandom`. It is printed on failure, and the reference is invariant under it:
  - class order is preserved by a sorted-to-sorted mapping;
  - the year moves ±28, so leap years and the 2 October cutoff are unchanged;
  - reshuffling same-day fills of one drug leaves the union of coverage unchanged;
  - ids and drug codes stay unique.
- Budget: about 70 driver runs within a 1,500 s deadline and a 1,800 s timeout.

## Folder quality and style

- The layout is clean: shipped copies under tests/shipped, generators under solution/, no stray files, and a digest-pinned base image.
- The task-visible prose (instruction, spec, README) is consistent with the r4 contract. Apart from finding 1, it makes no claims the files do not support.
