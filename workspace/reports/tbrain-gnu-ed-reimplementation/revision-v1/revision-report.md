# tbrain-gnu-ed-reimplementation — revision v1

**Returned snapshot** `0bd83f1dd850bc96541c32e47836703e7fe287578fbdfda5990952d3c9ee63f2`
**Report** `workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v1/fc57838e-86e3-431c-a65c-b8776a1f307e.md`
**Return** pre-difficulty gate: quality panel `NEEDS REVISION`, 106 blocking findings
(19 Major + 2 Minor on Correct Reference Solution, 55 Major + 30 Minor on Sound Verifier).
Oracle/NOP had already passed, so no agent run took place.

## What the evidence showed

| Platform claim | Raw evidence | Root-cause class | Decision |
|---|---|---|---|
| 19 Major: the reference deviates from the manual | each finding's own script run through GNU ed 1.19 and through the submitted reference: identical stdout, status and files in 21 of 22 | not a defect — the contract makes the binary the authority | disputed, and every script added as a graded case |
| 1 Major (14): `[[.ab.]]` accepted | GNU ed rejects a multi-character collating element under `LC_ALL=C`; the reference matched `[ab]` | oracle/reference defect | backed: bracket, interval and range-endpoint rules repaired |
| 4 Major (20, 23, 64, 65): the construction rules are not enforced | a candidate whose `ed.py` only `execv`s a staged GNU ed binary scored **reward 1** on the returned verifier | verifier defect, exploit proven by execution | backed: every run now goes through a launcher, plus a static read of the delivered package |
| 2 (40, 75): interrupts are not handled and never tested | the verifier delivers no signal; a timed signal would make grading depend on arrival time | promise not core | dropped: signals are now an explicit exception in the instruction |
| 2 Minor (76, 104): invocation forms not rejected | GNU ed itself accepts `-Es`, `-pfoo`, `-G`, and an option after FILE | not a defect; those forms are outside the stated grammar | disputed |
| 78 coverage findings | the returned corpus contains no case for any of them | missing behavioural coverage | backed: 121 cases added, expectations taken from GNU ed 1.19 at run time |

## Why these repairs and not the alternatives

Repairing the reference to match the panel's reading of the manual was the obvious move and
the wrong one: it would have made the program disagree with the authority the contract names
and the verifier runs, turning 19 correct behaviours into bugs. Execution settled each claim
before anything was edited.

Dropping coverage instead of adding it was available for the 78 coverage findings and was
rejected: the behaviours are documented in the manual shipped with the task, and the task's
whole difficulty is breadth of exact behaviour. Only the interrupt promise was cut, because
nothing graded it and grading it would have introduced timing into the result.

The construction rules could also have been dropped. They are load-bearing here — without
them the task is solved by shipping the real `ed` — so they were made true instead.

## Files changed

| File | Change |
|---|---|
| `solution/pyed/posixre.py` | collating elements and equivalence classes must be one character in the C locale; a range endpoint must be a character or a collating element; an interval needs something repeatable before it, valid bounds, and may not follow another repetition in a basic expression; the unreachable POSIX tie-break helper removed |
| `tests/cases.json` | 1523 → 1644 cases; 121 added, one replaced (see below) |
| `tests/guard.py` | new: runs the delivered entry point in-process under an audit hook and an import warden |
| `tests/guardcheck/*`, `tests/guardvendor/*` | new: four probe programs that show the launcher stops delegation, an exec, and a foreign import, and leaves an ordinary program alone |
| `tests/test_outputs.py` | candidate launched through the guard; `PYTHONDONTWRITEBYTECODE`; two new tests for the construction rules |
| `tests/Dockerfile` | stages the launcher and its probes under `/opt/pyedguard`, world-readable |
| `instruction.md` | signals added to the exceptions; the program settles what the manual leaves open; the construction rules are checked while it runs |
| `task.toml` | verification explanation describes the launcher, the package check and how cases are chosen |

## Results

| Run | Result |
|---|---|
| Oracle (reference, 1644 cases) | 24/24 tests, reward 1, 107 s |
| NOP (environment stub) | 22 failed, 2 passed, reward 0 |
| Launcher candidate on the returned verifier | reward 1 — the exploit |
| Launcher candidate on this verifier | reward 0, 23 of 24 tests fail |
| Differential check of the whole corpus against GNU ed 1.19 | 1644 cases, 0 differ |

## Known exposure

- The task's local probe was 0/2 before this revision and the corpus is now broader, so the
  platform's solvability rule (every test passes in at least one run) is the live risk, not
  the difficulty floor.
- Two undocumented divergences remain unfixed and ungraded: a basic `^\?` or `^\+` matches
  nothing in GNU ed and everything in the reference, and a leading `\{2\}` is literal in the
  manual but rejected by the binary. No case touches either.
- A vendored pure-Python dependency copied into the delivered package cannot be told apart
  from the candidate's own source; the launcher stops imports from outside the package, and
  the agent container has no network, so a package cannot be obtained during the run.

## Final state

| Item | Value |
|---|---|
| Repaired snapshot | `69e5a50c55ef...` (`revision_ledger_check.py --print-snapshot`) |
| Upload archive | `tbrain-gnu-ed-reimplementation-rev1.zip`, sha256 `2d1c84592e431b91e44fdbb02ca82fc041c6c760a2ec4b93fc839a9c98319b09`, 44 entries, task.toml at the root |
| Returned archive | untouched, sha256 `b8bfc5108b1decbe4dcbbb243088d3d44eddb903b9c0a1e435e83cef70993308` |
| Strict preflight | pass, with `--determinism`: both builds, oracle 1, NOP 0, oracle 1 under noexec /tmp |
| Wrong paths | 9 of 9 rejected on their own witness, all bound to the repaired snapshot |
| Panel precheck (`--full`, builder_certified) | pass, no blockers, no warnings |
| Revision ledger | 106 findings answered with snapshot-bound evidence |
| Exact-zip client review | ready; the two remaining notes are campaign-only receipts this profile does not produce |

The 20 disputed findings still need `contest-note.md` posted in `#terminus-3-submissions`: the
quality panel does not read revision notes.

## Post-packaging correction (2026-09-25)

A peer session found that a GPT-5.6 solver of a sibling task called glibc `regcomp` through
`ctypes`. The launcher already stopped that path, but the instruction forbade only non-standard
-library code and starting other programs, and `ctypes` is standard library — so the task would
have failed a submission on an unwritten rule. The instruction now reads "Use only the Python
standard library, without loading native code (through `ctypes`, for example), and do not start
other programs; all three rules are checked while it runs." A fifth probe program calls
`ctypes.CDLL` and must be stopped, so the rule has its own witness. Every snapshot-bound receipt,
the manifest, the ledger and the zip were regenerated against the corrected task.

## Corpus split (2026-09-25)

The panel's own findings say it stopped reading `tests/cases.json` after line 3856 of 28429,
and a repo gate added the same day fails any task file above about 60 KB for that reason. A
truncated corpus is most of why 85 findings say "no visible case does X": the cases existed in
the part nobody saw. The corpus is now one case per line in `tests/cases/<family>.jsonl`, with
input files shared through `tests/cases/fixtures.json` and a committed `roster.json` of families
and counts that collection checks before any case runs. The largest file is 41 KB, the whole
corpus is 268 KB rather than 503 KB, and a missing family, a wrong count or an unknown fixture
now fails collection instead of silently grading a smaller suite.

## Final archive

`tbrain-gnu-ed-reimplementation-rev1.zip`, sha256
`2d1c84592e431b91e44fdbb02ca82fc041c6c760a2ec4b93fc839a9c98319b09`, 44 entries, largest file
49,784 bytes. Snapshot `69e5a50c55ef`. Wrong paths 9 of 9, panel precheck pass with no warnings,
revision ledger 106 findings answered, coverage map 98 findings still backed by their cases,
exact-zip review ready. Copied byte-identically to `workspace/submissions/`, and the returned
archive is unchanged at `b8bfc5108b1decbe4dcbbb243088d3d44eddb903b9c0a1e435e83cef70993308`.
