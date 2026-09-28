# contract_review adjudication (builder) — tbrain-driver-hours-of-service-audit

Review: contract-review.json (overall reject, self_verification_resistance 2). One redesign used.

| Finding | Builder | Evidence / action |
|---|---|---|
| CR-1 (blocking) | accept | Correct: the silent value was named in the instruction ("a time left below nought") and the rest-with-miles exclusion sat in the yard-move rule sentence itself (status-keyed), so both read as written departures. Redesign: (a) yard moves are now a defined term, 2.3 "a yard move is on-duty time in a stretch in which the truck covers one mile or more", used by 2.2; the exclusion of moving rest follows only through 2.1 (on-duty time is time that is not rest). The README signpost about team berths and co-drivers is removed; `miles` is described neutrally as recorded on every entry whatever its status. The per-minute walk now iterates every stretch and classifies each through `is_driving`, so the rebuilt classification feeds the shift driving, break and violation accruals. (b) The named "below nought" sentence is deleted; the silent value follows only from FM-4 1.5 ("provides for ... time left from nought up to the limit") plus the generic value-level silence rule. Envelope families made neutral ("entries of every status with and without miles"). |
| CR-2 | accept | Silence rule rewritten at value level: figures a silent value is made from are worked as the manual says, and only the step that turns them into the reported value keeps today's code; that step takes precedence over the no-guard wording. No function or value is named. |
| CR-3 | accept | Symptoms now match shipped behaviour (fuzz evidence in CR-3): 10-hour and window over-runs come out clean, violation minutes land on the shift's start day, time left is often more generous. |
| CR-4 | accept | Instruction states "time left is compared as a number to within 0.001"; witnesses avoid -1/-2 minutes (manifest discriminating_instance). |
| CR-5 | accept (intended) | A co-driver logged `on` in a moving truck is on-duty time covering miles, so under 2.3 it is a yard move and driving time. Decided by definition; verifier team cases will be consistent (moving `on` = driving; moving off/sleeper = rest). No extra sentence, to keep the exclusion a two-hop reading. |

## Recheck (contract-review-recheck.json: accept_with_fixes, SVR 3)

| Finding | Builder | Evidence / action |
|---|---|---|
| CR-6 | accept | 5.2 now reads "Time left that this manual provides for (1.5) is reported in hours, rounded down to a tenth of an hour"; 1.5 adds "judged on the exact time left of 5.1 before any rounding". No value named. |
| CR-7 | accept (verifier plan) | No contract change. Verifier plan: negative time left on all three keys (driving, window, cycle) with 1-, 2- and 3-minute residues below a tenth (e.g. -61, -62, -63, -7, -35 minutes; -1/-2 appear only where -0.0 vs 0.0 is within the stated 0.001 band and agree numerically, so they cannot discriminate and are not relied on); moving-rest cases with off, sleeper and `on` stretches carrying 1+ miles (`on` = yard move, driving time). Each in its own named test, no hints added. |
