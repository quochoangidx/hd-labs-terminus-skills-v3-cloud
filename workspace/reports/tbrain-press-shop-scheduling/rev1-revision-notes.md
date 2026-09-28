# tbrain-press-shop-scheduling rev1 (platform submission f60dccff, v1 panel return)

Returned snapshot: v1/tbrain-press-shop-scheduling-source.zip (sha256 b767a5e2...bb73, untouched)
Revised ZIP: revisions/tbrain-press-shop-scheduling-rev1.zip = submissions/tbrain-press-shop-scheduling.zip
sha256 240c74f9d2fa51aa2b9e444565b1785bcfa43642975ce08df3599aaf5c46d04a

| Finding | Reproduced on v1 | Decision | Change | Closure on rev1 |
|---|---|---|---|---|
| 1 Coherent Contract MAJOR: undisclosed 2,000,000-byte cap | reference schedules + week-36 padded to 2,000,001 bytes -> week-36 tests 2 failed | backed (remove cap) | tests/test_outputs.py: MAX_BYTES/getsize removed | padded case 8/8 pass |
| 2 Sound Verifier MINOR: duplicate press key erased by json.load | `"P1": [], "P1": [...]` in week-36 -> 8/8 pass | backed | check_schedule.py (tests/ + environment/app/tools/, byte-identical): load_schedule() with object_pairs_hook rejects repeated press keys / repeated presses object; verifier and checker use it | verifier: week-36 2 failed; visible checker prints INFEASIBLE |
| 3 Sound Verifier MINOR: same as 2 | same | backed | same | same |
| (non-blocking) solution_quality: generator not shipped | - | backed | solution/search/{lns.py,ils.py,check_schedule.py} added; solve.sh + solution_explanation cite them | not run by solve.sh |

Other edits: press-rules.md file-format sentence now says the presses object is given once; verification_explanation mentions the duplicate-key check.
Unchanged: instruction.md, weeks, targets, reference schedules (costs 33983/47936/77699/112876 = targets).

Validation: instruction_preflight OK; scripts/preflight.sh --strict all PASS (agent+verifier build, Oracle=1, NOP=0, noexec Oracle=1).
Report: workspace/reports/tbrain-press-shop-scheduling/preflight-rev1.json
