Task 12e6eda4-8ced-4dcd-928d-7abc22b133a9 (tbrain-gnu-sed-reimplementation), quality panel v1: contesting 14 findings with GNU sed 4.9 binary evidence.

The contract is "behaves exactly like GNU sed 4.9 with LC_ALL=C" (instruction.md). The verifier's expected output is the image's own GNU sed 4.9 (Debian bookworm). On each finding's own repro, the binary gives the reference's output:

- Correct Reference Solution 6, 10 (-s empties hold space): `sed -s -n '/A/h;/B/g;p' f1 f2` with f1=`A`, f2=`B` → `A\n\n`. GNU starts each file with an empty hold space under -s.
- 7 (n with -s range): `sed -s -n '/A/,/Z/p;n' f1 f2` with f1=`A`, f2=`B\nC` → `A\n`. This matches the reference.
- 8, 13, 25, 27 (tied groups): `sed -E 's/(a|aa)(a?)/[\1]/'` on `aa` → `[a]`, and `<\1:\2>` → `<a:a>`. The instruction also says tied-group captures are not checked.
- 15 (c on an unclosed range): `sed '1,3c X'` on `a` → empty output.
- 22 (c on a range): `sed $'2a A\n2,4c\\\nX'` (script: `2a A`, newline, `2,4c\`, newline, `X`) on 1..5 → `1\nA\nX\n5`. The text is printed when the range ends.
- 18, 19 (ERE mid-pattern anchors): `sed -E -n 's/a^b/X/p'` on `a^b` → no output, and the same for `a$b`. glibc treats these as anchors.
- 20 (leading hyphen): `sed -n '/[-a]/p'` on `.` → no output. The reference already treats `-` as a literal.
- 26 (T): `sed -n 's/a/a/;T x;T y;:x;s/^/X/;b e;:y;s/^/Y/;:e;p'` on `a` → `Ya`. A T that does not branch still resets the flag.
- Sound Verifier 64 (`**`): `sed 's/a**/X/'` → "Invalid preceding regular expression", exit 1. The binary rejects it, and the contract says scripts never fail, so no valid case exists.

The findings that held (exponential regex, I back-references, D keeping the t flag, y escapes, -s n/N at a file's end, address 0) are fixed in rev1. Coverage for every sound-verifier finding is now in three case files, each under 25 KB, so the whole roster is readable.
