# Residual risk — tbrain-gnu-ed-reimplementation (revision v1, 2026-09-24)

- **Solvability, not difficulty, is the live risk.** The local blind probe was 0/2 before this
  revision and the corpus is now 1719 cases across 25 platform-visible tests, split so the panel can read every file whole. The platform
  calls a task solvable when every test passes in at least one of its eight runs; several
  families are hard enough that this is the plausible failure mode of the next round.
- **Two divergences stay unfixed and ungraded.** A basic `^\?` or `^\+` matches nothing in GNU
  ed 1.19 and everything in the reference. A leading `\{2\}` is literal per the manual and
  rejected by the binary, so grading it either way would contradict one of the two authorities
  the contract names; it is recorded in the manifest as a documented exception. No case in the
  corpus touches either form.
- **Vendored pure-Python source cannot be distinguished from the candidate's own.** The launcher
  stops imports from outside the delivered package and the standard library, the delivered tree
  is read for binaries and foreign imports, and the agent container has no network, so a package
  cannot be fetched during a run; source typed into the package is out of reach of any check.
- **The disputed findings need a human to post them.** 20 of the 106 findings are answered with a
  counterexample rather than a repair. The quality panel does not read revision notes, so
  `revision-v1/contest-note.md` has to be posted in `#terminus-3-submissions`.
- **Sibling tasks share the enforcement gap.** `tbrain-gnu-dc-reimplementation` still names a
  behavioural test as the enforcer of the same standard-library restriction and fails the new
  `panel_precheck.py` rule; it was not touched by this revision.

- **The errata changes what a solver knows (revision v2, 2026-09-25).** `/app/docs/ed-errata.txt`
  documents fifteen places where GNU ed 1.19 departs from its manual. That is deliberate: those
  corners were graded before and could only be guessed. It makes the task fairer and slightly
  easier, and the local probe result from before it exists should not be carried across the
  change.
- **The platform mutates the verifier now.** Three v2 findings were proven by the panel running a
  broken submission through the suite. Any future change to the corpus should be checked the same
  way, against the twelve wrong paths kept in the manifest.

- **The errata is now load-bearing (revision v3, 2026-09-25).** Twenty-one entries describe where
  the program departs from its manual, and the panel reads them as contract. Each is pinned by a
  graded case and checked by `revision-v3/evidence/errata-map.json`, but any future edit to that
  file has to be re-derived from the program, not from memory.
- **stb could not validate this task locally.** The Harbor Docker provider rejects the declared
  no-network phases and the check agent is region-blocked, so the evidence here is the Docker
  preflight. Platform execution remains the only authority for the phases stb refused to run.

- **Each revision's fix has been the next revision's finding (v4, 2026-09-25).** The NUL fixtures
  added in v2 broke the ASCII-only domain in v3; the `-v` case added in v3 to pin an errata
  sentence broke the option domain in v4. Before adding a case, check it against the domain the
  instruction states, not only against what the program does.
- **The binary-file paths are now wide.** Beyond the manual's Limitations rule, the reference
  implements ed's `Newline inserted` path and keeps a binary buffer's missing final newline
  across a later read. Four cases pin those states and a wrong path guards the flag reset.

- **The corpus shrank from 1,983 to 955 cases (revision v5, 2026-09-25).** The panel had left four
  case files unread in two consecutive rounds because the packet as a whole was about 300 KB, so
  the four generated buckets of 268–285 scripts were replaced by two of 40, chosen by which
  wrong-path mutants each script kills; every focused family and every errata entry keeps its
  cases, and 109 KB of case files now sit under the panel's total budget. Nothing about the
  grading changed (each result still comes from GNU ed 1.19 at run time), but the local probe
  signal from earlier snapshots does not carry across a corpus change, and no fresh probe was run
  in this revision.
- **A script GNU ed itself cannot finish within the case timeout is graded as a timeout.** glibc
  expands `y\{0,32767\}` into a program it takes minutes to run, and the verifier records GNU's
  result as `timeout`, which no candidate can match; no case in the corpus is near that, and a
  count above 32767 is refused by both (errata entry 11). A reviewer building such a script by
  hand would be probing the C library rather than the task.
- **`s/y\{0,50000\}z//` and its kind are inside the domain and now run in well under a second in
  the reference**, but a candidate with a naive backtracking matcher will time out on them, which
  is a legitimate difference from GNU ed rather than a verifier defect: the instruction says byte
  for byte and the same exit status, and a hundred-thousand-byte line is a stated bound.
- **The one disputed finding (7) needs a human to post `revision-v5/contest-note.md`** in
  `#terminus-3-submissions`; the panel does not read revision notes.
