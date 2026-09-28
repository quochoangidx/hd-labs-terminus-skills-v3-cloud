# 09c61abb v1 revision: stopped at clearance (rescope_required), 2026-09-28

Repair batch (tests only; instruction/environment/solution byte-identical to the graded zip):
all 7 panel findings reproduced at reward 1 on the returned snapshot and closed on the repaired one
(ledger: ../revision-ledger.json; Oracle 1, NOP 0; 38/40 wrong paths on their own witness, the two
harness exploits rejected by other tests).

Sound Verifier clearance (2 fresh reviewers, reviewers/sound_verifier-{A,B}.json) is blocking,
checked by execution against GNU sed 4.9:
- refuted: `#np` (GNU forces -n, as the manual says);
- confirmed, introduced by this batch: sweep_classes `s/\S/./g` over \v \f \r (GNU counts them as
  whitespace, manual says spaces and tabs);
- confirmed, pre-existing: empty match right after a match in s///Ng (matrix.json 1455-1464, 1706-1717;
  manual silent); mixed_1_2.json case `$D;0~1,+2N;...` reaches the left-open "range end read past by N".
Per task-revise-flag-remediation a blocking clearance stops; no ZIP was packaged or synced.
Same binary-vs-manual non-convergence that retired this task on 2026-09-26 (AGENTS.md §2).
