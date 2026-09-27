# tbrain-press-shop-scheduling rev2 (platform submission f60dccff, v2 panel return)

Returned snapshot: v2/tbrain-press-shop-scheduling-source.zip = rev1 (sha256 240c74f9...d04a, untouched)
Revised ZIP: revisions/tbrain-press-shop-scheduling-rev2.zip = submissions/tbrain-press-shop-scheduling.zip
sha256 aaa25cb90389a0db5639ea10c8f48e593f900ca0bd9d2521921655e5203d8163

| Finding | Reproduced on v2 | Decision | Change | Closure on rev2 |
|---|---|---|---|---|
| 1 Sound Verifier MINOR: NaN token in an ignored top-level key accepted | four reference schedules + `"diagnostic":NaN` -> 8/8 pass, reward 1 | dropped promise + backed | press-rules.md: "Any other top-level key is ignored" -> "`presses` is the only top-level key"; check_schedule.py (3 byte-identical copies) rejects extra top-level keys and NaN/Infinity/-Infinity via parse_constant; utf-8 open | same files -> 8/8 fail |
| (non-blocking) difficulty_explanation_quality: cites GPT-5.6 run results | - | backed | sentence removed from difficulty_explanation | - |

v1 findings (P1 size cap, P2/P3 duplicate keys): still closed (padded file passes, duplicate P1 rejected).
Unchanged: instruction.md, weeks, targets, reference schedules (costs = targets), planner.

Validation: instruction_preflight OK; scripts/preflight.sh --strict all PASS (both builds, Oracle=1, NOP=0, noexec Oracle=1).
Report: workspace/reports/tbrain-press-shop-scheduling/preflight-rev2.json
