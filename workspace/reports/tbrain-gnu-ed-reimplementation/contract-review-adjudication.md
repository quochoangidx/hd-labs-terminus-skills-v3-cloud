# tbrain-gnu-ed-reimplementation — contract_review adjudication

Reviewer: one independent task-visible session (Opus, general-purpose), packet = instruction.md + environment/ only.
Builder and orchestrator adjudicated every finding. The fairness mechanism is the same as for sed. The reference (a port of the GNU ed 1.19 source) matches the real binary on every generated case. For each point the manual leaves open, a variant of the reference implements the other plausible reading. A case is kept only if every variant gives the same stdout, zero/non-zero status and files as GNU ed. That makes 30 variants in total (reports/ed-work/make_variants.py and make_variants2.py).

| # | Finding | Disposition |
|---|---|---|
| 1 | Stream and presence of `?` under regular-file stdin | Instruction states it: "After every command that fails, ed writes `?` and a newline to standard output, and when its standard input is a regular file it then stops." |
| 2 | Non-existing FILE argument | The Overview chapter (now shipped) settles the pipe case. The instruction limits missing command-line FILEs to pipe stdin. Variant `missingcontinue` found no remaining case that depends on the other reading. |
| 3 | Modified-buffer warning, "second time" | Variants `emodsticky` and `emodsame` changed no retained case. The effects of -l and -s on the warning follow the documented -l/-s text. |
| 4 | Undo edge cases | Variants `undonoop`, `undofirstok`, `undomodtrue` and `undolastmod` are all applied. Every case where they differ is dropped (192 cases for `undofirstok` alone). |
| 5 | `f FILE` prints | Variant `fsilent`; its one differing case is dropped. |
| 6 | `s` without a match inside `g` | Variant `sglobalerr`; its differing cases are dropped. |
| 7 | `m` destination equal to the last address | Variants `mdestinclusive` and `movenoopclean`; their differing cases are dropped. |
| 8 | `l` format | Variants `lnowrap`, `lhex`, `lnobackslash` and `ltaboctal`; their differing cases are dropped. |
| 9 | `x` with an empty cut buffer | Variant `xemptyok`; 87 differing cases dropped. |
| 10 | What `s` copies to the cut buffer | Variant `syanknew`; its differing case is dropped. |
| 11 | Empty matches with `g`/COUNT | Variants `noinfloop` and `countadvance`; their differing cases are dropped. |
| 12 | Group assignment on ties, BRE `\|`, `\N` beyond the group count | Variants `groupslast` and `backrefempty`. The instruction now says "In basic ones `\|` is alternation, as in GNU", which the manual's `\C` rule would otherwise contradict. |
| 13 | Byte counts without a final newline, `w` on an empty buffer, default filename after a failed `e` | Variants `nonewlinemsg`, `countnoadded`, `wemptyerr` and `edefonsuccess`; their differing cases are dropped. |
| 14 | What `-r` rejects | The retained cases only use names outside the current directory (`sub/x.txt`, `../x.txt`, `/etc/hostname`), so the manual's wording settles them. |
| 15 | `i` with no lines | GNU leaves `.` at the addressed line, as the manual says. No change. |
| 16 | Option scope | The instruction now reads "and no others", and says `-p` takes the prompt string as the next argument. |
| 17 | `z` window size | The instruction now says none of the standard streams is a terminal, so the manual's "22 if screen size can't be determined" applies. |
| 18 | `G`/`V` details | Variants `gprompt` and `ampnoop` changed no retained case. Aborting on an error inside a list follows the g text ("execution of COMMAND-LIST stops on the first error"). |
| 19 | Address 0, `2,2j`, marks | Variants `zeroasone`, `jsamemodify` and `marksclearondelete`; their differing cases are dropped. The generator never uses suffix forms outside p/n/l/pn, and never leaves out a closing delimiter or a final newline. |
| 20 | `-G` | Out of scope in the instruction. |

Result: 2015 generated cases. 13 were out of scope (-G, -v, h, H); 477 were sensitive to at least one variant. **1525 retained.** The reference scores 22/22 with reward 1, and the stub 0/22 with reward 0. The first blind skeleton solution, graded on the retained set, fails 10 of the 22 tests.

## final_review (same reviewer session)

First pass: **REJECT**. The reviewer wrote 11 more variants and 6 of them changed retained cases.
- Reversed range on one-address commands (94 cases): kept. The Line addressing chapter settles it ("If only one address is expected, then the last address is used", together with the N-tuple rule), and the reviewer accepted that reading on recheck.
- EOF while G/V waits for a command list (3 cases): the instruction now says it is an error.
- Missing command-line FILE with pipe stdin (2 cases): the instruction now says it gives an empty buffer with that default filename and does not by itself change the exit status.
- `\|` in extended regexes (57 cases): the instruction now says it matches a literal `|`.
- `f` with no default filename (1 case): dropped. 1524 cases remain.
- .DS_Store: removed; the ZIP allowlist excludes it.
- ed is left unpinned in tests/Dockerfile because the policy gate forbids apt version pins. The base image is digest-pinned bookworm, whose ed is 1.19-1.

Targeted recheck: **ACCEPT**. Findings 2–6 are resolved and finding 1 is advisory with the reading accepted. The reviewer reran its six variants on the 1524 cases. The verifier is sound (root-only ed, demoted candidate, separate directories, real file vs pipe stdin, byte/zero-status/file-snapshot comparison, 20 s process-group timeout). The reference is self-contained.

## After the counted probe

The fresh counted Opus solver missed only 3 of 1524 cases (19/22 tests). Two of its misses are settled by the manual: `c` on address 0, which the manual never lists among the commands where 0 is valid. The third was `e missing.txt` on an unmodified buffer. Afterwards GNU treats the emptied buffer as unmodified, while both blind Opus solvers treated the deletion as a change and warned at end of input. Two independent solvers took that reading, so it counts as plausible. A variant `efailmodified` was added and the one case it changes was dropped (1523 cases). The probe outcome is unchanged, because the solver still fails two tests. All snapshot-bound receipts were then rebuilt.

Final confirmation on snapshot 0bd83f1d… (1523 cases): **ACCEPT stands** (same reviewer session). The only condition is that .DS_Store stays out of the ZIP; the ZIP listing was verified clean.
