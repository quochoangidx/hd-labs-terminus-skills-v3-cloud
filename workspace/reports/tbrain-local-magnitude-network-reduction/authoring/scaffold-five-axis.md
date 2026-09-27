# Scaffold five-axis checklist: tbrain-local-magnitude-network-reduction

Builder-only authoring artifact (never shipped, never shown to reviewer or solvers).
Answers `terminus-regular-task-authoring/references/scaffold-five-axis-checklist.md`
for the contract as written at step 3 (instruction.md + environment/, before any
verifier, model or Oracle).

Departure ids below follow `mined-candidate.json` (D1–D8); traps T1 (READINGS) and
T2 (OFF_TABLE_KEPT).

## 1. Coherent contract

### Declared input domain (NPM-4 §1)

| Field | Type | Range / structure | Absent / null / zero / negative |
|---|---|---|---|
| `stations[]` | list | 1–200 | never empty |
| `stations[].code` | str | 1–5 of `[A-Z0-9]`, distinct | — |
| `stations[].correction` | number | −1.0 … +1.0 | zero and negative allowed |
| `events[]` | list | 1–50, file order | never empty |
| `events[].id` | str | 1–20 chars, distinct | — |
| `events[].depth_km` | number | 0 … 60 | zero allowed |
| `events[].recordings[]` | list | 1–40, station at most once per event, station in table | never empty |
| `recordings[].epi_km` | number | 0 … 1000 | zero allowed |
| derived hypocentral distance | number | ≥ 1 (1.2 last sentence) … ≈1001.8 | — |
| `recordings[].amplitudes[]` | list | 1–4, distinct 3-char `channel` | never empty; ≥1 reading (1.3) |
| `amplitudes[].amplitude_nm` | number | 0.1 … 10^8 | positive only |
| `amplitudes[].noise_nm` | number | 0.01 … 10^7 | positive only |

Tier 3 (left open, never graded): any figure past these limits, any structural
breach of §1 (missing station, duplicate station/channel/id, recording with no
reading, wrong layout).

### Formula domains

| Rule | Domain as written | Notes |
|---|---|---|
| 2.2 record amplitude | every amplitude | universal; ceilings keep log10 finite |
| 2.3 reading | every amplitude, threshold "at least three times" (inclusive) | boundary fixtures exact in integers so ratio and product forms agree |
| 3.1 hypocentral | every recording | universal |
| 3.2/3.3 correction | listed distances and "between two listed distances", i.e. [10, 600] | outside [10, 600]: no rule → silence clause (T2) |
| 4.1 channel magnitude | each reading | depends on 3.x value; off-table value is the kept shipped calculation |
| 4.2 correction sign | every station | universal |
| 4.3 station mean | a station's readings (≥1 by 1.3) | universal |
| 5.1 contributes | every station, [10, 600] inclusive | universal |
| 5.2 median | contributors (≥3 when defined) | odd / even |
| 5.3 fewer than three | 0, 1, 2 contributors → null | 0 contributors only reachable with all stations off-table (T2 test only) |

### Rule × region table (witness per cell; test names planned)

| Rule | Low end | High end | Other regions | Witness |
|---|---|---|---|---|
| 2.2 gain | amp 0.1 (noise 0.01) | amp 10^8 (noise 10^7) | mid values | `test_rule_2_2_record_amplitude_uses_magnification_2080`, `test_section_one_limits_reached` |
| 2.2 half | same | same | single-reading station | `test_rule_2_2_record_amplitude_is_half_peak_to_peak` |
| 2.3 reading | amp < 3·noise (reading larger and smaller than the sub-noise one) | amp = 3·noise exactly (300/100) | amp just above | `test_station_mean_leaves_out_amplitudes_under_three_times_noise` (T1 only) |
| 3.1 hypocentral | epi 0 (depth ≥ 10 in-table), depth 0 | depth 60 | epi 6 / depth 12 (moves contributor) | `test_rule_3_1_distance_is_hypocentral` |
| 3.3 linear | R = 10 exactly (epi 10 depth 0; epi 8 depth 6) | R = 600 exactly (epi 600 depth 0) | a point inside several segments | `test_rule_3_3_correction_linear_between_listed_distances`, `test_rule_3_3_listed_distances_and_table_ends` |
| T2 off-table | R = 1 (epi 0, depth 1); R ∈ (1, 10) | R ∈ (600, 1001.8], epi 1000 depth 60 | an event whose stations are all off-table (null ml) | `test_station_beyond_the_table_keeps_the_shipped_correction` (T2 only) |
| 4.2 sign | correction −1.0 | +1.0 | 0.0, +0.37 | `test_rule_4_2_station_correction_is_added` |
| 4.3 mean | 1 reading | 4 readings | 2, 3 | `test_rule_4_3_station_magnitude_is_mean_of_channel_magnitudes` |
| 5.1 contributes | R = 10 → true | R = 600 → true | R just inside | table-end test; outside only in the T2 test |
| 5.2 median | 3 contributors | 40 contributors | even counts 4, 6 | `test_rule_5_2_network_magnitude_is_median_of_contributors`, `test_rule_5_2_even_number_takes_mean_of_middle_two` |
| 5.3 minimum | 1, 2 → null | 3 → number | 0 (T2 test) | `test_rule_5_3_fewer_than_three_contributors_has_no_network_magnitude`, `test_rule_5_3_three_contributors_give_a_network_magnitude` |
| magnitude sign (C8) | negative station ML (amp 0.1 at 10 km ≈ −2.3) | ML ≈ 9 (amp 10^8 at 600 km) | zero-crossing network ML | limits test + generated |
| counts (C5) | 1 event / 1 station table entry | 50 events, 200 stations, 40 recordings, 4 amplitudes | — | `test_section_one_limits_reached` |

Every cell can be filled with a trap-free fixture except the T1 and T2 rows, whose
inputs live only in their own named tests.

### State table

Stateless: `reduce_bulletin` is a pure function of one parsed file; no setters,
no carried state between events (station table is read-only). The only
cross-event sharing is the station table's corrections; witness: two events
sharing a station with different distances. No *not described* cells.

### Global claims checked against the silence clause

- 3.3 "At a listed distance the correction is the listed value": true for 10 and
  600 under both the shipped log formula and the fix; no conflict with T2.
- 5.2 "so that one misbehaving station cannot move the event far": explanatory,
  not a graded invariant. Not promised as a property; no witness needed beyond the
  median rule.
- 6.2 "no other keys": graded by exact key-set equality at every level.
- 0.3 "Nothing is rounded": graded implicitly (tolerance 10^-6; a rounded
  candidate fails every test).
- Instruction "fed with the quantities NPM-4 does define" (T2): the kept
  calculation takes the hypocentral distance; checked that no departure touches
  the end-segment nodes (10, 20, 500, 600 values identical in package and manual).

### Exact conventions (→ `exact_output_requirements`)

| Convention | Anchor |
|---|---|
| report keys at each level, no others | NPM-4 6.1, 6.2 |
| events in file order, stations in recording order | NPM-4 6.1 |
| `ml` null when no network magnitude | NPM-4 6.1, 5.3 |
| `contributes` boolean | NPM-4 6.1 |
| numeric tolerance 10^-6, exact for id/code/contributes/order/null | instruction ¶3 |
| inclusive threshold "at least three times" | NPM-4 2.3 |
| inclusive table ends | NPM-4 5.1 "both ends included" |

### Representation

Only decoded JSON values matter: object key order, whitespace and float
formatting are free. Decision for the verifier: `distance_km` and numeric `ml`
compare as numbers (int or float, never bool) within 10^-6; `contributes` must be
a `bool`; `ml` must be a number or `None`; `id` and `code` are exact strings.

### contract_review

Pending: the orchestrator spawns the single reviewer on instruction.md +
environment/ (step 3). Repairs land before any verifier.

## 2. Correct reference

- Order: `solution/model.py` from NPM-4 (no import of `mlnet`), then Oracle
  `fix.patch`, then a model-vs-Oracle fuzz (a few hundred generated bulletins,
  including off-table and sub-noise inputs), then the skeleton probe.
- Silent case T2: the model mirrors the shipped `_segment` + log-distance
  formula with a "Shipped step" comment, fed with the hypocentral distance; it
  never answers with its own reading (no clamp, no linear extrapolation).
- Numerics probe: exact half p2p via `/ 2`; `log10(a/2*2080e-6)` vs
  `log10(a) + log10(1.04e-3)` differ < 1e-15; hypot vs sqrt(x*x+y*y) differ by
  an ulp, so every fixture keeps R at least 10^-3 away from 10 and 600 unless it
  is exact in both forms (epi 10/600 at depth 0; epi 8, depth 6); 2.3 boundary
  only at exact integers; median of floats, (a+b)/2 vs a/2+b/2 within 1e-15.
  Extremes: amp 10^8 at R 1001.8 gives ML ≈ 10.9 (finite); amp 0.1 at R 1 gives
  ML ≈ −3.5.
- `solve.sh` header: Rule | File | Change table with a "(no change)" row for
  bulletin.py/driver and for the off-table branch ("kept as shipped").

## 3. Protected ground truth (harness shape fixed now)

- Separate verifier image; expectations sealed from `solution/model.py` into
  `tests/expected/` as plain JSON lines with a SHA-256 manifest; inputs sealed too
  (generator in `solution/jobgen.py`, constant seed).
- `test.sh`: reward 0 first, `install -d -m 700 /logs/verifier`, `chmod 700
  /tests`, `chmod -R a+rX /app`; candidate runs as a sandbox uid via
  `setpriv --reuid --regid --clear-groups --no-new-privs`, new session, small env,
  `python3 -I -S`, killpg on timeout.
- Driver: record submitted `/app/tools/ml_bulletin.py` bytes, compare with
  `tests/shipped/tools/ml_bulletin.py` before and after candidate code,
  `os.replace` the shipped copy onto the documented path in the verifier's staged
  `/app`, run exactly `python3 /app/tools/ml_bulletin.py BULLETIN.json` style
  command (staged path), prefix-less `mkdtemp()`, content-digest file names.
- No shipped differential copy is needed: T2's expectation comes from the model's
  mirrored shipped step (a differential cannot neutralise D1/D2/D5 cheaply). If
  one is added later, it runs under its own uid, mode 0700.
- Visible sample never graded.
- Harness-bypass wrong paths planned: a driver-side shim that prints expected
  output; a package that tries to read `/tests/expected`.

## 4. Sound verifier (plan)

- One named test per rule and per trap (list in the rule × region table), no
  parametrize; a limits predicate (`_keeps_the_limits`) over every graded
  bulletin that also asserts which trap inputs (sub-noise amplitude; hypocentral
  distance outside [10, 600]) each carries: only the two trap tests may carry them.
- Wrong paths: each departure hunk reverted alone; T1 mean-over-all; T2 linear
  extrapolation; T2 clamp; median lower-middle; `>` instead of `>=` at 2.3;
  exclusive table ends at 5.1; epicentral window.
- Revealing state: T1 fixture has the sub-noise amplitude both larger and
  smaller than the reading (max-based and mean-based wrongs both differ); T2 event
  keeps ≥3 in-table contributors so the network value is fixed and only the
  off-table station's `ml` moves; D5 fixture has a station that crosses 10 km
  only by depth.
- Alternatives to run: ratio form `amp / noise >= 3`; `math.hypot`;
  `statistics.median`; `numpy`-free sorted-list median; a per-segment
  `bisect`-based interpolation that keeps the shipped formula outside.
- Sweep C1–C18 at step 5b.

## 5. Deterministic execution

- Sealed literal fixtures; generator seed constant in `solution/`; no clock,
  network or RNG at grading.
- Same interpreter and libm: model runs in the verifier image only at sealing
  time on the authoring machine; expectations compared with 10^-6 tolerance, far
  above libm differences.
- `-p no:randomly`, one process per driver run, per-run timeout.
- `preflight.sh --determinism` once the first named tests pass on the Oracle.

## Revision after contract_review (CR-1..CR-6)

- T1 is now departure D9 (rule 2.3), still in its own test. New trap T3 STATION_GROUPING:
  recordings are one sensor's share; a station may send two recordings (same `epi_km`,
  distinct channels, one or two amplitudes each). Rule × region rows added: one station
  with 1+2 readings over two recordings (pooled mean != mean of means); two stations and
  three recordings -> null; three stations and four recordings -> median of three; two
  shared stations in one event. Witness `test_two_sensors_of_one_site_are_one_station`
  (only test with a repeated station; `jobgen.trap_inputs()` enforces it).
- Amplitudes per recording now 1–2; per station 1–4 across its recordings.
- NPM-4 3.2 now states "this part gives no correction for a distance outside it" (CR-2).
- Verifier numeric rules (CR-1, CR-5): 3x ties only binary-exact; table ends only at
  depth 0 or exact Pythagorean pairs; else keep >= 1e-3 from 10/600.
