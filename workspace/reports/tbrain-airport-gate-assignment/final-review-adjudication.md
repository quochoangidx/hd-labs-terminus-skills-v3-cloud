# final_review adjudication (reviewer: fresh local Claude Opus subagent, full visibility; stb unavailable: account not authorized for AI credentials, 2026-09-26)
Verdict: accept with fixes.
1. Resolved earlier findings - no action.
2. Should-fix, verification_explanation described split day files: builder accept; orchestrator uphold. Fixed: text now says one gzip copy per day checked against a roster SHA-256 and counts.
3. Advisory, "real" vs "synthetic": accept; now "realistic apron layout".
4. Advisory, BOM not stated: accept; rules now say "no byte-order mark". Cross-task: the roster review found a >4300-digit integer crashed the loader with an uncaught ValueError; fixed here too (ValueError caught, rules state the 4300-digit limit; 4300 accepted, 5000 refused).
5-10. OK, no action.

## Recheck (same reviewer; airport and roster both "accept with fixes")
The new 4300-digit sentence covered every number, but Python's limit reaches only integers: long fractions and exponents passed. Builder accept; orchestrator uphold. Fixed by making the checker enforce the sentence exactly, not by narrowing it: both loader copies (byte-identical) pass parse_int/parse_float hooks that count every digit of a number (sign, point and exponent marker not counted) and refuse more than 4300 with a stated message; sys.set_int_max_str_digits(4300) is pinned so the tool does not depend on PYTHONINTMAXSTRDIGITS. The rules now put the limit beside the byte limit, as its own rule rather than a consequence of standard JSON (roster advisory 2). Checked: 4300 digits pass as integer, fraction and exponent; 4301 refused in each form.
The ad-layout pair already launched on the prior snapshot was stopped after about 10 minutes and discarded; a fresh pair runs on this snapshot.
- Editorial: file-format paragraph rewrapped at 79 columns (words unchanged, asserted); rechecks 2 both accept.
- Recheck 3: accept. Correction: the source task also held tests/__pycache__, written when gen_wrong.py imported the checker. Deleted; snapshot hashers and the ZIP builder skip caches, so no receipt changed. gen_wrong/best now run with PYTHONDONTWRITEBYTECODE=1. Missing final newline in the rules file after the rewrap: cosmetic, kept to avoid invalidating the running probe / cleared panel.
