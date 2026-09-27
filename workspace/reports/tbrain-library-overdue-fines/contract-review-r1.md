# Contract review r1: tbrain-library-overdue-fines (blind)

Scope: only `contract-packet-r1/instruction.md` and `environment/`.

## Verdict
No BLOCKING divergence found. Taken together, the instruction's "keeps working the figure out the way it does today" and "Add no exception, clamp or guard" settle every silent figure. One SHOULD-FIX: the negative late days and fines on early returns are settled but easy to miss. There are two POLISH items.

## Findings

### F1 SHOULD-FIX: early returns (late days and fine for a loan that is not late)
- LF-5 2.2 defines late days and 3.1 defines the fine only for a *late* loan. 3.1 opens with "Every loan has late days and a fine", which pulls a reader towards 0.
- The instruction settles it. The figure is silent, so the step keeps `returned - due` using the new due day, and the fine stays `late * daily_fine`. Clamping to 0 is a guard the policy does not give. That means negative `late`, negative `fine` and a total that can go negative.
- Counterexample: BOOK borrowed 1405, returned 1411, daily 25. The contract answer is due 1426, late -15, fine -375. A clamping reader gets late 0, fine 0. A reader who replaces the step with "count non-Sunday days in (due, returned]" also gets 0 without meaning to clamp.
- Risk: a solver that honestly rewrites `late_days` as a Sunday-skipping count gets 0 on early loans. You could argue the 2.2 rewrite "owns" the whole step.
- Minimal fix: optionally add one instruction clause, e.g. "a loan returned before its due day still gets its late days and fine the way the package works them out today". Or keep the clause as the intended trap and make sure the rubric/tests cite the instruction sentence.

### F2 POLISH: a late loan whose late span is all Sundays
Due day 5, returned 6 (a Sunday). The loan is late but has 0 late days, so fine 0. 2.2 settles this (only an empty set of non-Sunday days). No divergence.

### F3 POLISH: the cap only applies to late loans
3.1 caps "the fine of a late loan". A reader who applies `min(fine, replacement)` to every loan gets the same output, because early fines are ≤ 0 < replacement ≥ 100. No divergence.

### Checked with no divergence
- Rounding: everything is integer cents with no division. No rounding exists.
- Due day on a Sunday: the policy never moves the due day. Late days start the day after it.
- The due day itself: 2.2 says "after its due day", so it is excluded. The return day is included, and so is a return on a Sunday (which is excluded as a Sunday).
- Order of operations: late days × daily, then cap. That order is unique.
- Input limits: 1.2 is complete for every field the code reads. Duplicate ids and out-of-range values are declared open.
- Output format: the driver is fixed (`json.dump` default separators plus newline), the README lists the keys and the instruction says integers. Nothing is left open.
- Sunday arithmetic: day % 7 == 6 is explicit.

## Silent figures and kept values
| Figure | Kept value / rule |
|---|---|
| JOURNAL loan period | 14 days (the shipped `LOAN_DAYS`), so due = borrowed + 14 |
| Late days for a loan returned on or before its due day | `returned - due` (0 on the due day, negative before it) |
| Fine for such a loan | `late * daily_fine` (0 or negative), no cap |
| Total | plain sum including negatives (3.2 also governs it) |

All of these kept values can be derived uniquely from the shipped code.

## Witness loans (Sunday ⇔ day % 7 == 6)
| # | Case | Input (kind, borrowed, returned, daily, repl) | Due | Late | Fine |
|---|---|---|---|---|---|
| W1 | BOOK late across two Sundays | BOOK 0, 35, 25, 2400 | 21 | days 22–35 = 14, minus Sundays 27, 34, gives **12** | **300** |
| W2 | DVD capped | DVD 1402, 1440, 100, 1800 | 1409 | days 1410–1440 = 31, minus Sundays 1413/1420/1427/1434, gives **27** | 2700 capped to **1800** |
| W3 | JOURNAL | JOURNAL 100, 130, 50, 5000 | 114 | days 115–130 = 16, minus Sundays 118, 125, gives **14** | **700** |
| W4 | Returned before due | BOOK 1405, 1411, 25, 3100 | 1426 | **-15** | **-375** (shipped code today: due 1419, late -8, fine -200) |
| W5 | Returned on due day | DVD 7, 14, 100, 1800 | 14 | **0** | **0** |
| W6 | Due day is a Sunday | DVD 1399, 1408, 100, 1800 | 1406 (Sunday) | days 1407, 1408, gives **2** | **200** |

Shipped example `eastgate-0314.json` under the contract: B0041172 due 1421, late 6, fine 150; D0007719 due 1409, late 3, fine 300; B0055010 due 1426, late -15, fine -375; total 75.
