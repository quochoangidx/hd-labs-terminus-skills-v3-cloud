# tbrain-gnu-ed-reimplementation — revision v2

**Returned snapshot** `69e5a50c55efc1da5b21e81a370dc5c932678bedbe59594d59181d446cb98228`
(byte-identical to the rev1 archive this project shipped)
**Return** pre-difficulty gate again: quality panel `NEEDS REVISION`, 64 blocking findings,
down from 106. Oracle/NOP passed, so no agent run took place.

## What changed on the platform side

Three findings now carry `confirmed by running the grader`: the panel built a broken submission
and watched the suite accept it. That is mutation testing against the verifier, and those three
are indisputable.

## What the evidence showed

| Platform claim | Raw evidence | Root-cause class | Decision |
|---|---|---|---|
| 3 proven coverage gaps: three print suffixes, a file past 32 lines, an unescaped brace | each mutant accepted by the returned suite | missing behavioural coverage | backed: cases added and each mutant kept as a wrong path |
| 21 Major + 1 Minor: the reference contradicts the manual | all 22 scripts run through GNU ed 1.19: identical output, status and files | not a defect — the contract grades against the program | disputed, and every departure now documented in a shipped errata |
| 50: binary files | GNU ed appends no newline to a binary file's last line, on reading or writing | reference defect, and the rule is in the manual's Limitations section | backed: implemented in full, including the empty-file reset |
| 42, 51: option layouts | GNU ed applies an option written after FILE and refuses a bare `-p` | reference defect plus an over-narrow contract sentence | backed: parser matches ed, instruction describes GNU's argument handling |
| 25: the package audit | it rejected any file holding a NUL, which the task never forbade | my own check, too broad | backed: rejects executable formats, leaves data alone |
| 53: the import guard | site-packages lives inside the standard-library directory, so installed packages counted as standard library | my own check, a real hole | backed: installed paths rejected, with an importlib probe as witness |
| 35 further coverage findings | the returned corpus had no case for any of them | missing behavioural coverage | backed: 51 cases added |

## Why an errata file rather than another round of disputes

The same reference findings arrived twice. They are not defects: the contract names GNU ed 1.19
and the verifier takes every expected result from it. But the task shipped the manual as its only
documentation, and the manual is wrong about these corners, so a reader who checks the reference
against the manual will keep raising them, and a solver reading the manual would implement them
wrongly.

`/app/docs/ed-errata.txt` states each departure as observable behaviour, verified by execution
today. That makes the required behaviour documented rather than only discoverable, which answers
the finding for a reader and helps a solver at the same time. It is fifteen entries against a
thousand-line manual, so the task's difficulty is untouched.

## Files changed

| File | Change |
|---|---|
| `environment/app/docs/ed-errata.txt` | new: the fifteen places GNU ed 1.19 departs from its manual |
| `environment/app/README.md` | points at the errata |
| `instruction.md` | the program decides where manual and program disagree; GNU's argument handling described |
| `solution/pyed/ed.py` | binary files keep their missing final newline on read and write, with the empty-file reset; option parsing permutes, honours `--`, and refuses a bare `-p` |
| `tests/cases/*` | 1644 → 1716 cases, 51 for the coverage findings and 21 pinning the disputed behaviours |
| `tests/test_outputs.py` | package audit narrowed to executable formats and given its own test; sixth launcher probe |
| `tests/guard.py` | an origin under site-packages or dist-packages is not standard library |
| `tests/guardcheck/installed.py` | new probe: importlib reaching an installed package |
| `task.toml` | verification and difficulty prose follow the above |

## Results

| Run | Result |
|---|---|
| Differential over the whole corpus | 1719 cases, 0 differ from GNU ed 1.19 |
| Oracle | 25/25 tests, reward 1 |
| The three platform mutants | each rejected on its own witness |

## The print-suffix mutant survived the first case written for it

The platform's finding gave `1pln` as its reach. That script does not discriminate a parser
capped at two print suffixes, because `p` is the command there and only `l` and `n` are
suffixes, so the cap is never reached. Running the platform's own mutant locally caught this:
the suite accepted it. Three cases that put three suffix letters after a command — `2dpln`,
`2kxpln`, `2t1pln` — kill it, and the mutant is kept as a wrong path so it cannot come back.
The lesson is that a finding's suggested reach is a hypothesis: run the mutant, do not assume
the script the report offers actually separates it.

## Final state

| Item | Value |
|---|---|
| Repaired snapshot | `68890de1633b...` |
| Upload archive | `tbrain-gnu-ed-reimplementation-rev2.zip`, sha256 `308fb5688bea58b61cf34efef885580c1e1a68b66d46857994867224c5590325`, 46 entries, largest file 51,161 bytes |
| Returned archive | untouched, sha256 `2d1c84592e431b91e44fdbb02ca82fc041c6c760a2ec4b93fc839a9c98319b09` |
| Strict preflight with determinism | pass: both builds, oracle 1, NOP 0, oracle 1 under noexec /tmp |
| Wrong paths | 12 of 12 rejected on their own witness, including the three the platform proved |
| Panel precheck (`--full`, builder_certified) | pass, no blockers, no warnings |
| Revision ledger | 64 findings answered with snapshot-bound evidence |
| Exact-zip client review | ready |

The 22 disputed findings need `contest-note.md` posted in `#terminus-3-submissions`. They were
disputed in round one as well, were never carried to the channel, and came back verbatim.
