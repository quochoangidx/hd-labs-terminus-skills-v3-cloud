# contract_review adjudication — tbrain-gnu-sed-reimplementation

Reviewer: one fresh Claude Opus subagent (general-purpose, model=opus); packet = instruction.md + environment/ only.
The reviewer ran a real GNU sed 4.9 container to confirm each claim. Builder and orchestrator are the same session.

| # | Finding | Severity | Builder | Orchestrator | Action |
|---|---|---|---|---|---|
| 1 | manual §5.3 describes `\|` as first-alternative-wins, contradicting "selects the longest" and real 4.9 | blocking | accept | uphold | instruction now states POSIX leftmost-longest across alternatives; suite filtered so no case depends on which group a tied longest match reports (posix_groups variant: 0 differences) |
| 2 | `-s` keeps undocumented per-file state (hold reset, 0,/re/ restart, n/N at file boundary) | blocking unless excluded | accept | uphold | suite drops every -s case using n/N/D/h/H/g/G/x/c or 0,/re/ |
| 3 | manual was the 4.10 edition | should-fix | accept | uphold | docs/sed.txt replaced by the 4.9 manual (sed-4.9 tarball doc/sed.info, as text) |
| 4 | T resets the flag when not branching; ERE mid-pattern anchors; \s vs \r\v\f; label edges | should-fix | accept | uphold | T_keeps_flag variant shows 0 affected cases; inputs restricted to ASCII without \r\v\f; label-edge scripts excluded; no mid-pattern ERE anchors in the suite |
| 5 | "files that cannot be read" ambiguous | should-fix | accept | uphold | instruction: "a file named on the command line may not exist"; no missing file combined with q/Q |
| 6 | option syntax not pinned | should-fix | accept | uphold | instruction: -n, -E, -s each as its own argument before the script; -e repeatable joined by newlines |
| 7 | input domain under-specified | should-fix | accept | uphold | instruction: a few dozen ASCII lines, newline-terminated, files may be empty; control characters only in l checks (documented octal escapes) |
| 8 | runtime errors / non-termination not excluded | advisory | accept | uphold | "Scripts never fail and always finish" |
| 9 | no limits; POSIXLY_CORRECT | advisory | accept | uphold | "finish each run within a few seconds"; "Nothing sets POSIXLY_CORRECT"; verifier env explicit |
| 10 | l wrapping undocumented | advisory | accept | uphold | l_nowrap variant: 26 cases whose output depends on wrapping removed |
Do-not-test list: each item mapped to a filter — empty match after a match (variant), case-escape combinations (regex), \x26/\x5c (regex), a/i/c text escapes and leading spaces (regex/parse), c on unclosed or negated ranges (variants), Q/q with pending appends (variants), -s state (structural).
Suite after filtering: 944 cases. Both reviewer-safe traps remain: addr1,~N when addr1 is a multiple of N, and a script whose first two characters are #n.

## final_review (same reviewer session) — snapshot a8eae5e7a795af3656d04691cc20403a63829a60e7c8ce4e55886edbf81e545d

Verdict: **ACCEPT** (restated 2026-09-24 after targeted recheck; reviewer confirmed oracle 24/24 reward 1, stub 0/24 reward 0).

Findings 1–9 and 11 resolved (a/i/c backslash texts dropped; \l/\u mixed with \L/\U removed; [[:upper:]] with I dropped; tied-alternation group cases verified tie-free; script-as-argument and empty-input cases added; verifier timeout 3600 s against ~42 s runtime; packaging junk removed; process-group kill on timeout; reference D-restart/append and missing-file-with-q fixed). Finding 10 ("about a thousand cases" in task.toml) is stale: task.toml says 866.

Residual risk carried to submission notes: the manual's own sentence on `\|` (first alternative) is overridden by the instruction's leftmost-longest rule, which must stay; `addr1,~N` rests on the literal manual reading; behaviour the manual leaves open (per-file hold and 0,/re/ under -s, T flag reset, c on unclosed ranges) is excluded by case filtering, so regeneration must rerun the variant filter; missing-file coverage is a single case.
