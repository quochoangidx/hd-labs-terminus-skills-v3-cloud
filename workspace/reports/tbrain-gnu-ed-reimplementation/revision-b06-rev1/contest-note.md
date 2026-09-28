Task b06b2c0a-ebb9-483b-b44d-bb86ce5eb3e9 (tbrain-gnu-ed-reimplementation), evaluation 2: four Correct Reference Solution findings contested

The task's contract says "Every expected result comes from running GNU ed 1.19 itself on the same script, so where the manual and the program disagree the program is what counts." Each script below is the finding's own, run through `/usr/bin/ed` (GNU ed 1.19) and through the submitted reference in the verifier image. Receipt: revision-b06-rev1/receipts/returned/crs-reproduction.json.

Finding 2 (Major): "Successful substitution yanks the deleted pre-substitution line instead of copying the last modified replacement line into the cut buffer."
- Script `a`, `abc`, `.`, `s/b/X/`, `x`, `,p`, `Q` on a pipe. GNU ed 1.19 prints `aXc\nabc\n` and exits 0. The reference prints the same bytes.
- So GNU ed also puts the line as it was before the substitution into the cut buffer. The reference matches the program.
- The script cannot be graded anyway: the instruction says the commands `x` and `y` "never appear in a script", and they are the only way to read the cut buffer.

Finding 3 (Major): "A bare alternative substitution-repeat command `s` is rejected as a malformed new substitution."
- Script `a`, `aa`, `.`, `s/a/b/`, `s`, `p`, `Q` on a pipe. GNU ed and the reference both print `bb\n` with no `?`, and both exit 0.
- The bare `s` takes the repeat branch in `command_s`. The finding's trace of the code is wrong.

Finding 4 (Major): "Repeated substitution with r uses any last compiled regexp, rather than only a search regexp that occurred after the previous substitution."
- Script `a`, `a`, `.`, `s/a/aa/`, `sr`, `p`, `Q` on a pipe. GNU ed 1.19 does not fail. It prints `aaa\n` and exits 0, and the reference prints the same bytes.
- The manual says `r` uses "the RE of the last search ... (if the search happened after the substitution)". When no search came after, the last RE is the substitution's own, so the output is the same either way. Where the two readings differ, the program decides.

Finding 9 (Minor, marked unverified): "The address parser caps each numeric offset component before evaluating the complete address."
- Script `a`, `x`, `.`, `0+2147483648-2147483648=`, `Q` on a pipe. GNU ed 1.19 prints `?\n` and exits non-zero, and so does the reference.
- Control: `0+2147483647-2147483647=` prints `0\n` in both. GNU ed rejects the oversized component in the same place as the reference.

Finding 1 (backreference with a bounded repeat) was a real reference defect and is fixed. With the fix, a 3,000-pattern back-reference differential against GNU ed goes from 19 disagreements to 0. The eight Sound Verifier findings are backed with cases and wrong paths, and the import guard now accepts only Python source under /app.
