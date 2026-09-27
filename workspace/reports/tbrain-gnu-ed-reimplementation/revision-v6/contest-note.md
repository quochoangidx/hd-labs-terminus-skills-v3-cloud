Task fc57838e-86e3-431c-a65c-b8776a1f307e (tbrain-gnu-ed-reimplementation), evaluation 6: four findings contested (three Correct Reference Solution, one Sound Verifier)

The contract grades against the GNU ed 1.19 binary: "Every expected result comes from running GNU ed 1.19 itself on the same script, so where the manual and the program disagree the program is what counts" (instruction.md, last paragraph). Each script below is the finding's own, run through `/usr/bin/ed` (Debian bookworm ed 1.19) and the submitted reference in the verifier image with LC_ALL=C. Both give the same stdout, exit status and files.

Finding 3 (Major): "The bracket parser interprets a hyphen in the first position as the lower endpoint of a range."
- Script (pipe, no FILE): `a\na\n0\n.\ng/[-a]/p\nQ\n`
- GNU ed 1.19: stdout `a\n`, exit 0. Reference: stdout `a\n`, exit 0.
- `bracket()` reads the leading `-` as its own item before it checks for a range, so `0` is never selected. Two graded regex cases now cover `[-a]` and `[a-]`.

Finding 4 (Major): "A substitution with no match returns success inside a global command list, bypassing the global list's first-error stop."
- Script (`-s`, regular-file stdin): `a\na\nb\n.\ng/./s/a/A/\nQ\n`
- GNU ed 1.19: stdout empty, exit 0. Reference: stdout empty, exit 0.
- Inside a global list, GNU ed 1.19 does not treat an s that finds nothing on the current line as an error. That holds even when no selected line matches: `g/./s/zzz/y/\` then `p` prints every line and exits 0. Outside a global command the same s prints `?` and exits 1 in both. The finding correctly noticed that the manual says otherwise. That is a manual/program departure, and errata entry 18 now states it for the candidate.

Finding 6 (Major): "Unset apostrophe marks resolve to address 0 even after the buffer becomes nonempty."
- Script (pipe, no FILE): `a\nx\n.\n'a=\nQ\n`
- GNU ed 1.19: stdout `?\n`, exit 1. Reference: stdout `?\n`, exit 1.
- For an unset mark on a non-empty buffer, `get_line_node_addr` returns -1, so the command fails as errata entry 1 says. Two graded address cases pin the empty-buffer and non-empty-buffer behaviour.

Receipt: revision-v6/receipts/returned/reference-findings-3-4-5-6.json. It is bound to the returned snapshot and holds the command, both programs' output and the verdict for each row.

Finding 21 (Sound Verifier, Major): "No graded case verifies that -s suppresses the byte count produced by the uppercase E edit command."
- The returned corpus already holds the case `ed -s f.txt` with script `E other.txt\nf\n` (tests/cases/files_and_write.jsonl) on a pipe.
- We scored the implementation the finding describes (E prints its byte count under -s) against the returned verifier. It failed test_files_and_write on that case: GNU ed prints `other.txt\n`, the wrong implementation prints `9\nother.txt\n`.
- Receipt: revision-v6/receipts/returned/E-count-ignores-s.json (reward 0, bound to the returned snapshot).
