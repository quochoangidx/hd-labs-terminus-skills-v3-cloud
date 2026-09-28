# tbrain-gnu-bc-reimplementation — review adjudication

Reviewer: one independent session, GPT-5.6 through `codex exec` on the stb Portkey key (user instruction: no local Claude runs). The `contract_review` saw only `instruction.md` and `environment/`; the `final_review` saw the whole task.

Fairness mechanism: the reference (`solution/pybc/bc.py`, a port of GNU bc's scanner, grammar actions, byte-code interpreter and number library) matches GNU bc 1.07.1 on all 2600 generated programs. Four variants implement readings of points where the manual contradicts the binary or says nothing (`reports/bc-work/make_variants.py`):
- `stmtprint`: the manual's literal assignment-statement rule;
- `boolclean`: clean 0/1 results from `&&` and `||`;
- `limits`: the manual's base limits;
- `raisenegzero`: a zero result of `^` carries no sign.

A program was kept only if every variant prints what GNU prints; 1905 programs remain. The following rules are stated in the instruction instead, each checked on the binary:
- the product and square-root scale;
- truncation;
- printing below one and of zero;
- output bases above 16 and non-decimal fraction digits;
- the shared 69th-character line split;
- when constants are converted, and the single-digit rule;
- `length`;
- evaluation order and short-circuiting;
- silent `for`/`if`/`while` headers, `continue`, `else` binding;
- `*name[]` aliasing;
- runtime errors and what survives them.

## contract_review

| # | Finding | Disposition |
|---|---|---|
| 1 | Scope wording ("whole language") | Reworded to "the bc language that the manual describes", with the unused parts listed |
| 2 | Operator scales | No change |
| 3 | `length()` of zero and insignificant digits | Stated with four examples; the `lengthzero` filter dropped |
| 4 | Output, `last`, line splitting | No change |
| 5 | `F.8` classification | Stated (the single-digit rule applies to the part before the point); the `firstdigitclamp` filter dropped |
| 6 | Unknown `print` escapes | Stated that none are used |
| 7 | Evaluation order, short-circuiting, index before RHS | Stated after checking on the binary |
| 8 | `for` header printing, `continue`, dangling `else` | Stated |
| 9 | Fractional array indexes | Stated (truncated) |
| 10 | `*name[]` aliasing, argument order, void return | Stated; void functions return no value |
| 11 | What survives a runtime error | Stated |
| 12 | Filtering the contract does not name | Paragraph added naming the two filtered areas (assignment-statement printing, negative zero from `^`) |

## final_review

**ACCEPT.** The reviewer sampled 44 cases across all 18 families. One should-fix: the verification explanation in task.toml still said 1782 cases and listed now-stated rules as filtered. Fixed before the receipts and the counted pair.
