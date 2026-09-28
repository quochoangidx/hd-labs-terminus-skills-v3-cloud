# Contract review r2: tbrain-linux-host-intrusion-triage

Scope: contract-review-packet-r2 (instruction.md plus environment/). instruction.md, record-formats.md and report.md are unchanged from r1. case-guide.md changed in rules 2, 3, 4, 7, 11 and 12. The case-1 evidence was regenerated (it now has 2 auth-log files and accounts `git` and `tpham`).

## Status of the r1 findings

| r1 # | Topic | Status |
|---|---|---|
| 1 | Join between a login and its Accepted line | **Closed.** Rule 4 now says "same account and address at the same second once both are corrected by rule 3" and "No two logins share account, address and second." |
| 2 | Key "text" and history scope in rule 7 | **Closed.** It is now the base64 blob after a named type word, "anywhere in the shell history file ... in any command at any time". |
| 3 | The 2 s bound in rule 11 | **Closed.** "at most 2 seconds before or after ... both times corrected by rule 3; exactly 2 seconds counts". |
| 4 | Path scope in rule 11 | **Closed.** cron paths at any depth, systemd `.service`/`.timer` at any depth, `/home/<user>/.ssh/authorized_keys` "exactly that depth; no other path is a persistence class". |
| 5 | Raw or corrected comparison in rule 3 | **Closed.** "whose uncorrected value is earlier than the step line's own time". |
| 6 | Year assignment before the step | **Closed.** "The year is assigned from the times as written, before any rule 3 correction." |
| 7 | Source of failed attempts in rule 12 | **Closed.** It now says "btmp failed attempts". |
| 8 | Admin root-history inclusion | Unchanged and still governed positively. It is a deliberate trap and not a defect, so I keep it as a note. |
| 9 | Matching the sudo TTY | Unchanged and acceptable. |

## New findings

N1. **should-fix: rule 7 now names key types that record-formats doesn't describe.** Rule 7 lists `ssh-rsa` and `ecdsa-sha2-nistp256/384/521`, but record-formats.md still fixes the Accepted line as "`Accepted publickey ... ssh2: ED25519 SHA256:FINGERPRINT`" and authorized_keys as "`ssh-ed25519 <base64 blob> <comment>`". Counterexample: the history contains an `ssh-rsa` blob, and an attacker login is logged as `... ssh2: RSA SHA256:x`. A parser written to the documented `ED25519` regex misses that login, and a tolerant one catches it. There are two fixes: widen the Accepted pattern in record-formats to `<TYPE> SHA256:...`, or drop the extra types from rule 7 if the hidden hosts use only ed25519.

N2. **polish: rule 4 doesn't cover a login with no Accepted line.** When there is no matching `Accepted` line, the reading defaults to "not a key login" and nothing else is needed. The guide could say so, but a competent reader will reach that reading anyway.

N3. **polish: are directories among "any path below `/etc/cron.d/`"?** fs-listing's "one row per path" could include directory rows. The case-1 listing has none, so the question only matters if hidden hosts list directories. A single sentence such as "fs-listing lists regular files only" would settle it.

N4. **polish: rule 11's wording is harder to parse.** The new sentence is long ("... (both times corrected by rule 3; exactly 2 seconds counts) was written by ..."). It reads correctly but is dense, and it can be split into two sentences without any change in meaning.

No new blocking issues. The silent/governed line holds: "no other path is a persistence class" closes the enumeration.

## Witnesses (re-derived against r2)

W1. The offset is `+05:45` and an auth line reads `Mar  1 00:10:00` in 2024 → 2024-02-29T18:25:00Z.

W2. There is a step of N=7200 logged `Jan  1 01:00:00`, and the preceding line reads `Dec 31 23:30:00`. The year is assigned before the step, so the preceding line is Dec 31 of year Y−1 and becomes Jan 1 01:30 of Y after adding N. That puts it after the step line in time but before it in reading order. The corrected time is still what counts.

W3. btmp failures from X are at t, +100, +200, +300, +600 → X is hostile. If the fifth is at +601 → X is not hostile.

W4. A btmp record has a raw value of S−10, where S is the step line's time and N=300 → it is reported at S+290. A raw value of S+10 stays S+10.

W5. The history of `git` contains `ssh-ed25519 AAAA... x`. The fingerprint is `SHA256:` + b64(sha256(decode(blob))) with the padding stripped. An `Accepted publickey for tpham` line naming that fingerprint makes tpham's login an attacker login, so tpham and its address are added.

W6. `/etc/cron.d/apt-listchanges` (listed by apt-listchanges.list) has a ctime 2 s after `status installed apt-listchanges:all` → excluded. At 3 s it is persistence if the ctime is in an attacker session.

W7. `/etc/rc.local` has an mtime reset with `touch -r` but a ctime inside the attacker session → persistence. (case-1's root history shows exactly this shape.)

W8. `/home/git/tools/.ssh/authorized_keys` → never persistence ("exactly that depth").

I had to guess only in N1, when a non-ed25519 Accepted line appears.

## Part 2: Solver-path screen (redo)

**A) Pre-mortem.** The guide is now a close-to-complete algorithm, and each r1 ambiguity has an explicit sentence. A strong solver parses the gz/utmp/tsv inputs and implements:
- the year walk before the step;
- the step using raw comparison;
- the hostile window;
- the rule 7/8/10 fixpoint;
- sessions, persistence with the dpkg ±2 s exclusion, and activity bounds.

It then self-tests by writing its own generator. The remaining failure points are:
- an ED25519-only Accepted regex, if hidden hosts use other key types (N1);
- fixpoint ordering, where root escalation brings in root's history keys;
- the step partition applied to all host-clock sources (btmp, wtmp, history, ctime, dpkg);
- the December→January year walk with rotated-away lines;
- the admin-root-history inclusion in rule 12, which goes against intuition.

These are careful-implementation risks, not comprehension gaps. The repaired guide gives an attentive solver fewer ways to go wrong.

**B) Scores (5 = strongly resists)**

- reference_unreachable: 2
- authority_incomplete_for_grading: 1 (with N1 fixed; 2 as it stands)
- hidden_state_not_closed_form: 2
- restraint_traps: 2 (the admin root-history inclusion and the dpkg exclusion sit inside the rebuilt persistence and activity aggregates; the mtime trap and the depth limits are written into the rule sentences and count zero)
- fuzz_blind_spot: 3 (the step × year crossing × rotation × fixpoint interactions are hard to self-fuzz without a reference)

**C)** self_verification_resistance: 2–3. prediction: likely collapses, and at best resists weakly, with 1–2 of 2 solvers fully solving. confidence: medium. decisive_reason: the repair removed every interpretive fork, so difficulty now rests only on implementation care across interacting clock, year and fixpoint edges, which a careful strong solver can self-check against the explicit rules.
