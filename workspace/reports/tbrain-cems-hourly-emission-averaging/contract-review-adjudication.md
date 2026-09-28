# Contract review r1: adjudication

| # | Severity | Builder | Orchestrator | Resolution |
|---|---|---|---|---|
| F1 | should-fix | accept | UPHOLD | DRP-4 now defines 2.7: "The firing ratio of a firing hour is (209 less the reference oxygen) divided by (209 less its oxygen average)." 3.2 now reads "its NOx average times its firing ratio". The 209 exists only inside a quantity that belongs to firing hours. For a valid hour that is not firing, the only procedure-determined inputs are its 3.1 averages and the reference oxygen. Its reported value comes from one present code path, `correction.corrected()` (oxygen held at 190, ambient 210), so readings 2 and 3 have no textual support. The silence clause is unchanged and still names no case. The reviewer's W5 value of 900 is what the model gives. |
| F2 | should-fix | accept | UPHOLD | This is closed by narrowing the section-1 limits. 1.4 now says "A CAL record always has a load of 1 MW or more, and an hour holding a CAL record holds no MNT or OOC record." Both (a) and (b) now fall outside the limits, so they are left entirely open. 2.3 has one reading on every in-limit job. `model.within_limits` enforces the new limit, the generators respect it, and the example job was regenerated. |
| F3 | should-fix/trap | accept as a fair trap, no change | no change | This is intended trap T1. The line is drawn by the defined term "lost hour" (2.5). |
| F4 | polish | no change | - | The rule already counts operating days. |
| F5 | polish | no change | - | The reviewer confirms there is no issue. |
| F6 | polish | no change | - | A partial first hour is governed by 2.1 and 2.3, and the fuzz family starts at any quarter. |

Receipts refreshed on snapshot f00f68b6… (receipts/panel-precheck-design-only.json):
- Fuzz, both seeds: agree.
- departure-trap-checks.json: pass. T1 step 118/118, T2 step 63/63. Trap natural fixes fail only their own family.
- Skeleton-scorer validation: oracle, shipped, T1nat, T2nat, D9.
- instruction-preflight: OK.
- canonical-smoke.
- Image sha256:398d9c21….
