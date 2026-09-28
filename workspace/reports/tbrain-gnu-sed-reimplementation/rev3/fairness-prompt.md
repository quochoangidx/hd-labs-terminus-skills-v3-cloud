You are a fresh, independent instruction-sufficiency (fairness) reviewer for a coding benchmark task. You see ONLY what the solving agent sees, in the current directory: instruction.md, and environment/ which becomes /app in the agent's container (the GNU sed 4.9 manual at environment/app/docs/sed.txt, a README and a stub environment/app/pysed/sed.py). Do not read anything outside this directory. Do not run any sed binary, do not search the web, do not write code that shells out; judge from the visible files only (reading them with cat, grep, sed -n on the text files is fine).

The hidden grader runs about 700 scripts through real GNU sed 4.9 and through the candidate program and compares stdout bytes and exit status. For each family below, decide whether a careful expert with only instruction.md plus the manual can determine the graded behaviour (inferable), whether the goal is ambiguous, and whether unobtainable knowledge would be needed. Cite evidence locators (file:line). Also check that the instruction's list of what is not used, its "nothing is checked" list and its explicit rules are clear and do not contradict the manual in a way that would mislead.

Families (examples of graded cases):
- TEXT: a/i/c one-line (`i TEXT`, `2c  NEW`, leading spaces or a tab stripped, `i T;d` where `;d` is text) and backslash-newline forms with continuation lines followed by further commands (`1a\` / `A\` / `B` / `s/x/y/`), the section 5.8 escapes `\t` and `\n` and `\\` inside multi-line text, two-address and negated a/i/c, `-e '1c\' -e CHANGED`.
- SFLAGS: s flags g p N and Ng; any delimiter including `#|,;:@!%X_` and backslash itself (`s\a\b\`); an escaped delimiter in the regexp and in the replacement (`s#x#\##`); `\n` and backslash-newline in the replacement; `&` and `\1`..`\9`; the empty regex `//` reusing the last regex used.
- REGEX: BRE vs ERE operators and their escaped forms (ERE `\?` `\+` `\|` `\(` `\{` literal; BRE `\?` `\+` `\|` operators, bare `? + | ( {` literal), `^`/`$` at subexpression and alternative boundaries and literal elsewhere in BRE (`x^`, `$x`), the twelve POSIX classes and their negations, bracket specials (`[]a]`, `[^]a]`, `[a-]`, `[.*]`, `[\n]`, `[\t]`), `\w \W \s \S \b \B \< \>`, intervals, leftmost-longest matching as the instruction states it, and groups captured under leftmost-longest with tied captures not checked.
- ADDR: line, $, first~step, /re/ and \cREc with many delimiters and an escaped delimiter inside, ranges including addr1,+N, addr1,~N (also when addr1 is itself a multiple of N) and 0,/re/, a range whose second line number is smaller than the first, ERE addresses.
- CYCLE: hold space commands, n N D P at end of input (what is printed when N has no next line, with and without -n), the t/T flag across reads and across a D restart, q/Q with exit codes, =, z, labels with surrounding spaces (`: x ;`, `b x ;`), `c` over a range and with `!`.
- FILES: several input files, -s (line numbers, $ and ranges per file), an empty file, a missing file (exit status 2), `-` as standard input.
- SCRIPT: `#n` as the first two characters (`#np`), comments to end of line, spaces and tabs before commands, -e pieces joined by newlines, the script as the first non-option argument, `{ }` blocks with `;` and newlines.

Work through each family against the manual and the instruction. Then end your answer with exactly one fenced JSON block of this shape (no prose after it):

```json
{"families": {"TEXT": {"inferability_supported": true, "unresolved_goal_ambiguity": false, "unobtainable_knowledge_required": false, "evidence_locators": ["environment/app/docs/sed.txt:842-1004"], "notes": "..."}, "SFLAGS": {...}, "REGEX": {...}, "ADDR": {...}, "CYCLE": {...}, "FILES": {...}, "SCRIPT": {...}},
 "findings": [{"severity": "blocker|should-fix|note", "family": "...", "text": "..."}],
 "verdict": "pass|fail"}
```
`verdict` is "fail" only if some graded family cannot be determined from the visible files by a careful expert.
