Task 12e6eda4-8ced-4dcd-928d-7abc22b133a9 (tbrain-gnu-sed-reimplementation), quality panel v2: contesting 9 Correct Reference Solution findings with GNU sed 4.9 binary evidence (the verifier's own ground truth, Debian bookworm sed 4.9).

On each finding's own repro the binary gives the reference's output:

- 5, 9 (`a**`): `sed 's/a**/X/'` → "Invalid preceding regular expression", exit 1. glibc rejects it although the manual lists `**`. rev2 instruction now lists this among the places where GNU sed departs from its manual and nothing is checked.
- 7 (`l 2` on a tab): the binary prints `\` + newline + `\t$`, the same as the reference. rev2 instruction states the wrap rule as the binary applies it: before adding each character's escaped form, end the line with `\` if the addition would put more than N-1 characters on it.
- 8 (`/[\/]/p` on `\` and `/`): the binary prints both lines. Inside a bracket, the backslash is literal (manual: "[\*] matches either \ or *").
- 10 (`sed N` on one line `a`): the binary prints `a`. The manual says the same (sed.txt "N command on the last line": "GNU sed prints pattern space before exiting unless ... -n").
- 12 (`2,9c X` on 1..3): the binary prints `1` only. rev2 instruction now marks "a c whose range is still open when the input ends" as not checked.
- 13 (`2s/x/y/; //p` on x, z): the binary exits 1 ("no previous regular expression"). The contract says scripts never fail, so this input is outside it.
- 14 (`-E '/a^b/p'` on `a^b`): the binary prints nothing. rev2 instruction now marks `^`/`$` in the middle of an ERE as not checked.
- 15 (`/[a\-c]/p` on `-`): the binary prints nothing. `\` is literal in a bracket, so `[a\-c]` is `a` plus the range `\`..`c`.

Fixed in rev2: 6 (short numeric escapes before the delimiter) and 11 (backslash as the s/y delimiter). All 25 Sound Verifier findings now have witnesses: a 263-case systematic sweep over classes, escapes in every context, delimiters, whitespace, M mode, escaped operators, anchors in groups, case conversion, l wrapping and labels. Finding 16 was answered by dropping "pure-Python" from the README. The panel's own repro for finding 1 (`a \t`) prints `t` on the binary, not a tab, so rev2 grades escape processing in multi-line a/i/c text and lists the one-line backslash form as not checked.
