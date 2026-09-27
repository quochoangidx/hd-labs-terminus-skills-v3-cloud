# Contract review r3 — tbrain-parcel-dim-weight-billing (blind)

Compared contract-packet-r3 with r2. The only change is rule 3.3. It now governs the fuel surcharge of a GROUND parcel only. For an EXPRESS parcel, 3.3 says a fuel surcharge exists but gives no rule for it.

## Findings

### G1 BLOCKING: express fuel is silent, but the instruction describes a fuel defect in general terms
Under the instruction, the silent figure keeps today's computation, applied to the corrected transport charge T: fuel = floor(T * 1425 / 10000). That is on T only, with the residential surcharge left out and the fraction dropped.

But instruction.md still says, with no restriction to ground: "the fuel line leaves out part of what it should be taken on and drops fractions of a cent the rules round." A careful reader can take that as the diagnosis for every parcel and apply the ground formula to express too.

Two readings:
- Reader A (silence, so keep today's step): express fuel = floor(0.1425 * T).
- Reader B (instruction's diagnosis, rule applied throughout): half_up(0.1425 * (T + R)).

Counterexamples:
- [14,10,1], 23, EXPRESS, z3, non-res: T=315, R=0. A: F=floor(44.8875)=44, total 359. B: F=45, total 360.
- [10,10,10], 50, EXPRESS, z2, res: T=760, R=450. A: F=floor(108.3)=108, total 1318. B: F=half_up(172.425)=172, total 1382.

Reader A is the literally correct one: the instruction says every step without a rule keeps working its figure out as it does today. Even so, the instruction's own description of the defect pulls in the other direction.

Minimal fix: scope the instruction sentence, e.g. "…and on ground parcels the fuel line leaves out part of what it should be taken on and drops fractions of a cent the rules round." Alternatively, if express fuel was not meant to be silent, revert 3.3 to r2.

### G2 SHOULD-FIX: the two fuel formulas must be split by service
The package's `fuel(moving, home)` receives no service, so it cannot tell ground from express. This is not a contract ambiguity: the kept express step is uniquely derivable. It is a trap worth knowing about. An agent must branch on service in invoice.py or charges.py and keep the express path exactly as floor(T*1425//10000), with R excluded, including for express home parcels.

Suggestion (optional): keep a witness express residential parcel in the tests so that both "kept" properties are pinned: R excluded and floor.

### Earlier findings
F1–F3 stay closed. The wording of 2.2 and 3.2 is unchanged from r2. F4 (polish) is unchanged.

## Silent figures and kept values
| Figure | Kept value |
|---|---|
| Non-box dimensional divisor | 166 |
| Residential surcharge, EXPRESS to a home | 450 |
| Fuel surcharge, EXPRESS (any residential) | floor(T * 1425 / 10000): 14.25% of the corrected transport only, residential excluded, truncated |

## Witnesses (reader A, the literal contract)
| Input | billable | T | R | F | total |
|---|---|---|---|---|---|
| [18,12,10], 84, GROUND, z5, res (box, ground home) | 16 | 2096 | 530 | 374 | 3000 |
| [14,10,1], 23, EXPRESS, z3, non-res (non-box) | 3 | 315 | 0 | 44 | 359 |
| [10,10,10], 50, EXPRESS, z2, res (express home) | 8 | 760 | 450 | 108 | 1318 |
| [2,2,2], 260, GROUND, z2, res (fuel 427.5 → 428) | 26 | 2470 | 530 | 428 | 3428 |
| [1,1,1], 72, GROUND, z4, non-res (7.2 → 8) | 8 | 944 | 0 | 135 | 1079 |
| [1,2,83], 5, GROUND, z8, non-res (non-box dimensional weight 1) | 1 | 190 | 0 | 27 | 217 |

A half-up witness needs a GROUND parcel. The r3 condition is (T + R) ≡ 200 (mod 400).
