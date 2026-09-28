# tbrain-gnu-grep-reimplementation — review adjudication

Reviewer: one independent session, GPT-5.6 through `codex exec` on the stb Portkey key (user instruction: no local Claude runs). `contract_review` saw only `instruction.md` and `environment/`. `final_review` saw the whole task and was rechecked twice.

Fairness mechanism: the reference (`solution/pygrep`) matches GNU grep 3.8 on all 2029 generated cases. Each point the manual leaves open got a variant copy of the reference implementing the other reading: `twidth0`, `twidthsize`, `binaryafter`, `nozapcount`, `sep0`, `onoseps`, `wempty`, `wordexisto` and `bsdash`. A case was kept only if every variant agrees with GNU; 30 cases were dropped, leaving 1999. Rules that come up constantly are stated in the instruction instead, and each stated sentence was checked against the real binary.

## contract_review

| # | Finding | Disposition |
|---|---|---|
| 1 | `-P` scope | Stated out of scope |
| 2 | Conflicting matchers and output modes | Stated: two different ones of -G/-E/-F are an error (exit 2); -q > -l/-L > -c > line output; -H/-h and -l/-L take the last one |
| 3 | -w/-x/-o with several patterns | No change (the manual settles it) |
| 4 | Multiple output modes | Covered by the precedence list |
| 5 | Empty patterns at the edges of -e | Stated (empty fields kept; a pattern file's final newline adds nothing) |
| 6 | -m per file; separators across files | Stated |
| 7 | Context merging, -A0 | No change |
| 8 | Continuation after a missing file | Stated (skipped; status 2 unless -q already selected a line) |
| 9 | Filename defaults, --label, -Z, -z | No change; the -H/-h conflict is covered by 2 |
| 10 | Binary-file combinations | Stated as a decision rule (NUL anywhere, -I selects nothing, NUL ends a line, nothing printed, stops at the first selected line except under -c) |
| 11 | Final line without a newline | No change |
| 12 | `\-` and other undefined escapes | Stated that patterns never use one; the retained cases use only \( \) \{ \} \1 \b \< \> |
| 13 | Undocumented exclusions | Addressed by 1–12 |

## final_review

1. **REJECT.** Repeated `-m` and the context-option precedence were unstated. Stated after checking against GNU: the last value wins; `-C`/`-NUM` set both sides; `-A`/`-B` take precedence over them in any order. The same sentence covers --label, the group-separator options and -a/-I/--binary-files. The verification explanation in task.toml was reworded.
2. **REJECT.** The new "last value wins" sentence contradicted the accumulation of `-e`/`-f`. Reworded to "Apart from `-e` and `-f`, which add patterns each time, ...".
3. **ACCEPT.** No other blocking issue. The reviewer sampled 113 cases, then 48 more, across every family.

A whitespace-only paragraph split in instruction.md followed. It changes no content, so the verdict stands; every receipt was rebuilt on the resulting snapshot `bfb0e461…`.
