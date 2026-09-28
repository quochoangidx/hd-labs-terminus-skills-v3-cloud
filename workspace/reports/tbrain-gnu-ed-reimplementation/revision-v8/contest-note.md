Task fc57838e-86e3-431c-a65c-b8776a1f307e (tbrain-gnu-ed-reimplementation), evaluation 8: three findings contested

Finding 9 (Correct Reference Solution, Major): "The bracket parser treats a first-position hyphen as a range endpoint."
- This is the third round with the same claim. Here is the finding's own script, run through `/usr/bin/ed` (GNU ed 1.19) and the submitted reference in the verifier image. The file holds `0`, the options are `-s f`, stdin is a regular file, and the script is `1s/[-a]/X/p` then `Q`.
  - Both print `?\n`, exit 1 and leave `f` unchanged. No `X` is printed.
- Control: on a file holding `0`, `-` and `a`, `g/[-a]/p` prints `-` and `a` in both.
- `bracket()` consumes the leading `-` as an item before it looks for a range, so `0` is never in the set. The graded cases `[-a]` and `[a-]` stay.
- Receipt: revision-v8/receipts/returned/reference-findings-9-10.json

Finding 10 (Correct Reference Solution, Major): "1m1 is a no-op, but move_lines sets modified, so q fails."
- GNU ed 1.19 does the same. The file `f` holds `x`, the command is `ed f`, stdin is a pipe, and the script is `1m1` then `q`.
  - GNU ed prints `2\n?\n`, exits 1 and leaves `f` unchanged. The reference prints the same bytes with the same status.
- `1,2m2` on a two-line file behaves the same way in both. Every expected result comes from running GNU ed 1.19 itself, so the reference's behaviour here is the required one.
- Receipt: revision-v8/receipts/returned/reference-findings-9-10.json

Finding 15 (Sound Verifier, Minor): "A fixed roster and seeded generator permit a verifier-specific lookup submission."
- The agent image contains only `/app/pyed/ed.py` (a stub), `/app/README.md` and the two manuals. The cases, the roster, the generator and its seed exist only in the verifier image.
- Filling such a table means reading hidden tests, and every finite hidden suite admits that.
- Drawing the seed at grading time would make an imperfect submission's reward change from run to run, which the deterministic-execution axis rejects.
- Receipt: revision-v8/receipts/returned/lookup-table-inputs.json
