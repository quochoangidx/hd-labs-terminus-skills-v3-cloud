# Scaffold five-axis answers: tbrain-driver-hours-of-service-audit

Snapshot: contract only (instruction.md + environment/); no tests/, model or Oracle yet.

## 1. Coherent contract

Input domain (FM-4 §1): `driver` str 1–32; `end` int 1–20160; `recap` exactly 7 ints 0–1440;
`events` 1–2000, `at` int strictly increasing from 0 and < `end`; `status` in off/sleeper/driving/on;
`miles` number 0–1000. Structural: a reset precedes minute 0 (leading rest continues it); some on-duty time exists.
Nothing may be absent/null. Outside §1 = tier 3 (left open, never graded).

Rule domains and regions (every cell gets a named witness; W = planned test):

| Rule | Regions to witness |
|---|---|
| 2.2–2.3 driving time, yard move | on miles 0 / 0.9 / 1.0 / 1000; driving miles 0; sleeper and off with miles > 0 (T1, own test) |
| 2.4 reset | rest 599 / 600 min; off+sleeper mix; leading rest shorter than 600 (continues the pre-log reset) |
| 2.5 shift start | shift opening with on before driving; shift with no driving; shift opening at minute 0 and mid-day |
| 2.6 break | rest 29 / 30; on-duty 45 (not a break); off+sleeper mix; reset as break |
| 3.1 | shift driving 599 / 600 / 601 / 660+; yard-move minutes past the limit |
| 3.2 | driving minute starting at 839 / 840 after shift start; rest inside shift; shift across midnight |
| 3.3 | 479 / 480 / 481 driving since break; break end vs shift start as the later point |
| 3.4 | cycle exactly 3600 at a minute start; reached mid-stretch; recap oldest day heavy (7th day excluded); recap all 0 and all 1440 |
| 4.1 | stretch across midnight; violation minutes after midnight in a shift begun the day before; last partial day |
| 5.1/5.2 | time left 0, 1–5, 6, 59, 60, full limit; each of driving/window/cycle; log ending in rest, on shift |
| silent (tier 2, from 1.5 + value-level rule, not named) | time left below nought under each limit, at ≤ −3 minutes (T2, own test) |

Promise budget: 8 core obligations, one named silent value, no direct-call helpers, envelope families listed in instruction ¶3, each mapped to a family above.

State table: batch computation, no setters. Observable state of the minute walk (current shift, shift driving, window clock, driving since break, day on-duty, cycle total) is fully determined by the definitions; no "not described" cell except negative time left (tier 2).

Global claims checked against silence: "every rule holds for every log within §1" — consistent: the only silent value is a derived figure, not an input. The value-level silence rule names no value; the silent one follows from FM-4 1.5, and the rule keeps the manual for the minutes it is computed from and only today's conversion step.

Exact conventions and anchors: report keys and day order (§6.1 "The audit prints one JSON object with the keys"); rule keys `"3.1"`–`"3.4"` (§6.1); minutes as integers (§1.4, §6.1); rounding down to a tenth (§5.2); day numbering from 1 (§1.2, §6.1); comparison rule (instruction ¶3).

contract_review: to be run next by the orchestrator's reviewer, blind to tests/solution.

## 2. Correct reference

- Model first (`solution/model.py`), not importing `hoslog`; seals expectations into `tests/expected/` with a SHA manifest; inputs from `solution/` generators with a constant seed.
- Silent case: the model mirrors shipped `round(minutes / 60, 1)` for time left below nought, commented "Shipped step" (never its own reading).
- Numerics: all minutes are ints; rounded-down hours computed as `(m // 6) / 10`, exact. Shipped `round` near −0.0: witnesses use m ≤ −3 so −0.0 vs 0.0 never decides a test.
- Fuzz model vs Oracle on several hundred logs before any test.

## 3. Protected ground truth (harness plan)

Separate verifier; `test.sh` writes reward 0 first, `install -d -m 700 /logs/verifier`, `chmod 700 /tests`, `chmod -R a+rX /app`; candidate runs demoted via `setpriv --reuid --regid --clear-groups --no-new-privs`, own session, `python3 -I -S`, small env, prefix-less `mkdtemp()` with content-digest file names; submitted driver bytes recorded, shipped driver `os.replace`d onto `/app/tools/hoslog_run.py`, documented command run; byte check after candidate code too. Shipped differential (if used) under its own uid, 0700. Candidate-read test on `/tests`, expectations and `/logs/verifier`. Harness-bypass wrong path: a driver shim.

## 4. Sound verifier

One named test per rule and per trap (see manifest witnesses). T1 and T2 inputs only in their own tests; a limits predicate asserts every broad/generated log has miles 0 on every rest stretch and every time left ≥ 0. Wrong paths: each departure reverted plus each natural over-repair (miles ⇒ driving; floor every time left; clamp at nought; window fixed in the walk but not in time left; cycle days fixed but not the limit). Alternatives to run: an event-driven (non-per-minute) implementation of the walk; a Fraction-based formatter.

## 5. Deterministic execution

Sealed literal fixtures, constant seed in `solution/`; no clock, network or set ordering in output; `-p no:randomly`; each job its own process with the phase timeout.
