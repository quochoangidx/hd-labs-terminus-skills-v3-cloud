# Resume state: task-batch 3 (session "Task-batch 3 tạo", started 2026-09-25 18:30 +07)

Profile: builder_certified, CORE+ bar (at most 1 of 2 blind GPT-5.6 solvers meets every target).
User: decide every criterion, don't ask; report ZIP + submission per task when 3 CORE+ are delivered.
Solvers: stb harbor (GPT-5.6, terminus-2) via task-local-solve-probe/scripts/stb_probe.sh. Reviewer turns: stb_codex.sh.
Peers (same repo): cobol rev4, gnu-sed, gnu-ed sessions. None owns these slugs; sed session will use stb for 2 trials. Never `stb keys refresh`.

Candidates (resumed from the abandoned batch-task-batch-4 of 09:58, never probed or submitted):
1. tbrain-airport-gate-assignment  Operations/Logistics   (stand allocation, QAP-like transfer walking + bus cost)
2. tbrain-ward-nurse-rostering     Software/Algorithms    (4-week nurse rostering, hard rules + soft penalties)
3. tbrain-newspaper-ad-layout      Media/Design           (ad make-up: skyline packing, sections, spreads, competitors)

Done this session:
- loaders in all 3 checkers (tool == verifier copy): reject a name repeated in one object; nesting > 64 levels (closes roster adversarial findings 1-2; same gap in the other two). Rules docs state it.
- best.py: collects cheapest valid file per instance -> reports/<slug>/authoring/best/.

Target search: rounds r1,r2(,r3) came from the earlier session. Round r3b (all 12, 2400 s, seed 11, from best) started 18:40.
Plan: more rounds + a second neighbourhood family per task until restarts stop improving; targets = best seen.

18:50 stb key hit the Portkey cap (reported by the sed session); it will `stb keys refresh`. I said ok (nothing of mine on the key).
Closure pipeline scripts (batch-task-batch-5/): finalize.py -> preflight.sh --strict --determinism -> gen_wrong.py --run -> gen_matrix.py -> gen_manifest.py --snapshot auto -> panel_precheck --full --profile builder_certified. Dry run on airport passes.
Airport verifier days now split into tests/days/<day>/*.json + roster.json (panel read limit).
18:55 sed session was DENIED stb keys refresh; key still capped. Not refreshing myself (user must run it). stb reviewer/probe steps blocked until the user refreshes.
19:13 r3b done (small gains). r4 = cycle.py iterated annealing, 3600 s, seed 21, on day-2..4, birch/cedar/dale, wed/fri/sat -> authoring/r4/.
20:13 r4 done: roster no gain; airport +0.02%; layout fri 7558 sat 10650. r5 started.
20:14 stb key still capped (Error 04) on a 1-request check.
21:14 r5: fresh 60-min roster anneals beat restarts (birch 1080, dale 1665) -> roster not converged. r6: 7200 s long anneals.
23:14 r6: day-4 15863240, birch 1070, fri 7526, sat 10631; dale 1665 both seeds (converged). key still capped. r7 started (7200 s).
01:15 r7: day-1 7439665 day-2 9156465 day-3 10344095 day-4 15810745; wed 6701 sat 10601; roster held. key capped. r8 (14400 s) started.
05:15 r8: day-2 9153275 day-3 10331305 day-4 15767540 fri 7500. Finalizing targets now; r9 polish in background.

05:21 FINAL TARGETS (finalize.py): airport 7439665/9153275/10331305/15767540; roster 450/1070/830/1665; layout mon 4635 wed 6701 fri 7500 sat 10601.
Closure PASS on all three (close.sh): preflight strict+determinism, wrong paths all rejected on own witness, independence OK, panel_precheck --full builder_certified pass, 0 warnings.
Snapshots: airport 6abdedcc391c..., roster 846bb5303540..., layout d9a418abdc9d...
Valid alternative (shuffled/pretty/extra keys) reward 1 on all three; review_task.py no blockers/should-fix.
Airport verifier days now gzip copies + roster sha256 (new panel_unread_budget rule, 150 KB tests/ text).
Probes + reviewer: stb only (batch-4 user rule: no local Claude for probes). Waiting for the user to refresh the capped key.
r9 polish (nice 10, 4 h) running on airport day-2..4 + layout fri/sat; if it improves, re-run finalize + close.sh.
08:11 user's stb keys refresh failed: account not authorized. Switching to documented local fallback (terminus-probe Opus, local reviewer). r9 killed; snapshots frozen at closure.
08:16 final reviews: airport/roster accept-with-fixes (fixed, recheck running), layout accept. Re-closed: airport 6f3f25e0..., roster 3f947380..., layout 1703feb1.... Layout probe pair (local terminus-probe Opus, docker --cpus 2 no-net, deadline 09:51) started.
08:21 rechecks 2 accept; rewrap; re-closed: airport 7b316a6c, roster 3377d46d, layout 89ad17e3. Layout pair (local terminus-probe) started, deadline 09:56.
08:24 Ownership agreed with session 'Task batch 3 submission' (it stays out). PR #12 pulled (49ad534): builder_certified now adds step 8 pre-submission quality panel (task-quality-panel-judgement creation mode) + panel_gate.py write-report + preflight --panel-report before --emit-zip. User confirmed: local Claude probes instead of stb.
09:49 layout probe 0/2 (4/8, 6/8; run 2 beat mon/wed targets, missed fri +22 sat +6). CORE+ cleared. probe-verdict.json written. Restored score_app.sh into batch dir (lost in peer merge).
09:56 LAYOUT DONE: panel discovery 10/10 None (no clearance needed), panel_gate report pass, ZIP workspace/submissions/tbrain-newspaper-ad-layout.zip sha256 98fe8fd0328ecfc0edd13a6971801063f630a5456373c665286b70e6c1cd2296. Airport pair running (deadline 11:24).
10:03 AIRPORT probe cycle 1: 2/2 (both beat targets by 0.9-2.7% in ~10 min; authoring SA was too cold, T0 2000 vs solver 30000). Strengthening cycle: pool + hot SA.
12:07 ROSTER pair INVALID (both agents stalled >600s, stream watchdog: foreground docker jobs). Archived to local-solve-probes/infra-failed/. Diagnostic grades 7/8 each (only birch missed; ash/cedar/dale beaten) -> targets soft; pooled rosters, strengthening before a counted pair. Airport h1 hot SA: 7241380/9017700/10141540/15578225.
12:07 probe prompt: every command <5 min; long jobs via docker run -d + polling (fix for stream-watchdog stalls).
12:47 h2: airport 7241380/9017700/10131965/15505590; roster 440/1070/820/1650 (no gain past pooled solver rosters). h3 started (3600 s).
13:49 new targets finalized (airport 7241380/9017700/10098740/15505590; roster 440/1070/820/1650), text updated, re-closed: airport fb51f32c, roster 6de6c6c1. Airport cycle-2 pair started.
15:16 AIRPORT cycle 2: 0/2 (4/8 each, 0.09-0.9% over). CORE+ cleared. Next: roster counted pair + airport panel.
15:23 AIRPORT panel discovery: 8 None complete; correct_reference A/B Unsure incomplete (cannot sum costs by hand). Repair: solve.sh cost table + assert within target. Re-closed 4bad1adc. Clearance axes: correct_reference_solution, deterministic_execution.
15:32 AIRPORT: clearance deterministic None x2; correct_reference A None complete, B Unsure incomplete -> panel_gate refuses; documented exception filed; ZIP via strict preflight without --panel-report.
16:01 USER: Science/Operations accept more. Decision: ad-layout -> Operations/Marketing (taxonomy 'Ads'); replace roster with a new Operations/Supply chain optimisation task; roster kept as fallback.
16:06 LAYOUT recategorized Operations/Marketing; clearance coherent+determinism 4/4 None; panel report pass; ZIP rebuilt.
16:10 ROSTER cycle-1 run 1: reward 1 (matched all four targets exactly). Roster is fallback only; replacement lot-sizing in progress.
16:33 NEW SKILL (AGENTS.md 2026-09-26): shipped solution/search.py in all tasks, rewrote difficulty text (no heuristic gap; named role), taxonomy gloss words, solve.sh assertions; independence model_in_tests -> documented exception. Re-closed airport 350a6199, layout 6dde2c81. clearance2 on coherent/correct_ref/determinism for both.
16:41 clearance2 done. LAYOUT receipt pass, ZIP rebuilt. AIRPORT correct_ref still incomplete (A Unsure) -> exception carried; ZIP rebuilt (sha df164038...).
16:42 ROSTER cycle 1: 1/2 (CORE+). Kept as fallback, not packaged.
17:22 STOPPED (user STOP relayed by session f651f6; verified against AGENTS.md §2 'Best-known-target optimisation fails the platform either way', press-shop v3-v5). All four candidates use the long-search target shape: not for submission. Search killed; no probes/panels running. Folders left untouched for archiving by that session.
