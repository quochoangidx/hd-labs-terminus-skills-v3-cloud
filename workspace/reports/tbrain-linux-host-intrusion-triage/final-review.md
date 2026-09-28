# Final review: tbrain-linux-host-intrusion-triage

Scope: the full task folder (instruction.md, task.toml, environment/, solution/, tests/). I extracted all 14 evidence tarballs into scratch and ran `solution/triage.py` over every sealed case. I compared the output with `tests/expected/*.jsonl` using the verifier's own semantics: sets for the three list fields, and exact matching for everything else.

**Result: all 26 cases match, with 0 differences.** The sealed `case1` evidence is byte-identical to `environment/app/evidence/case-1`. The shipped docs in `tests/shipped/docs` are identical to `environment/app/docs`, and instruction.md is unchanged from the r4 packet.

## Verdict

**Ready to submit, with no blocking findings.** Every graded field comes from `model.truth()`, which reads intruder-labelled scenario objects, and it agrees with an independent reference written from the guide. The guide's r4 sentences are backed by generator guarantees:
- `within_limits` puts collector lines at `tc-1` and `tc`, and keeps no graded event on `tc-1`;
- package installs avoid intruder windows (±120 s), except for the deliberate in-session package in the ctime family;
- the admin's root shell is kept 3600 s away from intruder windows.

## Checks

- **Assertion-to-source:** every field traces to guide rule 1–7 plus the evidence. `truth()` uses exactly the event classes in rule 7:
  - intruder failures from H;
  - session starts and ends, with an open end excluded;
  - sudo;
  - stamped root commands, only when the root history is stamped;
  - persistence ctimes.
- **Witnesses:** each family forces its own rule.
  - brute: the first-to-fifth failure span is exactly 600 s, plus a mistyping user at 601 s.
  - rotation: the auth log is cut at `brute[-3]`, so only btmp keeps the full burst.
  - sudo: the regular user's sudo runs on another pts before `t_pe`.
  - ctime: a forged mtime, an in-session package cron file, and a decoy with mtime inside the session and ctime outside it.
  - open: `REQUIRED` picks a seed whose last event is a stamped root command.
  - edge_lo/hi/late: every range end (offsets −12:00/+14:00, steps 30/7200 s, years 2019/2031, 1 and 6 auth files, package ctime −2/+2 s).

  Across the 26 cases, persistence covers rc.local (12), cron.d (10), systemd .service (10), .timer (10), crontabs (9), home authorized_keys (18) and root authorized_keys (5). 11 cases have more than one source and 3 have `privilege_escalation` null.
- **Equivalence policy:** it is sound. The report must have exactly the seven keys. The list fields must be lists of str with no duplicates and are compared sorted. `initial_access` values must be str. Everything else must match in type and value, so `null` vs `"null"` and int vs str are both caught.
- **Isolation:** the separate verifier image (`tests/Dockerfile`) runs `chmod 700 /tests /logs/verifier` before any candidate code. `_seal_app` rebuilds /app with only the delivered triage.py plus the shipped docs, root-owned 0644/0755, and evidence/ is removed. Each case is staged as `evidence` in a root-owned read-only mkdtemp. The candidate runs as uid 65534 under `setpriv --no-new-privs`, `-I -S`, with an empty environment, its own session and a 300 s cap. `test_candidate_cannot_read_verifier_files` shows /tests, the ROSTER, the expected files and /logs/verifier are unreadable. Case ids are hashed and the expected JSON is never staged. The candidate cannot steer which cases run, because the roster SHA-256 pins every file.
- **Oracle vs guide:** it is correct on every case (26/26). The step partition `t < step_t` (first agreeing raw time) is exact under the generator's `tc-1`/`tc` bracketing.

## Findings

1. **should-fix (witness gap): the "login as root" branch of rule 5 never decides a graded value.** `model.build` creates a root login (S2 as root) only when `key_target` is /root, and that requires `pe`, which always adds an earlier sudo (`t_pe < S1.end < S2.start`). So `privilege_escalation` always comes from the sudo, and `root` in `accounts` is already implied by it.

   Counterexample: a mutant that drops `esc += [s["start"] for s in atk if s["user"] == "root"]` from solution/triage.py passes all 26 cases. A mutant that ignores root logins for `accounts` also passes. The root key login's *address* is still tested, through `sources`.

   Fix: add one sealed case where the intruder writes a key into /root/.ssh/authorized_keys **without** sudo, for example via a writable file or a root password, and then logs in as root. Alternatively, accept this and remove "or a login as root" from the verification claims.
2. **polish: solution_explanation and the reference use a broader key rule than the guide.** The guide (rule 4) says a key counts when a history command "writes into an `authorized_keys` file". solution/triage.py (`KEY.findall(cmd)` over every command) and solution_explanation ("Keys whose text appears in an intruder account's history") take any mention. No sealed case tells the two apart, because the model only ever mentions a key in an echo/tee into authorized_keys. So grading is fair, but the task.toml text disagrees with the authority. Fix: change the solution_explanation wording, and optionally require `authorized_keys` in the command in the reference.
3. **polish: the fixpoint only covers root.** solution_explanation says the tie reaches "more accounts". In every scenario the only extra account comes from `root` via escalation or a root key login, because S2 is always either the victim or root. "through it, more accounts" in difficulty_explanation slightly overstates what the graded cases require.
4. **polish: `seal.py` couples case-1 by convention.** It copies `environment/app/evidence/case-1` but takes the truth from `model.build(1, "all")`. It never checks that the directory still equals `write_evidence(build(1, "all"))`. If someone edits the visible case by hand, it would carry a stale expected report. Today the two agree (26/26), but seal.py should regenerate case-1 from the model or assert that the bytes are equal.
5. **polish: the seal.py docstring** says `tests/expected/<family>.json`, but the files are `.jsonl`.
6. **polish: the "regular user" definition in rule 4 is circular.** "anyone who logs in to it from an address that is not the intruder's" depends on the intruder's addresses, which the rule is still building. It resolves in practice, because the password tie is explicitly empty, but "(a password never ties a login)" would be simpler.
7. **polish: the verification_explanation counts.** "26 cases in 14 named tests" plus "A final test" is right (15 test functions). The claimed mutant and wrong-analyzer results (13 + 12) are not reproducible from the folder, since there is no mutant harness. That is acceptable, but a reviewer cannot verify them.

## Folder and style

- The layout is clean.
- environment/.dockerignore excludes solution/ and tests/.
- The pinned python:3.13-slim digest is shared by both images.
- The verifier has no network, its timeout of 1800 s is above the internal DEADLINE of 1650 s, and it pins pytest.
- test.sh writes 0 before running and 1 only when pytest returns 0.

The task-visible prose (instruction, guide, record-formats, report) is consistent and specific, with no template phrasing or leakage of hidden-case facts. The instruction's variation list matches what the generator actually produces: the offsets list, N 30–7200, years 2019–2031, 1–6 auth files, a December→January crossing, rotation, a concurrent admin sudo, unstamped victim history, and forged mtimes.

## Recheck 1

Scope: this batch changed solution/, tests/ and task.toml. I re-extracted all 15 tarballs (30 cases) and ran the current solution/triage.py against tests/expected, using the verifier's semantics: **30/30 match, 0 differences.** The ROSTER covers 15 families, and the per-family case counts sum to 30. test_outputs.py has 16 test functions: 15 named tests plus the isolation test.

### (1) F1: root-login escalation. **Closed.**
- `rootlogin.jsonl` (1 case): `model.build(..., "rootlogin")` sets `pe = f["key"] = False` and adds S2 = `session("root", H, ...)`. The case therefore has no sudo, and `privilege_escalation` and `root` come only from the root login. It also has a backward step of 359 s.
- `test_rule_5_escalation_by_a_root_login_without_sudo` loads it.
- Mutant check: I deleted `esc += [s["start"] for s in atk if s["user"] == "root"]` from the reference. The mutant now **fails 1 case (rootlogin)** and passes every other family. That family is the witness.

### (2) Other r0 findings
- **F2 (key rule broader than the guide): closed.** The reference now fingerprints only keys in commands that contain `authorized_keys` (`KEY.findall(cmd) if "authorized_keys" in cmd else []`), and solution_explanation says "Keys that a command in an intruder account's history writes into an authorized_keys file".
  - Note: the variant that drops the `authorized_keys` filter still passes 30/30, so no case separates the two. That is fine, because the guide governs.
  - The "keys from every history" wrong analyzer in verification_explanation is best read as taking keys from *every account's* history. That would tie the admin's own key and its office address, so the claim is plausible.
- **F3 ("more accounts"): closed.** It now reads "ties a later key login from a new address, sometimes as root".
- **F4 (case-1 coupling): closed.** seal.py now regenerates `write_evidence(build(1, "all"))` and asserts that it is byte-equal to environment/app/evidence/case-1.
- **F5 (.json docstring): closed.** It now says `.jsonl`.
- **F7 (mutant claims unverifiable): not closed, polish.** There is still no mutant or wrong-analyzer harness in the folder. The claims ("Fifteen natural wrong analyzers", "Twelve one-edit mutants", "Oracle scores 1 three times") remain assertions that I checked only in part (root-login above, and the r0 check).

### (3) task.toml explanations: accuracy

- **difficulty_explanation:** accurate.
  - "ran slow or fast" matches the forward and backward steps now generated.
  - "sometimes as root" is correct.
  - "a package the unattended upgrader installed" names the ctime-family packages loosely (needrestart/apt-listchanges/debsums, and the model does not name an upgrader), but the claim is harmless.
- **solution_explanation:** accurate. The reference is 273 lines ("about 270"). The step logic matches the code: an error of either sign, auth lines split by file order, and other readings split by host time.
- **verification_explanation:** **two inaccurate claims (should-fix).**
  - (a) "steps of 30 and 7,200 s **in both directions**". A backward step comes only from `place_backward_step`, which draws `n = 30 if edge == 0 else R.randint(30, 900)`. So no case, and no possible case, has a 7,200 s backward step. The sealed facts show:
    - 7200 only with `step_sign` +1 (edge_hi, edge_late);
    - 30 only with −1 (both edge_lo cases);
    - no forward 30 s step at all.

    Backward steps span 244–786 s in the sealed set. Fix: generate a backward 7,200 s case and a forward 30 s case, or change the text to "steps of 30 s (set back) and 7,200 s (set forward), and backward steps up to 900 s".
  - (b) "30 cases in 15 named tests" is correct if the isolation test is not counted among the named tests, which is consistent with "A final test". No change is needed.
  - The rest is accurate: the isolation mechanics, the equivalence policy, and "clocks that ran slow and clocks that ran fast" (clock has 2 forward and 1 backward case; broad, brute, key, tz and rootlogin also carry backward steps).

### (4) New issues from the batch

1. **should-fix: the 30–7,200 s range is claimed for backward steps but never produced.** instruction.md lets the step be "30 to 7,200 seconds" in either direction (it doesn't state a direction). The generator caps backward steps at 900 s. That is not unfair to candidates, since a correct analyzer handles any size, but it is a coverage gap: a solution that mishandles large backward steps, e.g. one that assumes |N| < 1000 when the sign is negative, would pass. It is also the false explanation claim above. Same fix as (3a).
2. **No new blocking issue from backward steps.** `overlap_is_empty` rejects any step where a host-clock record other than a collector-kept sshd line has a true time in [tc−n, tc+n): wtmp, btmp, ctimes, dpkg, stamped history, sudo lines and hourly CRON lines are all checked. The collector noise lines at tc−1 and tc are then the only records in the overlap. So every host reading is either below tc (pre-step, raw = true + n < tc) or at or above tc + n (post-step), and the split by host time at the first agreeing line is exact. This matches guide rule 1's promise ("The collector's record always settles which side of a step every graded host-clock time lies on"). The month check (`a.month == b.month` over [tc−n, tc+3n]) stops the backward step from corrupting the month-order year walk. The reference passes every backward case (brute, broad, clock, edge_lo×2, key×2, rootlogin, tz).
3. **polish: forward 30 s is no longer exercised.** Both edge_lo cases are backward (`REQUIRED` adds a backward seed, and `backward_wanted` returns True for edge_lo). This is the small-forward-step counterpart of item 1.

**Recheck verdict:** F1–F5 are closed and F7 remains polish. There is one new should-fix: the step-size range of backward steps is claimed at 7,200 s but capped at 900 s, and forward 30 s is gone. Fix it in the generator (preferred) or in verification_explanation. Nothing blocks.
