Our minimal images have no dc, and the build and report scripts that still run it are being pointed at `/app/pydc/dc.py` instead. Implement it so that `python3 /app/pydc/dc.py ARGS...` behaves exactly like GNU dc 1.4.1 run as `dc ARGS...` with `LC_ALL=C` and the same standard input: it must produce the same standard output, byte for byte. Standard error and the exit status are not compared. The GNU dc manual is in `/app/docs/dc.txt`.

It has to cover everything the manual describes except the `!` shell command (the `!<R`, `!>R` and `!=R` comparisons are required):

- the options `-e EXPR` and `-f FILE` (each option and its argument as two separate arguments, in any number and order) and plain FILE arguments, with standard input read when no expression or file is given. `-h`, `-V` and long options are not used;
- every printing, arithmetic, stack, register, parameter, string, status-inquiry and miscellaneous command, including macros, conditional execution, the register stacks and arrays, and `?` reading a line of standard input;
- numbers of any size and precision, in every input and output radix the manual allows, including the way long numbers are split across lines.

GNU dc follows these conventions, which the manual leaves unstated:

- Arithmetic results that are cut to a number of fraction digits are truncated toward zero.
- A number whose integer part is zero is printed without a leading `0` (`.5`, `-.25`), and a zero value prints as `0` whatever its scale.
- In output radixes above 10, digits are the uppercase letters `A` to `F`. Above 16, each digit of the integer part is printed as a decimal number, zero-padded to the width of the largest digit in that radix and preceded by a space.
- In a radix other than 10, a number whose scale is n prints the smallest number k of fraction digits for which the radix to the power k is at least 10 to the power n, each digit truncated.
- A long number is printed as lines of 69 characters, each followed by `\`, then the rest. The count starts afresh at the first character of each number, including its sign. `DC_LINE_LENGTH` is never set.
- `f` prints the stack from the top down, one entry per line.
- `;R` for an array element that was never stored pushes 0.
- A number is written as an optional `_`, digits and at most one `.`, so `3.4.5` is 3.4 followed by .5. The digits `0` to `9` and `A` to `F` count at face value in every input radix. A number typed with n fraction digits has scale n, its value truncated to n decimal fraction digits.
- After an error, such as popping an empty stack, dc prints a diagnostic and goes on with the next command. When an arithmetic operator, a comparison or `r` finds too few values or a string among them, it leaves the stack unchanged, and so does a division, remainder or modular power that fails. A command that takes a single value removes it even if it then fails.
- A conditional whose register is empty behaves like `lR` followed by `x`, so it pushes 0.
- `Z` of zero is 1.
- A value used as a precision, a radix, an array index, an `R` or `Q` count or by `a` is cut to its integer part. A non-zero value whose integer part is 0, or one too large for a 64-bit integer, counts as -1.
- `^` can leave a negative zero, which prints as `-0`.
- `Q` never makes dc exit, while `q` at the top level ends the whole run. FILE arguments are processed after all `-e` and `-f` options, whatever their position.

Scripts always finish. Standard input is never a terminal. Input is ASCII text of at most a few hundred lines. Use only the Python standard library and do not start other programs.

Every check relies only on behaviour that the manual describes, together with the rules above. It will be checked against GNU dc 1.4.1 itself with many scripts.
