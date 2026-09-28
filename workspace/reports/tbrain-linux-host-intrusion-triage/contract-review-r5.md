# Contract review r5 (blind): tbrain-linux-host-intrusion-triage

Scope: contract-review-packet-r5 only. Compared with r4, the changes are these:
- case-guide rule 1: the clock is now "run behind ... then been set forward, at most once", with the added promise "the auth logs always keep at least one line from before the step that the collector also holds";
- rule 4 and rule 6 carry the key and "exactly 2 seconds" wording already seen in the final task.

instruction.md, the other docs and the case-1 evidence are unchanged from r4.

## Case-1

The r4 hand reconstruction still stands. The step is a forward step of 6036 s (the host ran behind), bracketed in true (17:20:39, 17:51:33], and the gap is shorter than N. That gives:

| Field | Value |
|---|---|
| initial_access | git / 77.157.180.252 / 2021-12-29T16:39:40Z |
| sources | {77.157.180.252, 193.3.49.175} |
| accounts | {git, root} |
| privilege_escalation | 2021-12-29T16:49:04Z |
| persistence | {/etc/rc.local, /etc/cron.d/apt-cache-clean, /home/git/.ssh/authorized_keys} |
| first_activity | 2021-12-26T18:12:49Z |
| last_activity | 2021-12-29T17:53:04Z |

Every field has one answer, and the new rule 1 fits case-1: its clock ran behind and was set forward.

## Findings

1. **No new ambiguity.** A forward-only step makes the pre-step and post-step host times disjoint. Every pre-step raw time is below the step line's host time, and every post-step raw time is at or above it. Together with "settles which side", a split by host time at the first line that agrees with the collector is the only answer. The new "at least one line from before the step" promise guarantees that N can be measured from the auth log itself, even after rotation. That closes the r3/F2-style gap where rotation could remove every pre-step pair (wtmp pairs would have survived anyway).
2. **polish (signposting):** "run behind ... set forward" now tells the solver the sign of the error, and the new promise tells them where to look for it (auth-log lines that the collector also holds). This lowers the difficulty a little: the solver no longer has to allow for a fast clock or a missing anchor. It is not a fairness defect, and it matches the definitional style of the guide. If the task was meant to stay silent on direction, this sentence gives the direction away.
3. **polish (instruction range wording):** instruction.md still says "one clock step of 30 to 7,200 seconds", with no direction. It is consistent with the guide now that the guide fixes the direction, so no change is needed.
4. **Cross-check note (not visible to a blind solver):** my full-visibility Recheck 1 found that the generator produces *backward* steps (the clock ran fast and was set back) in 9 sealed cases. If the sealed tests still contain those, rule 1 as now written ("run behind ... set forward") **contradicts the graded evidence**. That would be **blocking**. Before shipping, make sure the generator and the sealed cases were changed to forward-only steps, or restore rule 1's direction-neutral wording.

**Verdict:** the contract gives one answer per field, and the clock is unambiguous. The only risk is consistency with the sealed cases (finding 4).
