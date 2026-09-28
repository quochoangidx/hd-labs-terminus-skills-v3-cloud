# Contract review r3: tbrain-linux-host-intrusion-triage

Scope: contract-review-packet-r3 (instruction.md plus environment/). instruction.md is unchanged. case-guide.md is cut to 7 definitional rules. record-formats.md adds `var/log/remote/<hostname>.log` (sshd lines stamped by the collector's correct clock, failures dropped), `Connection closed ... [preauth]`, "every key is ed25519", the fingerprint formula, and "directories are not listed". The case-1 evidence was regenerated (offset −12:00, collected 2022-01-03T22:11:49Z).

Question under review: for each report field, does evidence plus definitions give exactly ONE answer, or does a field hang on an undocumented convention?

## Case-1 reconstruction (hand-worked, raw host times converted to UTC)

- **Clock:** the remote log pairs with auth/wtmp sshd events. Before the step, every pair differs by **+4453 s**, e.g. the git login at 77.157.180.252 is 15:25:27 raw and 16:39:40 remote, and the three logouts on Dec 29 match at +4453 as well. From the `Dec 29 05:51:33` Accepted line on (17:51:33 in both), the difference is 0. So the step size is exact (N=4453), and the step lies in true (17:20:39, 17:51:33]. That gap (1854 s) is shorter than N, so every raw host time in case-1 has a unique slow/correct classification: a raw time before the step reads below 16:37:20, and a raw time after it reads at 17:20:39 or later. The remote log also gives every year, so the year walk becomes trivial.
- **Hostile address:** 77.157.180.252 has btmp failures at 15:14:29 … 15:24:29, exactly 600 s apart, so it is hostile. That is the boundary case. 193.126.98.46 (ivan) has five failures spanning 633 s, so it is not hostile (a trap: ivan did log in afterwards). 77.146.61.220 is hostile but never logged in.
- **Initial access:** git from 77.157.180.252 at **2021-12-29T16:39:40Z** (pts/0).
- **Concurrent sessions:** git from 10.233.9.93 on pts/1 at 16:42:35 (this address used git by password on Dec 23 and Dec 25 as well), tpham by key on pts/2 at 16:43:36, and git from 193.3.49.175 by key on pts/0 at 17:51:33, with no logout.
- **Key tie:** git's history has `echo 'ssh-ed25519 AAAAC3...HR8JsjYu root@vps' >> ~/.ssh/authorized_keys`. I computed its fingerprint as `SHA256:c7vui0D9kxWx/qfgjQ3ICe80suC0On1uS34V0txnu/c`, which equals the 193.3.49.175 Accepted fingerprint. So 193.3.49.175 is an intruder source.
- **Sudo:** tpham on pts/2 at 16:45:45 (apt-get update) is admin. git on pts/1 at 16:47:02 (`systemctl restart app`) belongs to the 10.233.9.93 session. git on pts/0 at 16:49:04 (`/bin/bash`) is the intruder. git on pts/0 at 17:53:04 (`systemctl restart apt-cache-clean.service`) is after the step and in the 193.3.49.175 session, so it is the intruder.
- **Persistence (ctime, corrected):**
  - `/etc/rc.local`: ctime 16:53:24, and its mtime was forged back to November with `touch -r`. Included.
  - `/etc/cron.d/apt-cache-clean`: ctime 16:54:13. Included.
  - `/home/git/.ssh/authorized_keys`: ctime 16:57:13. Included.
  - `/etc/cron.d/apt-listchanges`: its ctime equals the `status installed apt-listchanges` time exactly (16:59:33), and it is in apt-listchanges.list. The intruder's root shell had already `exit`ed (root history, 16:55:07), so this is the package manager. Excluded.
  - `/etc/cron.d/certbot-renew`: mtime 16:43:38 is inside the session, but raw ctime 16:12:23 is slow-era, which makes it true 17:26:36, when no session was open. Excluded.
  - The other cron.d files have ctime equal to their package install times on other days. Excluded.

## Part 1: Findings

1. **BLOCKING: rule 4, "a credential ... the intruder used ties further logins".** The intruder got in with git's *password*. The pts/1 login from 10.233.9.93 at 16:42:35 used git's password too. Read literally, that ties it to the intruder, which adds 10.233.9.93 to `sources`. It also moves `privilege_escalation` to **16:47:02Z**, because the pts/1 `sudo systemctl restart app` then becomes an intruder command, instead of **16:49:04Z**. The expert reading is that 10.233.9.93 is the account's regular user, since it logged in the same way on Dec 23 and 25 before any hostile activity. That reading gives one answer, but nothing in the guide says a shared account password is not a tying credential while a new key is. The two readings produce different `sources` and `privilege_escalation` in case-1 itself, and this is exactly the "another user's sudo during the intruder's session" question in its hardest form: same account, different terminal. Fix: define "credential" as a key fingerprint, or say that logins from an address that logged in to that account before the initial access are not tied by the password. It also has to be stated whether the tie is by address history or by something else.

2. **should-fix: rule 1/rule 7, where the step falls in general hosts.** The step size is always exact, because any pre-step sshd event has a remote twin. The step *point* is known only to lie between the last slow and the first correct sshd event. For a non-sshd host time with raw value X (a btmp failure, which the collector drops; a sudo line; a history stamp; a ctime; a dpkg line), the answer is unique only if X < U−N (slow) or X ≥ L (correct), where L and U are those two anchors' true times. When U−L > N, raw values in [L, U−N) are undecidable. Case-1 is safe (U−L = 1854 < N = 4453), but instruction.md allows N as small as 30 s and sessions of hours with no sshd lines in between, so hidden hosts will often have such a gap. The ordering of auth-log lines does not fully fix this either: a forward jump in raw time between consecutive auth lines is a strong hint, but hourly CRON noise gives natural gaps up to 3600 s > N. This is fair only if the generator never puts a graded event in the undecidable window. The contract promises nothing of the kind. Fix: state that guarantee in the guide ("every event whose side of the step matters falls outside the window the sshd record leaves open"), or restore a logged step line.

3. **should-fix: the last-activity end point in rule 7.** Rule 7 contains the line "A session with no logout record was still open at `collected_utc`." The 193.3.49.175 session has no logout. One reader treats the still-open session end as an event, so `last_activity` = **2022-01-03T22:11:49Z**. Another reads the list of "recorded events" literally, so `last_activity` = **2021-12-29T17:53:04Z** (the last sudo). This changes case-1's answer. Fix: say whether the open session's end is an event.

4. **should-fix: whether packages running during the intruder's root session count as persistence.** "files ... that the intruder created or changed" plus dpkg.log and .list files let an analyst attribute a file to the package manager. The guide doesn't say whether a package installation made *while the intruder held root* (they may have run `apt install`) is the intruder's. The instruction says installations happen "at any time", so hidden hosts may hit this case. In case-1 it resolves because the root shell had exited, but only barely: 4.4 minutes of margin, and it relies on a history `exit` stamp. The ctime-to-dpkg matching tolerance is also unstated (case-1 matches exactly). Fix: one sentence, e.g. "a file dpkg.log shows the package manager writing is never the intruder's".

5. **polish: forged mtime.** This case is fair, because ctime-over-mtime is standard forensic knowledge and the instruction hints at it ("files whose mtime says something other than their ctime"). There is one realism slip. `touch -r /etc/hostname /etc/rc.local` at raw 15:39:13 would set rc.local's ctime to 15:39:13, but the listing shows 15:39:11 (the `vi` time). It doesn't change the output, since both are in the session, but a careful analyst may doubt the evidence.

6. **polish: another user's sudo on a different account.** tpham on pts/2 is excluded by user plus TTY with one answer. This part is fair.

7. **polish: year.** It is fully determined by the remote log for sshd lines. For non-sshd auth lines, month order plus neighbouring anchors fixes it. There is one answer.

8. **polish: failed attempts from the intruder's sources before the intrusion.** Rule 7 counts them, so the Dec 26 btmp failure from 77.157.180.252 opens the activity window three days before the break-in. That is unambiguous but counter-intuitive, and the text governs it.

## Field-by-field verdict (case-1)

| Field | Value I reached | Unique? |
|---|---|---|
| initial_access | git / 77.157.180.252 / 2021-12-29T16:39:40Z | yes |
| sources | {77.157.180.252, 193.3.49.175} | **no**: +10.233.9.93 under the literal "credential" reading (F1) |
| accounts | {git, root} | yes (10.233.9.93 is also git) |
| privilege_escalation | 2021-12-29T16:49:04Z | **no**: 16:47:02Z under F1 |
| persistence | {/etc/rc.local, /etc/cron.d/apt-cache-clean, /home/git/.ssh/authorized_keys} | yes in case-1; hidden hosts are exposed to F4 and F2 |
| first_activity | 2021-12-26T18:12:49Z (btmp 16:58:36 raw + 4453) | yes |
| last_activity | 2021-12-29T17:53:04Z | **no**: 2022-01-03T22:11:49Z under F3 |

Where I guessed: F1 (I took the expert reading) and F3 (I took the literal event list).

## Part 2: Solver-path screen

**A) Pre-mortem.** A strong solver builds parsers and immediately notices the remote-log offset. It fits N from paired sshd lines, brackets the step, and classifies other host times. That part is clean on case-1. Next it has to write attribution heuristics:
- ties by address and key;
- ties by TTY for sudo;
- ctime-in-session for persistence;
- dpkg matching to exclude package files.

The divergence comes where the guide is silent:
- whether the password credential ties in the regular user's 10.233.9.93 session, which some solvers will include because rule 4 literally says "credential";
- whether an open session ends at `collected_utc` for `last_activity`;
- how to classify host times in the step window when the anchors are sparse;
- whether package installs during a root shell count.

Self-tests can't settle any of these, because the solver's generator builds in its own policy. Failures will come from the hidden policy, not from forensic skill.

**B) Scores (5 = strongly resists)**

- reference_unreachable: 3. The reference is a heuristic attribution policy, not a stated algorithm.
- authority_incomplete_for_grading: **4**. F1 and F3 change case-1 fields, and F2 and F4 are open on hidden hosts. This is a defect, not difficulty.
- hidden_state_not_closed_form: 3. The step window and the attribution chain are inferable, but not closed-form in general.
- restraint_traps: 2. There are three legitimate ones: the forged-mtime exclusion of certbot-renew, other users' sudo, and the package-file exclusion. Each rests on standard forensic instinct. The 10.233.9.93 case fails the 0/8 screen (the literal authority text points the other way), so it counts as a contract defect, not a trap.
- fuzz_blind_spot: 4. Solvers can't fuzz against a policy they have to guess.

**C)** self_verification_resistance: 4 (for the wrong reason). prediction: **resists**, most likely 0–1 of 2 full solves, but mostly through F1/F3/F2 hidden-policy mismatch, which a quality panel would flag as unfair. confidence: medium-high. decisive_reason: case-1's own `sources`, `privilege_escalation` and `last_activity` each have two defensible answers under the cut-down guide, so graded outcomes depend on undocumented conventions rather than on reconstruction skill.

**Recommendation:** keep the inference-from-evidence design (the remote-log step fit, ctime over mtime, TTY attribution and dpkg matching are all fair and deducible). Add back three sentences:
1. what counts as a tying credential, and that a password shared with the account's regular user does not tie;
2. whether an open session's end counts as an activity event;
3. a generator guarantee (or explicit rule) that graded host-clock events never fall in the step's undecidable window, plus one sentence that package-manager-written files are never persistence.
