# Contract review r1: tbrain-linux-host-intrusion-triage

Scope: instruction.md plus environment/ (docs/case-guide.md, record-formats.md, report.md, triage.py stub, evidence/case-1). This is a from-scratch analyzer task, not a repair. I read the case guide as the grading authority.

## Part 1: Contract findings

1. **should-fix: no join key between a wtmp login and its `Accepted` line.** Rule 4 says "The auth-log `Accepted` line of a login gives its method and, for a key, the key fingerprint", but it never says how the two are matched. Rule 8 depends on the match ("every login whose `Accepted` line names an attacker key's fingerprint"). Counterexample: two wtmp USER_PROCESS records for `ops` from 198.51.100.7 land in the same second, and two `Accepted publickey for ops from 198.51.100.7` lines land in that second with different fingerprints. One reader matches by (user, addr, second) in order, another by (user, addr, nearest time), and a third also uses the pid. The attacker-login set, and so `accounts` and `sources`, can differ. The matching also depends on the clock-corrected times, which rule 3 only implies. Suggested fix: add one sentence, for example "a login's Accepted line is the one with the same account and address at the same corrected second".

2. **should-fix: rule 7, "public key whose text appears".** The rule doesn't say what the "text" is: the base64 blob, the whole `ssh-ed25519 <blob> <comment>` line, or a key that also appears in an authorized_keys file. Counterexample: the history has `echo AAAAC3Nza...XYZ >> ~/.ssh/authorized_keys`, which holds the blob but no `ssh-ed25519` type word. A blob-substring reader derives a fingerprint and a full-line reader does not. It is also unclear whether the whole history counts or only commands inside attacker sessions. Rule 12 restricts to sessions for activity, but rule 7 has no such restriction. Suggested fix: add "the base64 blob of an `ssh-ed25519` key appearing anywhere in the history file".

3. **should-fix: rule 11, the bound of "within 2 seconds".** It could mean |ctime − t| ≤ 2 or < 2. Counterexample: a dpkg-listed file with ctime exactly 2 s after `status installed`. Also, is `t` the rule-3-corrected dpkg time? It should be, but the rule doesn't say so. Rule 5 states its inclusive bound ("at most 600 seconds"), so this one should match it.

4. **should-fix: rule 11 path scope.** In "under `/etc/cron.d/`, `/var/spool/cron/crontabs/` or `/etc/systemd/system/` (a `.service` or `.timer` name, any depth)", the phrase "any depth" reads as belonging only to systemd. So is `/etc/cron.d/sub/x` persistence? Also, "every `.ssh/authorized_keys` of a home directory" could mean only `/home/<u>/.ssh/authorized_keys`, or it could also cover a nested path such as `/home/u/backup/.ssh/authorized_keys`, or a home outside `/home` (e.g. `/srv/git`). Counterexample: an attacker-session ctime on `/srv/git/.ssh/authorized_keys`. Home dirs are defined only through `home/<user>` in record-formats.

5. **should-fix: rule 3 and fuzzy reference points.** "every other host-clock time (rule 1) earlier than the step line's own time" doesn't say whether the raw host time or the corrected time is compared to the step line's (corrected) time. In practice raw values in [step−N, step) can only come from before the step, so comparing raw values gives one consistent answer. A reader who compares after adding N gets a different partition for raw times in [step−N, step). Suggested fix: add the word "uncorrected".

6. **polish: rule 2, year inference and Feb 29.** A `Feb 29` line in an inferred non-leap year cannot happen if the year walk is right. The walk uses raw month order before the step correction, which is fine. The rule is clear, but it doesn't say that the step correction is applied after the year is assigned. Counterexample: a step of 7200 s across midnight on Dec 31. Assigning the year before correcting gives Dec 31 + 2 h, which crosses into the new year. That is correct under either order only if the reader converts to a datetime before adding N.

7. **polish: rule 12, "failed attempts from attacker addresses"** is sourced from btmp (rule 4) and auth-log `Failed` lines duplicate it. The two agree on time after correction unless rotation dropped lines. The rule is fine, but it could name btmp explicitly.

8. **polish: rule 12 includes admin-written root history.** Once `root` is an attacker account, any stamped root-history command inside *any* attacker session counts, including one typed by an administrator in their own concurrent session. The text governs this case positively, so it is not a defect, but it goes against expert intuition. Solvers who "improve" the rule will be marked wrong. The design should make sure it is intended.

9. **polish: the sudo TTY match** in "the session open on its TTY at the line's time" relies on the wtmp `line` field equalling `TTY=pts/N` as text. That is clear enough. The session ends are inclusive, which is stated.

No numeric range is missing its floor or ceiling. Offsets, years, step size, file count and window are all bounded, and the output time format is fixed. The set semantics are stated. There are no rounding conventions to check (whole seconds; `tv_usec` is ignored).

## Witnesses (hand-derived)

W1. The offset is `+05:45`, and an auth line `Mar  1 00:10:00` in 2024 gives 2024-02-29T18:25:00Z.

W2. Collected 2021-01-03T11:29:23Z at −08:00, so local time is 2021-01-03 03:29:23. The last auth.log line is `Jan  3 03:00:00`, which gives year 2021. The line before it, `Dec 30 ...`, has a month later than Jan, so it gets 2020. (This matches case-1's shape.)

W3. The btmp failures from X are at t, t+100, t+200, t+300, t+600, so X is hostile. With the fifth at t+601 and only five attempts, X is not hostile.

W4. There is a step of N=300 at step time S. A btmp record raw at S−10 is reported at S+290. A wtmp login raw at S+10 stays at S+10.

W5. The history of attacker account `deploy` contains `ssh-ed25519 <blob> k`. The fingerprint is SHA256:b64(sha256(b64decode(blob))) with `=` stripped. A later `Accepted publickey for ops ... SHA256:<that>` login from a benign address becomes an attacker login, so `ops` and its address are added to accounts and sources.

W6. `/etc/cron.d/kworker` has a ctime inside an attacker session and is not listed by any package, so it is persistence. If `cron.list` listed it and dpkg had `status installed cron:amd64` 1 s from its ctime, it would be excluded.

W7. An attacker is logged in on pts/2 and admin alice on pts/1 does `sudo ... USER=root` during that time. That is not escalation because the sudo is on pts/1. If the attacker's pts/2 session has a sudo line, escalation is that line's time.

W8. An attacker session has no DEAD_PROCESS, so it runs to collected_utc and a persistence ctime 1 h before collection counts.

The only guesses were in W5, over what counts as key "text" (finding 2), and in W6, over whether the 2 s bound is inclusive (finding 3).

## Part 2: Solver-path screen

**A) Pre-mortem.** A strong solver reads the three docs and writes a parser for the gz logs, the utmp structs, the histories and fs-listing. It implements the year walk, the step correction, the hostile window and the fixpoint loop, then runs on case-1 and eyeballs the output. With no expected report it builds its own generator for self-tests, and that generator is only as good as its reading of the rules. The likely failure points are these:

- applying the step to non-auth host times with the wrong partition, or forgetting that btmp, wtmp, history and ctime also need it;
- the year walk across Dec→Jan combined with rotated-away lines;
- the fixpoint order (the root escalation brings root's history into rule 7);
- including admin root-history commands (it may wrongly filter them by session owner);
- the join ambiguity in finding 1;
- the dpkg 2 s bound;
- missing the `cron.d` ctime-vs-mtime trap (the guide says it outright, so this is unlikely).

Each rule is local and explicit, and the combined state is closed-form. Most of the risk comes from volume and edge interactions, not from any hidden insight.

**B) Scores (5 = strongly resists)**

- reference_unreachable: 2. The guide is a complete algorithm.
- authority_incomplete_for_grading: 2. Findings 1–5 are real but narrow, and will bite only if the hidden cases exercise them.
- hidden_state_not_closed_form: 2. The fixpoint and the step correction are deterministic and stated.
- restraint_traps: 2. There are two: the admin root-history inclusion (a positive rule that goes against intuition), and the dpkg exclusion sitting inside the persistence aggregate. The mtime trap scores zero because it is written into the rule.
- fuzz_blind_spot: 3. The many interacting variation axes (step × year crossing × rotation × fixpoint) are hard for a solver to self-fuzz correctly without a reference.

**C)** self_verification_resistance: 3. prediction: resists weakly, with around 1 of 2 solvers fully solving. The main failure is an edge interaction, not a comprehension gap. confidence: low-medium. decisive_reason: every rule is explicit and local, so full solves depend on getting many interacting clock/year/fixpoint edges right across fuzzed hosts with no reference report, plus the unstated login-to-Accepted join.
