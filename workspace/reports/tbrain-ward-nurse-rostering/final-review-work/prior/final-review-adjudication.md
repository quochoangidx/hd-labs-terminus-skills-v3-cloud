# final_review adjudication (reviewer: fresh local Claude Opus subagent, full visibility; stb unavailable: account not authorized for AI credentials, 2026-09-26)
Verdict: accept with fixes.
1. Should-fix, integer longer than 4300 digits raised an uncaught ValueError (false rejection of an ignored key): builder accept; orchestrator uphold, narrowed. Fixed by stating the limit in the rules ("no number of more than 4300 digits") and catching ValueError in both loader copies (byte-identical). 4300 digits accepted, 5000 refused with the stated message. Same fix in the stand-plan and ad-layout tasks.
2. Advisory, BOM: accept; rules say "no byte-order mark".
3. Advisory, unsupported claim in task.toml: accept; removed.
4. Advisory, trailing space: accept; removed.

## Recheck (same reviewer; airport and roster both "accept with fixes")
The new 4300-digit sentence covered every number, but Python's limit reaches only integers: long fractions and exponents passed. Builder accept; orchestrator uphold. Fixed by making the checker enforce the sentence exactly, not by narrowing it: both loader copies (byte-identical) pass parse_int/parse_float hooks that count every digit of a number (sign, point and exponent marker not counted) and refuse more than 4300 with a stated message; sys.set_int_max_str_digits(4300) is pinned so the tool does not depend on PYTHONINTMAXSTRDIGITS. The rules now put the limit beside the byte limit, as its own rule rather than a consequence of standard JSON (roster advisory 2). Checked: 4300 digits pass as integer, fraction and exponent; 4301 refused in each form.
The ad-layout pair already launched on the prior snapshot was stopped after about 10 minutes and discarded; a fresh pair runs on this snapshot.
- Editorial: file-format paragraph rewrapped at 79 columns (words unchanged, asserted); rechecks 2 both accept.
