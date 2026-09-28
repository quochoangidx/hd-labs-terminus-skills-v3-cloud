# Final review: tbrain-hotel-folio-charges (final-packet)

Scope: this review read only final-packet/. I ran all Python on a scratch copy with PYTHONDONTWRITEBYTECODE=1, and the packet still holds no `__pycache__`/`.pyc` files. Docker/Harbor runs were not possible here. I reproduced the verifier's `compare()` logic in-process instead: the function was extracted verbatim from tests/test_outputs.py and run over the sealed families.

## Verdict
There are no BLOCKING or SHOULD-FIX findings. There are 3 POLISH items, and 3 claims I could not verify without Docker.

## Checks
1. **The patch applies and matches the model.**
   - `patch -p1 --no-backup-if-mismatch < fix.patch` applies cleanly to a copy of environment/app laid out as /app. It touches only charges.py; money.to_cents and the driver are untouched.
   - The patched package's `statement` equals `model.statement` on all 8 sealed families.
   - It also agrees on 20,000 random single-stay files across the full rule-1.2 range (half the rates are multiples of 100, to hit half cents).
2. **The sealed expectations reproduce.**
   - Re-running solution/seal.py in the scratch copy gives byte-identical tests/expected/*.jsonl and ROSTER.
   - Every sha256sum equals its ROSTER digest, and the row counts match (1, 1, 1, 2, 1, 1, 4, 1).
   - tests/shipped equals environment/app/{src,tools} byte for byte.
3. **The kept figures are graded and isolated.**
   - The fee rounded half-up fails only `service_fee`.
   - The cheap-room city-tax mutants fail only `city_tax_cheap`: the new tax applied from 3,000, the new tax on every room, a 14-night stop on cheap rooms, and the 3,000-cent exemption dropped.
   - The half-fee stays in the service_fee family include 4 with an even lower cent and 3 with an odd one.
   - No family other than city_tax_cheap contains a rate under 5,000.
   - Everywhere else a half-fee stay's fee and totals are skipped, as documented.
   - The shipped package fails all 8 families; the patched one fails none.
   - The other mutants I ran each fail at least their own rule's test: all nights charged, every 8th night free, a 13-night stop, the old city tax, occupancy half-even, 12%, the fee on the old base, a fee floor, a 5,001 threshold, and free nights excluded from the city tax.
4. **The instruction's coverage promises are met.**
   - 1-stay files (ONLY) and a 200-stay file (limits).
   - Stays of 1, 6, 7, 8, 13, 14, 15 and 60 nights.
   - Rates of 1,000, 2,999, 3,000, 4,999, 5,000 and 150,000.
   - Half cents on the occupancy tax and the service fee, with both even and odd lower cents.
   - Ids of 1 and 10 characters, and folio order checked, including a shuffled relabel.
5. **task.toml claims.**
   - Verified:
     - there are 10 tests over 8 sealed files;
     - there is a named test per rule 2.1/2.2/2.3/2.5, plus 2 kept-figure tests, limits, the generated family and 2 harness tests;
     - the named nights and rates, and all 1.2 limits, are reached;
     - the os.urandom relabel exists;
     - model.py never imports the package;
     - the read-isolation test covers /tests, ROSTER, the shipped copy and /logs/verifier;
     - the Oracle scores 1 and the shipped package 0, in emulation;
     - every mutant named in the claim fails its own test.
   - Not verifiable here: the Docker-level Oracle/nop scores, "a contract-valid alternative scores 1", and that pytest==9.1.1 and pytest-json-ctrf==0.5.2 install and provide `--ctrf`. Confirm these from the Harbor run logs.
6. **Hygiene.**
   - No caches, resource forks or .DS_Store files.
   - .dockerignore excludes solution/ and tests/.
   - Both images use the same digest-pinned base.
   - The instruction and environment are identical to contract-packet-r3.
   - Nothing task-visible leaks the solution or the tests.

## POLISH
- P1: the comment on `GRADES` in tests/test_outputs.py says "Families that grade the service fee of a stay whose fee lands on a half cent", but the dict also holds `city_tax_cheap: {"cheap"}`. Suggested wording: "Figures left to today's code that each family grades", which is what jobgen.py says.
- P2: difficulty_explanation says "A hand-built reference fuzzed against the package will not flag the difference." It is unclear which reference and which difference are meant. Reword it, or drop the sentence.
- P3: the docstring of test_rule_1_2_limits_reached lists only the 5,000 and 150,000 rates. That is accurate for that file, since the 1,000 end is in city_tax_cheap, but a reader could take it as the whole limits claim. Optional note.

## Hand witnesses (the model agrees)
| Stay | Folio |
|---|---|
| 1n@22000 | 25990 |
| 7n@14500 | 103540 |
| 15n@18900 | occ 33170, fee 8600, total 290970 |
| 1n@1100 | occ 149, city 0, fee 38, total 1287 |
| 1n@1300 | occ 176, fee 46, total 1522 |
| 15n@4000 | city 3000, total 63840 |

## Silent figures and kept values (as implemented)
- city tax, rate < 3000: 0
- city tax, 3000 ≤ rate < 5000: 200 × nights, uncapped
- service fee: 3.5% of the rule-2.1 room charge, rounded half to even (money.to_cents)
