# Final review: tbrain-climate-observer-monthly-summary (reviewer D)

Snapshot: `workspace/tasks/tbrain-climate-observer-monthly-summary/`. I did not modify any file there. All
scratch work was done in my session scratchpad.

**Visibility note.** My first command of this turn ran one `diff` of this task's `instruction.md` against the
r3 contract packet under `workspace/reports/`, before I noticed that path was now off-limits. It showed only the
fallback sentence I had already reviewed in r3. I opened nothing else under `workspace/reports/` apart from this
output file.

## What I ran

1. **Resealed from scratch.** I copied the task, ran `solution/seal.py`, and compared the output with the
   snapshot. `tests/expected/*` (all 16 families plus ROSTER) and `tests/shipped/` came out byte-identical.
2. **Real harness in Docker.** I built `environment/` and `tests/`. I then applied `solve.sh`, copied `/app` into
   the verifier image, and ran `tests/test.sh` with `--network none`.
   - Oracle: 18/18 pass, reward 1.
   - Unmodified package: 16 fail and 2 pass (the two harness tests), reward 0.
3. **Independent cross-check.** My own handbook reference, written in r1-r3 and never looking at `model.py`,
   agrees with the sealed expectations on all 99 station summaries.
4. **Mutant sweep.** I ran 39 mutants of the oracle package in-process against the sealed expectations. The
   harness mirrors the verifier's `_value` typing rules. This exercises the sealed comparisons only, not the
   shipped-copy differentials.

## Verdict: **accept-with-fixes**

There is nothing blocking. One should-fix: no witness covers the "or trace" clause of 1.3 (F1). The rest are
polish.

## Findings

**F1 (should-fix): the trace clause of 1.3 has no witness.**
Citation, handbook 1.3: "The amount **or trace** the observer enters when the gauge is next read is an accumulated
amount".

A `T` after an `A` run ends the accumulation, so the next amount is an ordinary day's precipitation and shifts at a
morning station. No graded form contains a `T` straight after an `A`:
- `accumulated_morning` always writes a numeric amount there;
- `generated` puts `A` runs only at afternoon stations.

Surviving mutant `trace_keeps_unread`:
```python
credited = day if unread else day - shift
if entry["precip"] != "T":
    unread = False
```
It passes every family. The failing input: hour 7, form day d `A`, form day d+1 `T`, form day d+2 `0.40`. The
correct answer credits 0.40 to day d+1. The mutant credits it to day d+2.

A solver who reads a trace as "the gauge was not really read" writes exactly this. Fix: add one such station to
`accumulated_morning`. `trap_inputs` already classifies the T as accumulated, so the family's declared trap set is
unchanged. See also F4, because the differential would mis-handle a T there.

**F2 (polish): `test_rule_4_4` does not reach a whole-degree half, despite its docstring.**
Citation, test docstring: "Each day's mean is rounded to the whole degree before the 65 F base; halves both sides
of nought."

`fam_degree_days` forces hi+lo to be odd, so every day's mean ends in .x5 hundredths. Only day 4 (64.45, double
rounding) and day 3 (65.0) are hand-placed. No day's mean is ever exactly k.5 degrees, so half-up against
half-even and half-away at the whole degree is not tested here.

Degree-day-only mutants `dd_half_even` and `dd_half_away` pass `degree_days` but are killed elsewhere (`limits`,
`generated`, `means`, `morning_maximum` and others). The task still rejects them. What is wrong is the
attribution in the docstring and in task.toml, which says each mutant "score[s] 0 on [its] own named test".

Fix: add a positive k.5 day with k even (e.g. 70.0/59.0 → 64.5 → 65) and a negative one (e.g. -4.0/-5.0 → -4.5 → -4)
to the family, or soften the docstring.

**F3 (polish): the verification_explanation's mutant claim is slightly overstated.**
The whole-degree rounding mutants of F2 die on other tests, not on test_rule_4_4. Either fix F2 or reword to
"each is rejected, most on their own named test".

**F4 (polish): the accumulated differential is fragile to a T accumulated amount.**
Citation, `test_accumulated_amount_keeps_its_form_day`: the differential keeps `accumulated(s)` positions
unchanged and compares against the shipped copy, which counts `T` as 1 hundredth.

If F1's fix adds a T accumulated amount, a correct solution gives 0 against the shipped copy's 0.01 and is wrongly
rejected. Fix: in the differential, rewrite a kept accumulated `T` to `0.00` too, or exclude T positions from
`keep`.

**F5 (polish): stale "complete" wording in solution-side and agent-visible code.**
- `fix.patch` docstring: "for a complete month".
- `model.py`: "Trap T2 input: … not complete for temperature".
- Shipped `temperature.complete`: "complete for temperature".

The handbook now says "well-observed" (2.8). The section 6 key is still `complete`. Harmless, but aligning the
solution comments to "well-observed" would help. Leaving the shipped package's docstring as it is is fine, because
it is part of the drift the agent repairs.

**F6 (polish): the instruction says "well-kept" where the handbook says "well-observed".**
Citation, instruction: "the mean temperature of a well-kept month is off". This is a symptom sentence and
probably deliberately informal, but using the defined term would remove a small doubt.

## (1) Assertion-to-source coverage

Every assertion traces to a visible sentence:
- full-summary equality → section 6 and every rule;
- integer typing → "Counts and degree days are integers";
- number-or-integer acceptance for temperature and precipitation → "JSON number whose decimal value…";
- station order → instruction and section 6;
- the two differentials → the instruction's "keeps what the package does with it today";
- the byte check on the driver → instruction.

Coverage of rules and promises (✓ = a discriminating witness, confirmed by a mutant that dies there):

| Source | Witness / test | Mutant killed |
|---|---|---|
| 1.2 trace nought, traces-only month | traces | trace_one |
| 1.3 accumulated amount stays on form day (within month, in `next`, 1-6 unread, same-day collision) | accumulated_morning (+ differential) | shift_accumulated, drop_accumulated, accum_to_prev, overwrite_total |
| 1.3 "or trace" | **none (F1)** | trace_keeps_unread survives |
| 1.4 half up, negatives | means, many | half_even_means, half_away_neg |
| 2.1 `M` still empties the gauge | morning_precipitation | M_as_unread |
| 2.2 hour 0/11 morning, 12/23 afternoon | hour_edges | noon_morning, hour11_afternoon, midnight_afternoon |
| 3.1/3.2/3.3/3.4 incl. form day 1 out, `next` in | morning_maximum, morning_precipitation, hour_edges | shift_minima, no_precip_shift, next_ignored |
| 2.6-2.8 gap count, exactly 5 vs 6, larger of the two | gap_count, gappy_months | complete_lt5, complete_max_only |
| 4.1 means, null when no max | means, gappy_months | floor_temp, half_* |
| 4.2 latest tie | tied_temperatures | tie_high_first, tie_low_first |
| 4.3 standard means (well-observed) | well_observed_mean | mean_unrounded_std |
| 4.3 not reached, keep daily-mean figure; null only when no day has a mean | gappy_months (+ differential) | mean_all_months, mean_null_gappy |
| 4.4 per-day whole-degree rounding, 64.45, 65.0 | degree_days | dd_double_round, dd_trunc (half rules: F2) |
| 4.5 inclusive 90/32/32/0 | thresholds | thr*_strict (all four) |
| 5.1 sum, not overwrite | accumulated_morning (20.00 + 20.00) | overwrite_total |
| 5.3 inclusive 0.10/1.00 | heavy_days | heavy10_strict, heavy100_strict |
| 5.4 latest tie, null | tied_precipitation, traces | greatest_first |
| section 6 per-pair nulls | gappy_months (all max M, min present) | covered |
| section 6 decimal exactness | limits etc. | float_precip |
| Instruction limits: 40 stations, 1950-01, 2099-12, leap and common Feb, -60/130, 20.00, 620.00 month, six `A` | limits, gap_count | leap_wrong, cap_precip_month |
| Station order, labels | generated relabel (reverse-sorted ids, shuffled) | sorted_stations |
| Driver byte-identical | test_submitted_driver_unchanged + test.sh `cmp` | n/a |

## (2) Sound Verifier

All 39 mutants except `trace_keeps_unread` (F1) are rejected:
- caps and floors;
- hour boundaries at noon, 11 and midnight;
- shifting minima;
- ignoring `next`;
- tie direction, three sites;
- half-even and half-away, globally and in degree days;
- double rounding and truncation in degree days;
- `<` for `<=` on every threshold;
- `<5` for `≤5` completeness;
- mean over all months, null for gappy months;
- the unrounded standard mean;
- overwrite instead of add;
- M treated as unread;
- dropping, shifting or back-dating accumulated amounts;
- a month-length slip in Februaries;
- sorting stations;
- float-summed precipitation.

**Contract-valid alternatives are accepted.** `int_temps`, which writes integer JSON for whole-degree
temperatures, passes. `_value` accepts int or float for number keys, and extra keys, key order and whitespace are
irrelevant because the output is parsed as JSON. Fraction or exact-integer arithmetic yields the same correctly
rounded double as the sealed decimal.

**The differentials are sound for the current data.**
- The gappy differential forces hour 17, where the shipped crediting equals the correct one, and every form stays
  above five gaps.
- The accumulated differential leaves exactly one nonzero amount per station, with no threshold equalities, so the
  shipped copy's strict comparisons and first-tie rule do not come into play. The exception is the latent
  T-accumulated case in F4.

## (3) Correct reference

`fix.patch` and `model.py` both follow the handbook everywhere I checked, including the two kept behaviours:
- **Accumulated amount on its form day.** In the patch, `unread` is set on `A` and cleared by the next amount or
  `T`. The model mirrors this.
- **Month that is not well-observed.** Both keep the mean of the daily means, half-up to tenths. It is null only
  when no day has both readings.

M after A is barred by 1.5, and both implementations treat an `M` as clearing nothing, consistent with 2.1. My
independent reference matches all 99 sealed station summaries, and resealing reproduces the expectations byte for
byte.

## (4) Protected ground truth and harness

- **Expectations are sealed.** They sit in `/tests` (mode 0700, root), and each file is pinned by SHA-256 and row
  count in ROSTER.
- **The verifier runs separately from the agent.** task.toml sets `environment_mode = "separate"`.
- **Candidate code is demoted.** It runs through `setpriv` as uid 65534 with no new privileges, in its own session
  (process group killed afterwards), with `-I -S` and a sanitized environment, from a fresh working directory, on
  a neutral `form.json`.
- **`/app` is closed before any candidate run.** The verifier's own driver is `os.replace`d onto the documented
  path, and the whole tree is `lchown`ed to root with group and other write stripped. Symlinks are not followed.
- **The driver check holds.** A symlinked `/app/tools` would fail the `lstat` mode check in
  `test_submitted_driver_unchanged`. `test.sh` also `cmp`s the driver after pytest.
- **The shipped copy is separate.** It runs as uid 65533 under a 0700 directory.
- **Probe tests pass.** `test_candidate_cannot_read_verifier_state` covers the targets and has a positive control.
- **No case label reaches the candidate.** It sees the form only. Network names and ids carry no family label, and
  the generated family is relabelled at run time.

No gaps found.

## (5) Determinism

- Expectations are regenerated identically from `SEED = 20260927`.
- The only randomness at run time is the relabel seed from `os.urandom`, which changes names, ids and order but no
  figure.
- A single run takes about 1.2 s against a 1500 s internal deadline and a 1800 s verifier timeout.
- No network, clock or locale dependence (LANG=C.UTF-8 and utf-8 file I/O cover the non-ASCII network names).

## (6) task.toml metadata

- `difficulty_explanation`, `solution_explanation` and `verification_explanation` are accurate and specific. They
  describe the eight repairs, the two kept behaviours and the chains of definitions behind them, the harness, the
  oracle and no-op results (verified: 1 and 0, 16 of 18 failing), and the mutant sweep.
- Overstatements: F3, and F2's docstring claim that surfaces in "daily means of 64.45 and exactly 65.0" (true) and
  "halves both sides of nought" (true for means, not for degree days).
- `difficulty = "core"`, Science/Earth, the tags and the 4 h estimate are consistent with the task.
- Style: the prose is long single paragraphs but readable, with no LLM tics that stood out.

## (7) Task-visible style

- The instruction is three paragraphs:
  - the symptom list, in a network-office voice;
  - the restraint and fallback rule, whose wording now covers "a reading, … what is done with it, or … a figure";
  - the promised domain.
- The handbook is consistent: section cross-references (2.6, 2.8, 2.9, 4.1, 4.3, 5.2-5.4) resolve, and the r3
  gaps are closed. The `M`-empties-gauge sentence is now in 2.1, and the fallback sentence names what is done
  with a reading.
- The README matches the input format.
- Only nit: F6 ("well-kept").

## Required before submission
- F1: add a morning-station witness with `A` → `T` → amount, and make the differential T-safe (F4).

## Optional
- F2/F3: add whole-degree half witnesses to `degree_days`, or soften the docstring and the task.toml claim.
- F5/F6: align the wording.
