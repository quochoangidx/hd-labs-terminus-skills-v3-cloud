Task 12e6eda4-8ced-4dcd-928d-7abc22b133a9 (tbrain-gnu-sed-reimplementation): contest of v5 quality-panel findings, with GNU sed 4.9 receipts

These were checked on the returned rev3 snapshot, where the panel's input was run through the verifier image's own GNU sed 4.9 (`/bin/sed`, `LC_ALL=C`) and through the reference.

1. Correct Reference Solution, Major, findings 15, 17, 19, 23 and 26 (bracket escapes). Contract passage: manual §5.5 says `\` is "not special within LIST" except for the §5.8 escapes such as `\n` and `\t`. GNU sed 4.9 and the reference produce identical output:
   - `sed -n '/[\w]/p'` on `a\nw\n\\\n` prints `w\n\\\n`, so `a` does not match.
   - `sed -n '/[\s]/p'` on ` \ns\n` prints `s\n`.
   - `sed -n '/[\]]/p'` on `]\n\\]\n` prints `\\]\n`, i.e. the class `[\]` followed by `]`.
   - `sed -n '/[\/]/p'` on `\\\n/\n` prints both lines.
   - `sed 's/[\t]/X/'` on a tab prints `X`, which is what the reference does too.

   The resubmission clarifies this in one clause of the instruction. The reference is unchanged.

2. Correct Reference Solution, Major, finding 25. `sed 'b x; /a/p; :x; s//X/'` on `b\n` exits 1 in GNU sed 4.9 ("no previous regular expression"), and the reference does the same. The instruction says "Scripts never fail and always finish", so this input is outside the graded domain.

3. Sound Verifier, Major, findings 31, 36 and 40. The returned roster already graded each of these:
   - 31: `branching_and_t_flag` has `s/e/E/;N;tx;s/$/ nx/;b;:x;s/$/ x/` over eight lines. An engine that also matches `$` before the embedded newline inserts the text after the first line and fails.
   - 36: `step_and_regex_addresses` has `/^.\{5\}$/p`, a BRE exact interval.
   - 40: `hold_space` has `1{h;d};G;s/\n/ /;h;$!d` and `$!{h;d};x;G`, and `branching_and_t_flag` has `1{N;s/a/A/;D};t ok;...`. All three put `;` right after `}`.

   The resubmission adds more cases for each regardless (the new matrix families).

The other 34 findings of the same panel draw are backed with fixes or new coverage, including two real reference defects (lazy input-file opening for q/Q exit codes, and `1,2q` now rejected). The per-finding receipts are in the revision ledger.
