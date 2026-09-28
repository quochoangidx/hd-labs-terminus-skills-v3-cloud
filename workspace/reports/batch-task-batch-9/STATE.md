# Resume state: task-batch 9 (session 2026-09-27)

Profile: builder_certified (default), CORE+ bar (at most 1 of 2 blind claude-opus-5 terminus-probe solvers succeeds).
User: `task-batch 3`; decide every criterion, don't ask; no commits; report ZIP + SUBMISSION immediately as each task reaches CORE+/builder_certified.
One active candidate at a time. Probes: local terminus-probe (memory: no stb). Reviewer/panel: fresh subagents, blind packets.
Orchestrator rules carried from batch-8: contract_review clean before skeleton pair (never parallel); one strengthening after 2/2, second 2/2 replaces; close post-probe ambiguity by narrowing data limits; unanimous miss with <=1 flag and isolated is accepted per step 7.

Delivered: 0/3

Candidates:
A. tbrain-cems-hourly-emission-averaging  Operations/Compliance (boiler stack CEMS hourly averages, valid-hour rules, substitute data, rolling-average compliance report)
- 21:20 A builder phase1 launched.
- 21:37 A phase1 done (9 departures, T1 partial-data hour carry, T2 non-firing hour correction; svr 3; image 3734bb10). contract r1 launched.
- 21:39 A contract r1: 0 blocking; F1 should-fix (T2 non-firing constants 3 readings) UPHOLD, F2 should-fix (CAL hour) UPHOLD, F3 = fair T1 trap; svr 3. Repair sent to builder.
- 21:42 A r1 repair done (snapshot f00f68b6; image 398d9c21). contract r2 launched.
- 21:43 A contract r2 clean (all polish; svr 3, marginal collapse). Skeleton cycle-1 launched.
- 21:49 A skeleton cycle-1 = 2/2 (claude-opus-5; 12/12 families both; both named T1/T2 explicitly). One strengthening sent.
- 21:54 A strengthened (snapshot f641ce6b; image c81a9a85 :skeleton2; T1 carry previous operating hour after lost-average, T2 shared O2_CAP/AMBIENT constants). contract r3 launched.
- 21:55 A contract r3 clean (polish only; svr 3-4 resists). Skeleton cycle-2 launched.
- 22:09 A skeleton cycle-2 = 2/2 (claude-opus-5; both solved all families). A REJECTED (second 2/2); task folder moved to workspace/dropped/. Both pairs kept old functions untouched and added new branches beside them (additive repair disarms keep-today traps).
B. tbrain-microbial-plate-count-reporting  Science/Biology (food-lab aerobic plate count: countable-range plates, dilution-weighted counts, estimated/TNTC results, report rounding)
- 22:30 B phase1 done (snapshot 6059142a; 8 departures; T1 skipped-step tenth dilution, T2 mixed no-countable sample keeps pooled estimate; svr 3; image 535b8fa5). contract r1 launched.
- 22:31 B contract r1: F1 should-fix/borderline blocking (T2 mixed sample multiple readings) UPHOLD; T1 read as plain rule; svr 2. Redesign 1/1 sent.
- 22:36 B redesign done (snapshot 726cdf98; image 4a1bbfdc :skeleton2; T1 tenth-dilution exclusion, T2 counted plates include sparse/empty in pooled sum; mixed samples governed by 4.4). contract r2 launched.
- 22:37 B contract r2: all r1 closed, polish only, but svr 1 (fully governed closed-form; traps are direct SOP sentences). B REJECTED at step 3 (svr 1 stops before verifier); moved to workspace/dropped/.
C. tbrain-water-utility-tiered-billing  Operations/Claims (municipal water/sewer bill: tiered blocks, cycle-length proration, winter-average sewer cap, estimated reads and true-up)
- 22:55 C phase1 done as water billing (7 departures, T1 short span keeps widths, T2 multi-unit meter no cap; svr 3). Orchestrator novelty ruling: too close to accepted utility-rebill-true-up -> re-domain to tbrain-driver-duty-log-compliance (Operations/Compliance), same trap architecture.
- 22:55 Builder flagged duty-log collision with existing tbrain-driver-hours-of-service-audit; re-domain changed to tbrain-fleet-tire-tread-compliance (Operations/Compliance).
- 23:03 C phase1 done as tire-tread (snapshot 87ce668e; 8 departures; T1 wear-bar reading keeps shown figure, T2 part-worn tire keeps first-reading basis; svr 3; image 8c13e35b). contract r1 launched.
- 23:05 C contract r1: F1 should-fix (wear-bar 3 readings) UPHOLD; F2 fair trap; svr 2 (advisory). Repair sent.
- 23:07 C F1 repair done (snapshot 10b11ab8; image 1bc813e2 :skeleton2). contract r2 launched.
- 23:08 C contract r2 clean (svr 2 advisory). Skeleton cycle-1 launched.
- 23:11 C skeleton cycle-1 = 2/2 (claude-opus-5, 11/11 both; both explicitly scoped 'measurement'/'fresh' and kept old code). One strengthening sent.
- 23:21 C strengthened (snapshot 95b58224; image c60d81b1 :skeleton3; T1 km_left shares divide (half-even kept), T2 regroove floor shares REMOVAL constant). contract r3 launched.
- 23:22 C contract r3: F1 blocking (km_left half rounding 2 readings), F2 blocking/should-fix (regroove 50 vs 52); restraint 1 once fixed; reviewer predicts collapse after repair. Strengthening spent -> C REJECTED (no fair trap survives); moved to workspace/dropped/.
D. tbrain-bod5-dilution-data-reduction  Science/Earth (BOD5 bench data reduction; icpms-style defined-term 'result' traps)
- 23:23 D builder phase1 launched.
- 23:39 D phase1 done (8 departures; T1 empty usable seed set keeps pooled factor, T2 RPD on bound pair keeps parent divisor; svr 3; image 03182559). contract r1 launched.
- 23:41 D contract r1: F1 blocking (T1 two readings, competing seed rate), F2 blocking (G rounded vs unrounded), F3/F4 should-fix (RPD inputs); svr 2. Redesign 1/1 sent.
- 23:47 D redesign done (snapshot d9d30ac0; image 299d36d9 :skeleton2; T1 governed reference-controls inclusion, T2 silent RPD on bound pair). contract r2 launched.
- 23:48 D contract r2: r1 closed; N1 should-fix/near-blocking (T2 RPD on bound pair: 6.1 competing formula, 2 readings flip pass); T1 plain governed rule. No fair trap survives (governing N1 removes T2, naming it signposts it). D REJECTED; moved to workspace/dropped/.
Orchestrator: four seeded-departure SOP candidates in a row failed (2/2 or no fair trap). Switching shape for E: evidence-reconstruction (agent writes a reusable analyzer; verifier runs it on hidden generated evidence sets of the same inferable model).
E. tbrain-linux-host-intrusion-triage  Security/Forensics
- 00:07 E phase1 done (12 decoy rules, 12 wrong analyzers each fail own family; reference 385/385 vs model; svr 2 self; image 853e1b67). contract r1 launched.
- 00:09 E contract r1: 0 blocking, F1-F5 should-fix (join, key text, 2s bound, path scope, step compare) UPHOLD; svr 3 resists weakly. Repair sent.
- 00:11 E r1 repair done (snapshot 506a3098; image 534f9056 :skeleton2). contract r2 launched.
- 00:13 E N1-N4 fixed (snapshot 48ad8cbc; image 6c2c74d9). Skeleton cycle-1 launched.
- 00:29 E skeleton cycle-1 = 2/2 (claude-opus-5; 11/11 families both, ~4 and ~15 min). One strengthening sent (move stated conventions into evidence inference).
- 00:33 E strengthened (snapshot 698ae771; image 8219787c :skeleton3; clock step inferred from UTC collector copy; guide 7 definitions; decoys unstated). contract r3 launched.
- 00:36 E contract r3: F1 blocking (shared-password tie), F2-F4 should-fix (step window, open session end, package files); svr 4 'for wrong reason'; reviewer keeps inference design, 4 sentences. Repair sent.
- 00:39 E r3 repair done (snapshot dd31317a; image 23beafef :skeleton3). contract r4 launched.
- 00:41 E r4 N1 fixed (snapshot f4b10580; image dd038a83). Skeleton cycle-2 launched.
- 01:00 E skeleton cycle-2 raw 1/2 (claude-opus-5): run_1 fails clock c006 last_activity only; run_2 solved. Cause analysis sent to builder.
- 01:01 E cycle-2 cause: legitimate miss (run_1 corrects host readings by session's clock side; contradicts rule 1 at-most-one-step; 184/200 on extra seeds, run_2 200/200). CORE+ signal 1/2 -> phase 2 sent.
- 01:12 E phase 2 done (snapshot 8c9a9309; 15 tests; preflight strict+determinism PASS, independence PASS, 13/13 wrong paths, sweep 14/14, bounds 5/5, precheck full pass). final_review launched; builder preparing step-7 receipt + panel packets.
- 01:15 E final_review: ready, nothing blocking; F1 should-fix (root-login escalation branch unwitnessed, mutant passes), F2-F7 polish. Held for consolidated batch with panel.
- 01:23 E panel discovery: CRS-A Minor, CRS-B Minor, SV-A Unsure, SV-B Minor. Root R1 clock direction (all 4) -> make true in solution/tests (env byte-identical); R2 final-review root-login witness; SV-1 narrowed to Advisory (rule 6 'intruder created or changed'). Consolidated batch sent.
- 01:30 E batch applied (gates pass) but rescore 0/2: run_2 misses new backward-overlap sudo trap (unscreened, threaded 4 tests). Orchestrator: remove it (no graded record in overlap), keep backward steps graded.
- 01:34 E final_review recheck 1: F1-F5 closed; new should-fix: step range per sign not exercised (backward capped 900 s, forward 30 s missing), verification_explanation overclaims. Held pending clearance.
- 01:41 E clearance: SV-C Advisory, SV-D None, CRS-D None, CRS-C Minor (reference wrong on contract-valid backward steps: month-end crossing, overlap login settled by collector, rotation removing pre-step lines). Blocking clearance -> E contract STOPPED as rescope_required (no third round).
- Orchestrator (batch authority, user delegated all decisions): ONE rescope E2 from a revised scope ledger: guide narrows rule 1 to a host clock that ran behind and was stepped forward at most once (drops the backward promise every CRS finding concerned). env changes -> fresh skeleton pair + fresh narrow panel (discovery+clearance) on the new contract. Not counted as another clearance of E.
- 01:44 E2 rescope done (snapshot 630a3788; image ee2ed6c6 :skeleton4; rule 1 forward-only + surviving pre-step line; 27 sealed; all gates pass; info rescore run_1 0 / run_2 1). contract r5 (rule 1) launched.
- 01:45 contract r5: one answer per field; potential blocker (backward sealed cases) verified closed (all step_s >0 or none). E2 fresh pair cycle-3 launched.
- 02:09 E2 cycle-3 raw 1/2: run_1 solved; run_2 fails persistence only (9 families) by reading 'during the intrusion' as [initial access, collection] -> ambiguity (= SV-1, SV-D note). Pair DISCARDED. Rule 6 wording repair + fresh pair cycle-4.
- 02:10 E2 rule 6/7/4 wording fixed (snapshot 766a90e9; image 67c51ed3). Fresh pair cycle-4 launched.
- 02:22 E2 cycle-4 = 2/2 (claude-opus-5, all families both). E STOPPED rescope_required (re-probe 2/2 after the scope cut); task folder moved to workspace/dropped/. Batch paused for user report: 0/3 delivered after 5 candidates (A-D seeded-departure, E forensics).
F. (Hardware/RTL, same-cycle interaction lane) builder phase1 launched 07:32
- 07:44 F phase1 done (tbrain-virtual-channel-credit-arbiter; from-spec VC credit arbiter; 8 wrong orderings each fail; svr 2 self; image 98b21f7d). contract r1 launched.
- 07:46 F F1 fixed (§4.4 reading kept; image 89fb7a3e). Skeleton cycle-1 launched.
- 07:52 F skeleton cycle-1 = 2/2 (claude-opus-5, all 8 families, ~4-5 min each; both wrote an independent model + random bench). F REJECTED without strengthening (no inference lever: spec fully determines every bit; reviewer/builder both predicted collapse). Batch paused: 0/3 after 6 candidates.
G. tbrain-supplier-rebate-settlement Operations/Supply chain (workers-comp shared-constant recipe x2 + loop trap) builder launched 07:54; user: continue until one task delivered
- 08:14 G phase1 done (7 departures; TA MINIMUM_CREDIT shared settle/protection, TB HANDLING_PER_UNIT shared returns/chargeback, TC carton loop; svr 3; image 770197b1). contract r1 launched.
- 08:15 G contract r1: should-fix (5.1/5.2 totals give closed reading for TA/TB) UPHOLD; svr 2 advisory. Repair sent.
- 08:16 G r1 fix (5.1/5.2 per-item subject + 5.3 every line; image 880bc9d2). Skeleton cycle-1 launched.
- 08:21 G skeleton cycle-1 = 2/2 (claude-opus-5; both split shared constants on sight, cued by reach sentence 'every constant at its value today' + visible imports). One strengthening sent: sharing through a data-keyed table (no import/grep trail).
- 08:24 G strengthened (rates.py FIGURES/USES table; image 8c825cfa). Skeleton cycle-2 launched.
- 08:28 G skeleton cycle-2 = 1/2 (claude-opus-5): run_1 solved; run_2 fails TA+TB only (gated all notices/sales on 2.4/2.5 subjects = exclusion reading, misread today's code as zero). Contract unchanged since r1 repair; judged legitimate miss. CORE+ -> phase 2.
- 08:41 G phase 2 done (25 tests; strict/determinism/independence/16 wrong paths/bounds 25/sweep 21/precheck full pass; rescore 1/2 on real verifier). Budget trim + panel packets requested.
- 08:52 G panel discovery: CRS-A None, CRS-B None, SV-A Advisory, SV-B Advisory (growth half-cent; RELABEL_SEED urandom noted). final_review: F1 should-fix narrowed to polish (reason recorded), F2/F3 polish. Consolidated tests/solution batch sent.
- 09:04 G clearance: SV-C1 None, SV-C2 None, CRS-C1 None, CRS-C2 None. Packaging + submission sent.
- 09:05 G DELIVERED builder_certified: ZIP workspace/submissions/tbrain-supplier-rebate-settlement.zip sha256 fcf8bdf4...a1bcf; SUBMISSION-tbrain-supplier-rebate-settlement.md; panel_gate check passed (snapshot a0d735d6); preflight package strict + panel:receipt pass; local probe 1/2 claude-opus-5. Delivered 1/3. Batch stopped per user ('stop when a task is obtained').
## Continue (user: 'tiếp đủ 3 task') 09:16
H. tbrain-crop-hail-loss-adjustment Operations/Claims (G mechanism: data-table shared figures x2) builder launched
- 09:40 H phase1 done (8 departures; TA trace_tenths shared, TB small_cents shared; svr 3; image a38576f9). contract r1 launched.
- 09:43 H contract r1: F1 blocking (6.2 'carries one line' vs clamp), F2/F3 should-fix; svr 2. Repair sent.
- 09:48 H r1 repaired (snapshot ce868ca3; image 5251f2f9). contract r2 launched.
- 09:49 H contract r2 clean (svr 2 advisory). Skeleton cycle-1 launched.
- 09:54 H skeleton cycle-1 = 2/2 (claude-opus-5; both read STEPS map in figures.py and split). One strengthening sent: data-derived lookup keys (no literal link).
- 10:02 H strengthened (unit.kind keys via UNITS; contract text byte-identical; image dfcfe8ff). Skeleton cycle-2 launched.
- 10:10 H skeleton cycle-2 = 2/2 (claude-opus-5). H REJECTED; moved to dropped. Note: G's held miss was the EXCLUSION reading (domain instinct zeroes small items), not the in-place edit.
I. tbrain-sales-commission-statement Operations/Finance (exclusion-pull + shared table) builder launched 10:10
- 10:32 I phase1 done (7 departures; TA courtesy credits window_days shared, TB trial orders small_cents shared; svr 3; image d7f12825). contract r1 launched.
- 10:36 I contract r1: F1/F2 should-fix (reach clause lets window move; README 'new-logo bonus' misdirects), F3-F5 polish; svr 2. Repair sent.
- 10:39 I r1 repaired (image cf9461f9). contract r2 launched.
- 10:40 I contract r2 clean (svr 2). Skeleton cycle-1 launched.
- 10:43 I skeleton cycle-1 = 0/2 (claude-opus-5): both runs fail TA+TB only by exclusion reading (0 for courtesy credits / trial orders). Contract r2 one-value -> legitimate. 0/8 screen: <=1 soft flag each (contrary instinct), isolated, no competing enumeration -> 0/8 RISK carried (icpms precedent), not blocker. Phase 2 sent.
- 12:44 I phase 2 done (24 tests; strict/determinism/independence pass; 15/15 wrong paths; sweep 25/25; bounds 19/19; precheck full clean; rescore 0/2). final_review + panel discovery (SV-A/B, CRS-A/B) launched.
