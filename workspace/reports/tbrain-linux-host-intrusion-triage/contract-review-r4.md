# Contract review r4: tbrain-linux-host-intrusion-triage

Scope: contract-review-packet-r4. The guide adds four sentences: one in rule 1 on the step side, one in rule 4 on tying credentials, one in rule 6 on package-written files, and one in rule 7 on collection time. The other docs and instruction.md are unchanged. Case-1 was regenerated: every host-clock value moved by −1583 s, and the true (remote) times are unchanged.

## r3 findings

| r3 # | Status | Evidence |
|---|---|---|
| F1 password credential (blocking) | **Closed** | "The credentials that tie are the keys the intruder added; a password the intruder shares with an account's regular user ties nothing by itself." 10.233.9.93 (git by password on Dec 23, 25 and 29) is excluded. |
| F2 step window | **Closed** (by guarantee) | "The collector's record always settles which side of a step every graded host-clock time lies on." |
| F3 open session and last activity | **Closed** | "that collection time is not an event of the intruder." |
| F4 package-written files | **Closed** | "A file the package manager wrote (its ctime within 2 seconds of a `status installed` line for a package that lists it) is never persistence." |
| r3 polish: touch -r ctime realism | **Fixed** in the data | rc.local ctime now equals the `touch -r` stamp (15:12:50 raw). |

## Case-1 by hand (r4 data)

- **Clock:** the remote/auth/wtmp pairs give N = **6036 s**. For example, the git login from 77.157.180.252 reads 14:59:04 raw and 16:39:40 remote. The pts/1 logout reads 15:40:03 raw and 17:20:39 true. From the 17:51:33 Accepted line onwards the offset is 0. The step lies in true (17:20:39, 17:51:33], and that 1854 s gap is shorter than N, so every raw time is classified uniquely:
  - a slow time must have a raw value below 16:21:57;
  - a correct time must have a raw value of 17:20:39 or later.
- **Hostile address:** 77.157.180.252 has btmp failures at 14:48:06 and 14:58:06 raw, exactly 600 s apart, so it is hostile.
- **initial_access:** git / 77.157.180.252 / **2021-12-29T16:39:40Z**.
- **sources:** {77.157.180.252, 193.3.49.175}. The second is tied because the history key `...HR8JsjYu root@vps` has fingerprint SHA256:c7vui0D9…, which matches its Accepted line. 10.233.9.93 is excluded by the new F1 sentence.
- **accounts:** {git, root}.
- **privilege_escalation:** `sudo /bin/bash` on pts/0 at 15:08:28 raw + 6036 = **2021-12-29T16:49:04Z**. Neither tpham's pts/2 sudo nor git's pts/1 sudo from 10.233.9.93 counts.
- **persistence:**
  - Included: `/etc/rc.local` (ctime 16:53:26), `/etc/cron.d/apt-cache-clean` (16:54:13) and `/home/git/.ssh/authorized_keys` (16:57:13). All three fall inside the pts/0 intruder session, 16:39:40–17:11:55.
  - Excluded: `apt-listchanges`, whose ctime equals its dpkg install time of 15:18:57 raw. Also excluded: `certbot-renew`, whose raw ctime of 15:46:00 is slow, so its true time is 17:26:36, when no session was open (its mtime was forged into the session).
- **first_activity:** btmp from 77.157.180.252 at 12-26 16:32:13 raw + 6036 = **2021-12-26T18:12:49Z**.
- **last_activity:** the pts/0 sudo at 17:53:04 in the open 193.3.49.175 session gives **2021-12-29T17:53:04Z**.

Every field has one answer, and I made no guesses.

## New findings

1. **should-fix (low): who "added" a key when two sessions overlap on the same account.** Rule 4 now ties by "the keys the intruder added". In case-1 the `echo ... >> ~/.ssh/authorized_keys` line in git's history is unstamped. authorized_keys' ctime (16:57:13) falls inside the intruder's pts/0 session **and** the regular user's concurrent pts/1 git session (16:42:35–17:20:39). Attribution to the intruder rests on judgement:
   - the key's `root@vps` comment;
   - the recon sequence (`id`, `uname -a`, `cat /etc/passwd`, `sudo -l`) that comes before it;
   - later use only from a never-seen address.

   It holds in case-1, but a hidden host where the regular user's session is the only one open at the ctime, or where the key comment is neutral, would be undecidable. Suggested fix: add "a key is the intruder's when it was written into authorized_keys during an intruder session", or guarantee that the generator never overlaps such writes with a regular-user session on the same account.
2. **polish: "within 2 seconds" (rule 6)** no longer says whether exactly 2 s counts. r2 had fixed that, and the new wording drops it. Add back "at most 2 seconds before or after; exactly 2 counts".
3. **polish: "regular user"** is undefined. In case-1 it is plainly the prior-logging-in 10.233.9.93, and the rule reads fine with the key-only tie. No change is needed unless hidden hosts have an intruder password with no regular user.

## Short solver screen

- **Pre-mortem:** a strong solver fits the step from the remote log, applies the key-only tie, the TTY sudo attribution, ctime-in-session with dpkg exclusion, and the event list. All the remaining forks are closed. The risk left is implementation care (step classification, the fixpoint via root history, the 600 s boundary, forged mtime) and new finding 1 on hidden hosts.
- **Scores:**
  - reference_unreachable: 2
  - authority_incomplete_for_grading: 2 (finding 1)
  - hidden_state_not_closed_form: 3 (the step bracket and attribution are inferred, not given)
  - restraint_traps: 2
  - fuzz_blind_spot: 3
  - self_verification_resistance: 3
- **Prediction:** it resists weakly, with about 1 of 2 solvers fully solving. **Confidence:** medium. **Decisive reason:** the contract now gives one answer for every field, so the difficulty is legitimately in inferring the step and attributing activity from evidence. The one remaining fairness gap is how to attribute a key write when sessions on the same account overlap.
