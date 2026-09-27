# Builder adjudication of contract_review r1: tbrain-sealed-source-decay-inventory

The review is at `contract-review-r1.md`. This adjudication and the repairs apply to snapshot
`2619ac20e6b278c69614eab1681593ae6dadf35f17f52fa818aee91c222c25f5`.

| Finding | Disposition | Evidence | Action |
|---|---|---|---|
| F1: formula form and summation order not fixed | accept | The reviewer's counterexample is plausible. A limit set to a multi-term float sum could flip `over_limit` between addition orders. | Manual 1.1 now says sums are taken in inventory order and that "two figures that agree to one part in 10^9 are the same figure". Phase 2 compares floats at 1e-9 relative and builds every exact boundary at t = 0 or from single, exactly representable terms. It is also listed as exact output `SUM-ORDER-TOLERANCE` in the manifest. The exp(-ln2·t/T) alternative scores 0 mismatches in the fuzz. |
| F2: paragraph-2 wording convoluted | accept | The old sentence said the kept step "comes before anything else in this paragraph". | Paragraph 2 is rewritten. It is now value-level ("Where the manual gives no rule for a figure it defines, the answer the package gives for that figure today is the one the Office wants"), followed by one plain composition sentence. It no longer names any case. |
| F3: a leak test dated after the survey is governed | accept (no conflict) | 5.2 governs it. | This is now out of the input domain: 1.5 and the envelope state "no wipe dated after the survey date". That also keeps the day-count clamp from binding in the leak interval. |
| F4: disposal-eligible entries are still subject to 4.1 and 5.2 | accept, moot | The `in storage` concept (old 1.7) is removed. | No action. |

## Solver-path screen (self_verification_resistance = 1, collapses)

**Disposition: partial.**

- **Accepted.** The departures and the old "in storage" trap were one-hop reads, so the redesign is done.
- **Challenged: "T1's clamp is kept by both the natural and correct day count".** The review's 55k-pair count compared the 30-day count and the Gregorian count, both with the clamp kept. The natural rewrite is `(end - start).days` with no clamp, and it does change the output:
  - `fuzz-model-vs-oracle.json`, family `with_future_certificates`: `t1_overrepair` mismatches 143 of 150 jobs (the old design gave 146 of 150).
  - `departure-check.json`, T1 silent case: the natural rewrite mismatches 95 of 100 jobs, while the shipped package and the Oracle both mismatch 0.
  - The shape is the Bound.hold shape from contract-closure §15: a departure and a silent sub-domain in one function.
- **Where the review is right about T1.** Naming the input in the instruction made T1 easy.
- **Action on T1.** T1 is kept as the third, formula-everywhere trap. It is no longer named in the instruction; the value-level silence clause and 1.3's domain carry it. The two new traps below stand without it, so T1 can be governed or dropped if the orchestrator overrules.

## Redesign: the ONE allowed redesign of the causal core

These trap kinds come from the orchestrator's list and blueprint §4.1/§4.2. Each is in a different file, in a different list, and behind a different phrase.

1. **TRAP_WIPE_NOT_A_LEAK_TEST** (checks.py, `entry.leak_tests`). Definition hop on a bare row.
   - `last_leak_test` becomes a homogeneous list of wipes `{date, removable_bq}`, and the field name is the rule's own term.
   - A new departure D7 takes the last wipe listed, whatever it read. That forces the "last leak test" aggregate to be rebuilt.
   - 5.2 speaks of the latest leak test, and 1.7 (section 1, far from 5.2) defines a leak test as a wipe below 185 Bq.
   - The natural rebuild, `max(date)` over all wipes, is wrong. Getting it right requires adding a reading condition.
2. **TRAP_LICENSING_FOLLOWS_CERTIFICATE** (locations.py). An already-correct kept shipped step inside the aggregate that D9 forces the solver to rebuild.
   - The shipped filter `entry["ref_bq"] <= exempt_quantity` is correct by the new 1.8 (licensing follows the certificate parent figure, whatever the decay or the daughters).
   - It sits beside D9's `+= entry["ref_bq"]` and shares its pattern with D6, where judging on `ref_bq` instead of current activity is the bug.
   - The natural rebuild judges the filter on today's activity, on the total, or on the exempt flag, or it drops the filter.
   - Rebuilding from report rows needs the certificate figure carried back in, so keeping the step correct means adding code.
3. **TRAP_FUTURE_CERTIFICATE** (dates.py). Formula-everywhere edge in a function already being edited, now unnamed (see above).

**What was removed.** The "in storage" definition (old 1.7) and the eligible-entry exclusion from store postings. The removal is recorded in `removed_obligations`.

**Departure count stays at 9.** The old D7 (missing alpha threshold) is dropped: the shipped package now has correct class thresholds. The new D7 is the last-listed wipe.

**Receipts, all on snapshot 2619ac20e6b2…:**
- `fuzz-model-vs-oracle.json`: the Oracle and the exp-form alternative mismatch 0 jobs in every family.
- `departure-check.json`: every departure reverted alone is detected, and the unpatched package matches the model on the kept steps of T1 and TB.
- `zero-of-eight-screen.json`, `solver-path-screen.json` (self-score 3, low confidence), `panel-precheck-design-only*.json` (pass), `canonical-smoke.json` (pass).

## Contract review r2 (svr 2; orchestrator: threshold exception applies, proceed to the skeleton probe, no further redesign)

| Finding | Builder | Orchestrator | Action |
|---|---|---|---|
| F1 (should-fix): 1.7's "incident procedure rather than by this manual" read as making the entry silent | accept | uphold | 1.7 now says a wipe of 185 Bq or more is not a leak test, stays on the record as evidence of a leak, and "section 5 still governs the entry: only its leak tests count there". The definition stays in section 1, and nothing was added to the instruction. |
| F2 (polish): the 1e-9 "same figure" relation was imprecise | accept | uphold | 1.1 now says a reported figure is taken as the manual's figure when it differs "by no more than one part in 10^9 of the manual's figure" (relative to the manual's figure, inclusive). The allowance applies to reported figures only: every comparison against a quantity, threshold, limit or reading is made exactly on the computed figures. This also removes the reviewer's Co-60 at 1e5·(1+5e-10) counterexample. The manifest anchor for SUM-ORDER-TOLERANCE is updated. |
| F3 (polish, optional): "figure" in the silence clause is loose | acknowledge, no change | — | The reviewer's own check shows the output is unambiguous (t = 0, A = A_ref, not eligible). instruction.md is left byte-identical. |
| F4 (none) | noted | — | This is a restraint site, not a defect. |

Receipts were rerun on snapshot 5129563dd553105632a0a2212ec198843ccd4e1ec04eef06ea331169dd1cf6df, and all pass:

- instruction preflight
- design-only precheck under the builder_certified and strict profiles
- fuzz (the Oracle mismatches 0 jobs in every family)
- departure check (identical counts to r1; shipped mismatches 0 on the T1/TB kept steps)
- canonical smoke

The package code, model, Oracle and instruction are unchanged; only the manual (1.1 and 1.7) changed.
