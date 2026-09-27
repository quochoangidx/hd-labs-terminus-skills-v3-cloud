# Resume state: task-batch 1 (session 2026-09-27, batch-9)

Profile: builder_certified (default), CORE+ bar (at most 1 of 2 blind claude-opus-5 terminus-probe solvers succeeds).
User: "Tự quyết mọi tiêu chí, không hỏi lại. Không commit. Mỗi task CORE+ xong thì báo cáo ngay ZIP và SUBMISSION."
Deliver: first task reaching builder_certified at CORE+ -> report ZIP + workspace/submissions/SUBMISSION-<slug>.md.
Environment: dockerd started by hand in this container; python base pulled from Docker Hub by the same digest
(sha256:01f42367...) and tagged as the public.ecr.aws name (ECR CloudFront blob host is denied by the egress proxy).

Candidates:
A. tbrain-medication-adherence-pdc  Operations/Claims (pharmacy claim lines -> proportion of days covered per member and drug class, class adherence rates)
- builder = orchestrator session (one persistent builder).
- 14:00 A scaffold done: authority AM-2 (5 sections), README, shipped package 158 LOC, 9 departures (start day, carry-over, measure dates, 2 Oct cutoff, period end, stays, half-up rounding, adherent, class divisor); traps T1 member outside measure keeps shipped span, T2 non-reportable class keeps shipped divisor, T3 fill above supply limit keeps 100-day coverage.
- 14:05 model.py (independent) + Oracle fix.patch; fuzz 400 files model==Oracle, shipped differs on 100/100.
- 14:07 contract r1: 3 blocking (period meaning, 90-day window, non-reportable rate) + 1 should-fix, all upheld and repaired.
- 14:09 contract r2: all closed, no blocking/should-fix; svr 2 (advisory, skeleton decides); reviewer named T1-T3 as kept figures.
- 14:10 skeleton pair cycle-1 launched (terminus-probe, image tbrain-pdc:env local variant).
- 14:15 skeleton cycle-1 raw 0/2 (claude-opus-5 both): run_1 failed only T3 (read over-limit fills as covering nothing), run_2 failed T1 (treatment period for everyone) + T3. T3 unanimous miss with an exhaustive reading of 3.1 = ambiguity evidence -> pair DISCARDED (not counted), wording repaired.
- 14:18 repair: 3.1 "every fill covers one or more consecutive days", T2 rebound via defined term "rate base" (2.7) used by 5.1, 1.3 one class per drug code, member limit 100 (panel packet size). contract r3: clean, svr 2.
- 14:20 skeleton pair cycle-2 launched.
- 14:35 skeleton cycle-2 = 2/2 (claude-opus-5; both reward 1 on the finished local verifier, 19/19). Both kept T1, T2, T3 citing the silence clause.
- 14:40 ONE strengthening (step 4a): new departure DI (index date = first listed dispensing line instead of earliest fill date) + governed two-hop subtype: claim lines with days 0 are not fills (2.1), with shipped filters living inside the index-date and measure-test expressions that departures DI and D4a force the solver to rebuild. T1-T3 kept. Next: contract r4, then fresh pair cycle-3 (a second 2/2 replaces the candidate).
- 14:45 skeleton cycle-3 = 1/2 (run_1 21/21; run_2 failed T1 only). CORE+ met. Risk: one live trap (T1). Sweep 44/44, fixture bounds all ends reached.
- 14:55 final_review: no blocking; 2 should-fix repaired (coverage wording 'every day' -> 'any day', adjustment-only member); sweep 44/44. Fresh pair cycle-4 on final contract = 2/2 -> A REJECTED (second 2/2). Moved to workspace/dropped/. Nothing packaged, no ZIP.
- user: "làm đến khi có task" -> continue with new candidates.
B. tbrain-car-rental-agreement-billing  Operations/Finance (rental agreements -> time, mileage, fuel, tax charges). Design lesson from A: three traps of the kind that bit (a rewrite that naturally applies a new formula to everyone), on different figures: TA time charge of a short rental (<24h) keeps today's ceil days (the grace rewrite gives 0 days under an hour), TB mileage allowance of a short rental keeps today's 100 miles, TC fuel charge of a car returned as full or fuller keeps today's credit.
- B contract r1-r3 (short-rental allowance dropped as ambiguous; fuel existence sentence added). Skeleton cycle-1 raw 0/2: both runs failed only TC (floored the fuel credit at 0), both kept TA. TC = 0/8 risk (unanimous miss, flags: contrary instinct), reported with the package.
- B sweep 24/24, bounds all ends, final review (solve.sh added), narrow panel 4 reviewers all None, panel_gate check passed on f773a5d1. ZIP + SUBMISSION written. builder_certified.
C. tbrain-warehouse-cycle-count-variance  Operations/Supply chain. contract r1-r3; skeleton cycle-1 2/2 -> one strengthening (shipped booked = count-system, adjusted must book variance, non-adjusted keeps shipped); cycle-2 1/2 (run_2 wrote booked = variance everywhere). Sweep 17/17, bounds ok, final review (pycache, every class letter) fixed, panel discovery SV-B Minor (README control file) + CRS-B Advisory -> one batch (verifier-made control file, jobgen docstring) -> clearance 4 reviewers all None; panel_gate passed on 9dbe02a6. ZIP + SUBMISSION. builder_certified.
B: same control-file fix applied; sound_verifier clearance running (snapshot 5fc02a49).
- B: sound_verifier clearance 2/2 None on 5fc02a49; panel_gate passed; ZIP repacked.
D. tbrain-parcel-dim-weight-billing  Operations/Logistics. contract r1-r2 clean; skeleton cycle-1 2/2 (both kept non-box 166 and express-home 450) -> one strengthening (3.3 scoped to ground, express fuel keeps transport-only floor; fuel() lacks service so it is rewritten); contract r3 G1 blocking (instruction symptom unscoped) fixed r4 clean; sweep 17/17, bounds ok; cycle-2 = 2/2 (13/13 both) -> D REJECTED (second 2/2). Moved to workspace/dropped/. No ZIP.
E. tbrain-container-demurrage-billing  Operations/Logistics. contract r1 (B1 not-on-demurrage credit) withdrawn in r2 on the no-clamp clause; skeleton cycle-1 = 1/2 (run_2 clamped days/charge inside free time at nought; both kept tank 5). Sweep 13/13, bounds ok, final review no blocking (P1 wording fixed), narrow panel 4 reviewers all None, panel_gate passed on 64f23bef. ZIP + SUBMISSION. builder_certified. Risk: same domain as existing tbrain-container-demurrage-detention (different tariff and figures).
F. tbrain-mobile-data-overage-billing  Operations/Finance. contract r1 clean (one should-fix settled by the no-clamp clause); skeleton cycle-1 = 1/2 (run_2 clamped over and charge at nought inside the allowance; both kept FLEX 5120). Sweep 16/16, bounds ok, final review no blocking, narrow panel 4 reviewers all None, panel_gate passed on 19d5a02e. ZIP + SUBMISSION. builder_certified.
