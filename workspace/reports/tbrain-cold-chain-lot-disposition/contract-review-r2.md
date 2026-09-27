# Contract review r2: tbrain-cold-chain-lot-disposition

Packet read: `contract-review-packet-r2/instruction.md` and everything under `contract-review-packet-r2/environment/` (Dockerfile, .dockerignore, README, SOP, driver, `src/coldchain/*.py`, example job). No other path was opened.

## Status of r1 findings

| r1 | Status | Evidence |
|---|---|---|
| F1: MKT undefined when every reading has weight 0 (blocking) | **Closed** | 1.4 now requires "at least one pair of consecutive stamps no more than 30 minutes apart". Under the kept package step (see N1 below), a gap opener's hold is also ≥31, so the total hold of any lot is > 0. |
| F2: readings outside the span vs the silence clause (should-fix) | **Closed** | 1.4: "every reading of a job lies within the table's span (2.5)". 2.6 no longer mentions the span. |
| F3: silence clause had no identifiable target (should-fix) | **Closed** | The clause is now "Where the SOP names a figure but gives it no value for some input". There are two identifiable targets: the hold of a reading that opens a logger gap (2.7 defines only logged-interval openers and last readings) and the time in a band of a lot that is not chained (4.1 covers chained lots only). |
| F4: "one decimal" vs "at most one decimal" (polish) | **Closed** | SOP 1.1 now says "given to at most one decimal place", matching the README. |
| F5: MKT weight of a gap opener only implied (polish) | **Closed / superseded** | 2.7 defines the hold and 5.1 weights by hold. A gap opener's hold is now deliberately left open, and the silence clause governs it (see N1). |

## Part 1: Contract review (fresh)

### What the package gets wrong under the r2 SOP

1. `holds` gives the last reading of an export a hold of 60. 2.7 says it is 0.
2. `unlogged_minutes` treats only spacings over 60 as gaps. Under 2.4 anything over 30 is a gap.
3. `band_of` puts the upper limit out of range (`<`). Under 2.1 the range is inclusive at both ends.
4. `band_of` sends 25.0 to `hot`. Under 2.5, bands above the range have an exclusive lower end. Bands below the range are already correct.
5. `lot_band_minutes` takes the `max` over legs. 4.1 wants the sum for chained lots only.
6. Prior time is not subtracted. 4.2 requires it.
7. The MKT is unweighted. 5.1 weights each reading by its hold.
8. The quarantine test rounds the MKT first (`round(mkt,1) > high`). 1.2 and 6.2 require the unrounded value.
9. `hours` truncates. 1.2 says to round to the nearest hundredth.

`KELVIN_OFFSET` is already 273.15, so it is correct as it stands.

The fixes have two deliberate stopping points:
- **Kept A:** a gap opener's hold stays at what `holds` computes today, `min(span, 60)`.
- **Kept B:** the band time of a lot that is not chained stays the per-band `max` over its legs, with each leg's band time now worked out per the SOP.

### Findings

**N1 (should-fix): the shared constant makes it unclear which gap-opener hold the silence clause keeps.**
Instruction: "the value the package's step works out for it today stands, worked from the figures the SOP does define". The package uses one constant for two jobs. `LOGGER_WINDOW_MINUTES = 60` is both the cap on `holds` and the gap threshold in `unlogged_minutes`. The instruction's symptom ("skipped readings for three quarters of an hour never show up as unlogged time") pushes the solver toward setting that constant to 30. That natural fix silently changes the gap-opener hold from `min(span,60)` to `min(span,30)`.

A second competent engineer could read "worked from the figures the SOP does define" to mean that the package's window should become the SOP's 30-minute logged-interval bound. The alternative reading is that 60 is the package's own figure, so it stays.

A third reading is also invited by 1.4's new "at least one pair ... no more than 30 minutes apart" limit. That limit is only needed if gap openers hold 0, which is the r1 semantics. So the limit reads as a hint toward hold 0.

Counterexample W3 below: `00:00,12.0` / `00:45,5.0` / `01:00,5.0` (range [2,8], warm (8,25]).

| Gap-opener hold | warm | MKT | disposition |
|---|---|---|---|
| 45 (keep `min(span,60)`) | 0.75 | 10.7 | quarantine |
| 30 (constant set to 30) | 0.5 | 10.2 | quarantine |
| 0 (hint in 1.4) | 0.0 | 5.0 | release |

I think the literal reading ("today") is 45, but the text should settle it. For example, add "that value is what the step computes today with its own constants unchanged, even where one of them is also used for a figure the SOP defines". Alternatively, split the constant in the shipped code so the trap is only about reading the contract, not an accident of editing a shared constant. Also drop or explain the redundant 30-minute clause in 1.4.

**N2 (should-fix / trap audit): "chained lot" limits 4.1, but expert instinct says allowances accumulate across the whole lot.**
4.1: "A chained lot's time in a band is the total of that band's time over its legs." 2.9 defines chained as "none of whose handovers is longer than 2,880 minutes". 1.4 and the instruction ("handovers from the same minute to a week later") both put non-chained lots in scope. The only rule for them is the silence clause, which keeps today's `max`.

This is a genuine definitional chain (defined term, then scoped rule, then silence clause), and nothing in the authority lists a competing rule. It passes the 0/8 screen on text. Two things work against it:
- The strong domain instinct is that the stability allowance belongs to the lot. The r1 SOP even said so, in 4.1's removed first sentence.
- The instruction's first symptom ("warm for a few hours on each of three trucks") pushes the solver toward an unconditional sum.

I rate it a fair trap, not a defect. A one-clause cue would remove any doubt without giving the answer away, for example "4.1 ... (this procedure does not carry allowances across a longer handover)".

Counterexample W6 below: handover 2,880 gives warm 6.0; handover 2,881 gives warm 3.0.

**N3 (polish): 2.7 leaves the hold of a gap-opening excursion reading to the package, which also feeds band time.**
3.1 sums the "hold of the leg's excursion readings", so the kept gap-opener hold (N1) enters `band_hours`, `remaining_hours` and, through 6.1, can cause a reject. The contract is consistent about this. A reviewer should just confirm that the reference applies the kept hold in both 3.1 and 5.1.

Counterexample: a warm gap opener with a 90-minute gap gives warm 1.0 (hold 60), not 1.5 or 0.

**N4 (polish): handover minutes are defined but deliberately never counted.**
Handovers feed only the chained test, not unlogged time (4.3 is legs' gaps only) and not any hold. This is consistent, and the definitions in 2.3 and 2.9 make it clear. No action needed.

**N5 (none): exact conventions are complete.**
- Rounding: 1.2. A whole number of minutes never lands halfway (m·5/3). 1.5 keeps the MKT away from the limit and from halves.
- Boundaries: range inclusive (2.1), gap `>30` (2.4), chained `≤2880` (2.9), unlogged `>120` (6.2), reject `<0` (6.1), frozen strictly below (2.8).
- Output: lot order and JSON number format are stated.
- Ranges: every one in 1.4 has both ends, including the new handover 0–10,080.

Nothing found for the "does the authority positively govern a case the instruction calls silent" check. No SOP sentence gives a value to a gap-opener hold or to non-chained band time.

### Hand-worked witnesses

Common record: range [2.0, 8.0], freeze 0.0, H 9880. Bands: cold [-10, 2) with 12 h, warm (8, 25] with 72 h, hot (25, 40] with 2 h. Each lot has a single leg with no prior time unless stated.

| # | Input | Expected |
|---|---|---|
| W1 | `00:00,8.0` `00:30,8.0` `01:00,8.0` | holds 30/30/0; band_hours all 0.0; remaining 12.0/72.0/2.0; unlogged 0.0; mkt 8.0 (not > 8.0) → `release` |
| W2 | `00:00,25.0` `00:20,5.0` `00:40,5.0` | 25.0 goes to warm; warm 0.33, hot 0.0, remaining warm 71.67; MKT 19.655 → 19.7 → `quarantine` |
| W3 | `00:00,12.0` `00:45,5.0` `01:00,5.0` | gap-opener hold kept at 45; warm 0.75, remaining warm 71.25; unlogged 0.75; MKT 10.71 → 10.7 → `quarantine` (**guess on hold; see N1**) |
| W4 | `00:00,12.0` `01:30,5.0` `01:40,5.0` | holds 60/10/0; warm 1.0; unlogged 1.5; MKT 11.29 → 11.3 → `quarantine` (**same guess**) |
| W5 | `00:00` `01:01` `01:11` `02:11` `02:21`, all 5.0 | gaps 61+60, unlogged 121 min = 2.02; mkt 5.0 → `quarantine` |
| W6 | legs A and B, each 19 readings of 10.0 every 10 min (holds total 180); handover 2,880 vs 2,881 | chained: warm 6.0, remaining 66.0. Not chained: warm 3.0 (max), remaining 69.0. mkt 10.0 → `quarantine` both ways. With a warm allowance of 5 h: −1.0 → `reject` vs 2.0 → `quarantine`. |
| W7 | prior hot 120; `00:00,25.1` `00:01,5.0` `00:02,5.0` | hot 0.02, remaining hot −0.02 → `reject` (truncation would print −0.01) |
| W8 | 1 min at 8.1, then 59 min at 8.0, last reading 8.0 | warm 0.02; MKT 8.0017 → prints 8.0 but `quarantine` (unrounded > 8.0 beyond the 0.001 margin) |
| W9 | `00:00,-0.1` `00:10,4.0` `00:20,4.0` | cold 0.17; frozen → `reject`. A reading of exactly 0.0 is not frozen. |
| W10 | `00:00,5.0` `00:10,5.0` `00:20,30.0` (last reading) | last hold 0, so hot 0.0, remaining hot 2.0; mkt 5.0 → `release`. The package today gives hot 1.0 and a different MKT. |

I had to guess on W3 and W4, and only because of N1.

## Part 2: Solver-path screen

**A) Pre-mortem.** A strong solver maps the nine defects to SOP rules quickly. The symptom list points straight at the sum, prior time, the upper limit, the MKT and the 45-minute gap. It then writes a reference and tests.

It most likely goes wrong in two places:
1. It lowers the shared `LOGGER_WINDOW_MINUTES` to 30. That fixes unlogged time but changes gap-opener holds from 31–60 to 30, which shifts band time and the MKT on every lot with a 31+-minute gap. Or it sets gap-opener holds to 0 because 2.7 "doesn't give them a hold" and 1.4's 30-minute clause hints at it. Either way it "adds an exception" the instruction forbids.
2. It sums band time for every lot, missing that 4.1 is scoped to chained lots. The first symptom and domain instinct both push toward summing.

Its own tests are built from its own reading, so neither misreading shows up in self-verification. A solver that reads the silence paragraph closely and diffs `holds` line by line gets both right. Everything else (band ends, last-reading hold, rounding, unrounded comparison) is mechanical.

**B) Scores** (5 = strongly resists solving)

| Axis | Score | Why |
|---|---|---|
| reference_unreachable | 1 | A closed-form reference is small. |
| authority_incomplete_for_grading | 2 | The N1 wording lets two plausible readings apply to the gap-opener hold. Otherwise complete. |
| hidden_state_not_closed_form | 1 | Everything is deterministic. |
| restraint_traps | 3 | Two countable sites. (a) The non-chained `max` is a kept routing decision inside the band-time aggregate that the sum fix forces the solver to rebuild, reached through a defined-term chain. (b) The gap-opener hold is kept inside `holds()`, which must be rebuilt for the last-reading-0 fix and shares a constant with the gap threshold. (b) is partly a contract defect until N1 is tightened. |
| fuzz_blind_spot | 3 | Random jobs with 31–60-minute gaps and handovers over 2,880 minutes hit both traps often, but only against a correct oracle. A solver fuzzing against its own reference reproduces its misreading. |

**C) Verdict**

- self_verification_resistance: 3
- prediction: resists, weakly. I expect at most one of two solvers to fully solve, mostly through N1 and secondarily N2.
- confidence: low-medium
- decisive_reason: the natural fix for the 45-minute unlogged symptom lowers a constant that also caps gap-opener holds the contract says must stay as today; that is a real restraint site, but until N1's wording is tightened part of the resistance comes from contract ambiguity rather than legitimate difficulty.
