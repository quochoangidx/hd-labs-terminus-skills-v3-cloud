## Findings

1. **Advisory — Scope is coherent, with no direct contradiction.**  
   `instruction.md:1` requires byte-identical stdout; `instruction.md:11` clearly excludes options, libraries, `read`, and several environmental cases from grading. The added rules refine rather than contradict the manual.  
   **Smallest fix:** Replace “cover the whole bc language” with “cover the following verifier-visible subset” to distinguish implementation scope from test scope.

2. **Advisory — Numeric scale and truncation are mostly fully settled.**  
   The manual says unspecified binary results use “the maximum scale of the expressions involved” (`bc.txt:124`), division uses global `scale` (`bc.txt:152`), remainder gives its explicit construction (`bc.txt:157`), and power gives its scale formula (`bc.txt:165`). `instruction.md:15-16` supplies multiplication, square-root scales, and truncation toward zero; `instruction.md:21` supplies constant scale. Thus `+ - * / % ^ sqrt`, unary minus, and constants are determined.  
   **Smallest fix:** None.

3. **Should-fix — `length()` remains underdetermined for zero and insignificant digits.**  
   The manual only says “number of significant digits” (`bc.txt:255`) while its earlier description calls length “the total number of decimal digits used” (`bc.txt:54`). Neither determines `length(0.00)`, `length(.0010)`, or treatment of leading/trailing zeroes. The task says disputed cases were dropped, but exact drop-in behavior remains unspecified.  
   **Smallest fix:** Give an explicit formula and examples for `length(0)`, `length(0.00)`, `.0010`, and `100.00`.

4. **Advisory — Number output, `last`, and line splitting are unusually well specified.**  
   Expression output and assignment suppression are specified at `bc.txt:293-300`; output bases at `bc.txt:301-312`; `last` at `bc.txt:313-322`; and `.` is made mandatory by `instruction.md:5`. `instruction.md:17-20` settles leading zeroes, zero, bases 11–16, bases above 16, nondecimal fraction length, and the exact 68-character wrapping boundary for numbers and strings.  
   **Smallest fix:** None.

5. **Should-fix — One input-constant classification remains ambiguous.**  
   The manual says a “single digit” ignores `ibase`, while “multi-digit numbers” clamp digits (`bc.txt:100-107`). It never says whether `F.8` has a single-digit integer part or is a multi-digit numeral. `instruction.md:21` settles timing, scale, and fraction truncation, but not this classification.  
   **Smallest fix:** State explicitly whether the decimal point and fractional digits make the entire constant multi-digit.

6. **Should-fix — Unknown `print` escapes are linguistically ambiguous.**  
   Plain strings are literal (`bc.txt:324-327`), while `print` recognizes listed escapes (`bc.txt:329-340`). “Any other character following the backslash will be ignored” (`bc.txt:340-341`) could mean discard the following character, discard the backslash, or ignore escape processing.  
   **Smallest fix:** Add one example such as `print "a\\zb"` with exact stdout.

7. **Blocking — Evaluation order and Boolean short-circuiting are unstated.**  
   Precedence and associativity are fully listed (`bc.txt:226-236`), and Boolean results are normalized to 0 or 1 (`bc.txt:214-224`). But neither precedence nor operator descriptions determine:
   - whether `&&` and `||` short-circuit;
   - left-versus-right operand evaluation;
   - function-argument evaluation order;
   - whether an array subscript is evaluated before the RHS of `op=`.

   These are stdout-visible with assignments and `++`, and are natural outputs of the described random program generator. The blanket assurance in `instruction.md:27` is not enough for an implementer to identify which generated programs were filtered.  
   **Smallest fix:** Add the verified GNU rules for operand order, argument order, `&&`/`||`, and indexed compound assignment—or explicitly exclude side effects in those contexts.

8. **Should-fix — Control flow is defined, but output in `for` clauses is not.**  
   `if`/`else`, `while`, `for`, `break`, `continue`, and `halt` are described at `bc.txt:347-389`; `quit` is read-time termination at `bc.txt:406-408`. However, the manual’s equivalent expansion of `for` (`bc.txt:371-377`) makes its first and third expressions look like expression statements, while it never says whether their values print. It also does not explicitly say whether `continue` performs expression 3 or how a dangling `else` binds.  
   **Smallest fix:** State that control/header expressions do or do not print, describe `continue`’s path through expression 3, and bind `else` to the nearest unmatched `if`.

9. **Should-fix — Array indexing and compound array assignment need two details.**  
   `var <op>= expr` evaluates the variable only once (`bc.txt:184-187`), and `instruction.md:23` lists certain invalid indexes. But positive fractional indexes such as `1.5` are not assigned a conversion rule, and “evaluated only once” does not determine subscript-versus-RHS order.  
   **Smallest fix:** Specify index integer conversion and the complete evaluation sequence for indexed `op=`.

10. **Should-fix — Most function semantics are settled, but three edges remain.**  
    The manual settles scalar/array value parameters (`bc.txt:425-435`), dynamic scoping and recursion (`bc.txt:437-451`), return forms (`bc.txt:453-461`), call-time `ibase` for constants (`bc.txt:463-467`), redefinition (`bc.txt:413-420`), void call output (`bc.txt:479-495`), and `*name[]` syntax (`bc.txt:497-500`). It does not operationally state that call-by-variable aliases the caller’s array, does not give argument evaluation order, and does not define which `return` forms are legal inside a void function.  
    **Smallest fix:** Add explicit aliasing, argument-order, and void-return sentences.

11. **Advisory — Runtime termination is defined, but persistence should be explicit.**  
    The manual says runtime errors terminate “the current execution block” (`bc.txt:695-711`), and `instruction.md:23` identifies the relevant errors. `instruction.md:22` settles uninitialized variables and array elements. Immediate execution strongly suggests that prior stdout and assignments survive, and later blocks continue, but it never explicitly rejects transactional rollback.  
    **Smallest fix:** State: “Output and side effects completed before the error remain; execution resumes with the next execution block.”

12. **Blocking — Fairness depends on undocumented filtering.**  
    The supplied arithmetic, conversion, formatting, and wrapping rules remove most GNU-specific arbitrariness. Remaining arbitrary points are evaluation order, short-circuiting, unknown escapes, `for`-clause output, fractional indexes, and function alias/return edges. If every such case was genuinely removed, the verifier can be fair; the contract alone does not let a solver recognize that subset.  
    **Smallest fix:** Add these semantics or list them explicitly among forbidden verifier patterns.

## Witnesses

1. **Arithmetic scales and truncation — uniquely determined**
```bc
scale=3
1.20+3.456
1.20*3.456
1/8
5.5%2
```
```text
4.656
4.147
.125
0
```

2. **Power and square-root scales — uniquely determined**
```bc
scale=4
scale(1.20^3)
1.20^3
scale(2^-1)
2^-1
scale(sqrt(2))
sqrt(2)
scale(sqrt(1))
```
```text
4
1.7280
4
.5000
4
1.4142
0
```

3. **Constant scale, base conversion, and single digits — uniquely determined**
```bc
scale(001.230)
ibase=16
scale(A.F)
A.F
ibase=2
F
```
```text
3
1
10.9
15
```

4. **Output bases and fractions — uniquely determined**
```bc
obase=16
255
obase=20
399
.5
-.25
0.000
```
```text
FF
 19 19
.10
-.05 00
0
```

5. **Exact line split shared by string items — uniquely determined**
```bc
print "12345678901234567890123456789012345678901234567890123456789012345678X\n"
```
```text
12345678901234567890123456789012345678901234567890123456789012345678\
X
```

6. **First digit of `F.8` in base 2 — not uniquely determined**
```bc
ibase=2
F.8
```
Whole-numeral clamping gives:
```text
1.5
```
Treating `F` as a single digit gives:
```text
15.5
```

7. **Plain strings versus unknown `print` escapes — partly unsettled**
```bc
"A\nB"
print "C\nD","\z","E"
```
If `z` is discarded:
```text
A\nBC
DE
```
If only the unrecognized backslash is discarded:
```text
A\nBC
DzE
```
No final newline in either output.

8. **Assignment printing and precedence — uniquely determined**
```bc
a=0
a=3<5
a
-2^2
scale=2
2^-2
!2==0
```
```text
3
4
.25
1
```

9. **Boolean short-circuiting — not uniquely determined**
```bc
a=0
0 && (a=1)
a
```
Short-circuit:
```text
0
0
```
Eager evaluation:
```text
0
1
```

10. **Binary operand evaluation order — not uniquely determined**
```bc
i=1
i++-i++
i
```
Left operand first:
```text
-1
3
```
Right operand first:
```text
1
3
```

11. **Indexed `op=` evaluation order — not uniquely determined**
```bc
i=0
a[0]=10
a[i++]+=i
i
a[0]
```
Subscript first:
```text
1
11
```
RHS first:
```text
1
10
```

12. **Output from `for` expression 3 — not uniquely determined**
```bc
for(i=0;i<2;i++) print i
print "\n"
```
If header expressions are silent:
```text
01
```
If expression 3 behaves like an ordinary expression statement:
```text
00
11

```

13. **Dynamic scope, call-time `ibase`, and redefinition — uniquely determined**
```bc
x=7
define g(){return x}
define f(x){return g()}
f(3)
x
ibase=10
define h(){ibase=2;return 10}
h()
ibase
define h(){return 11}
h()
```
```text
3
7
10
2
3
```

14. **Arrays, void call, runtime survival, uninitialized values, halt/quit**
```bc
a[0]=1
define v(x[]){x[0]=2}
define r(*x[]){x[0]=3}
define void z(){}
v(a[])
a[0]
r(a[])
a[0]
z()
print x,a[4],":"
{print "B";1/0;print "C"}
print "D\n"
if(0) halt
print "E\n"
if(0) quit
print "F\n"
```
With normal alias semantics for `*x[]`:
```text
0
1
0
3
00:BD
E
```
A hyper-literal reading that does not infer aliasing would leave `a[0]` as `1`; thus this witness is not completely determined by the text.