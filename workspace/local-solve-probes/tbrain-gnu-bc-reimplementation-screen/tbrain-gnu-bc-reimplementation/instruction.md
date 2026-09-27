Our minimal images have no bc, and the report scripts that still pipe calculations into it are being pointed at `/app/pybc/bc.py` instead. Implement it so that `python3 /app/pybc/bc.py [FILE]...` behaves exactly like GNU bc 1.07.1 run as `bc [FILE]...` with `LC_ALL=C` and the same standard input: it must produce the same standard output, byte for byte. Standard error and the exit status are not compared. The GNU bc manual page is in `/app/docs/bc.txt`.

It has to cover the whole bc language that the manual describes:

- numbers of any size and precision, simple and array variables, `scale`, `ibase`, `obase` and `last` (also written `.`), and both kinds of comment;
- every operator, with the manual's precedence, and `length`, `scale` and `sqrt`;
- every statement, including strings, `print`, `if`/`else`, `while`, `for`, `break`, `continue` in `for` loops, `halt`, `quit` and compound statements;
- functions, with parameters, `auto` variables, recursion, `void` functions and array parameters passed by value or by variable;
- runtime errors, which end the current execution block as the manual describes.

Programs are read from the FILE arguments in order and then from standard input. They are valid bc: every line ends with a newline, and calls pass the right number and kinds of arguments. Command-line options, the math library, `read`, `random`, `limits`, `warranty` and `history` are not used, and neither is `continue` inside a `while` loop. Input bases stay at or below 16, output bases at or below 999, and array indexes below 65536. Standard input is never a terminal, and `BC_LINE_LENGTH`, `BC_ENV_ARGS` and `POSIXLY_CORRECT` are not set.

GNU bc follows these rules, which the manual leaves unstated:

- The product of a and b has the smallest of scale(a)+scale(b) and the largest of `scale`, scale(a) and scale(b) as its scale. The square root of 0 is 0 and of 1 is 1, both with scale 0; the square root of any other x has the larger of `scale` and scale(x).
- Wherever digits are cut, the value is truncated toward zero, never rounded.
- A number whose integer part is zero is printed without a leading `0` (`.5`, `-.25`), and a zero value prints as `0` whatever its scale.
- In output bases 11 to 16, digits are the uppercase letters `A` to `F`. Above 16, each digit of the integer part is printed as a decimal number, zero-padded to the width of `obase-1` and preceded by a space. After the point, the fraction digits are printed the same way, separated by single spaces, with no space right after the point.
- In an output base other than 10, a number of scale n is printed with the smallest number k of fraction digits for which `obase` to the power k is at least 10 to the power n, each digit truncated.
- bc counts the characters it has printed since the last newline, numbers and strings alike. When a character would become the 69th on its line, bc first prints a backslash and a newline, so the character starts the next line.
- A constant is converted when the statement containing it runs, with the input base in force at that moment (in a function body, the one in force when the function was called, as the manual says). A constant with n digits after the point has scale n, and in an input base other than 10 its value is truncated to n decimal fraction digits.
- A variable or array element that was never assigned holds 0.
- Dividing by zero, taking a remainder by zero, raising zero to a negative power, the square root of a negative number, an array index below 0 or strictly between 0 and 1, and calling an undefined function are all runtime errors.

Use only the Python standard library and do not start other programs.

Every check relies only on behaviour that the manual describes, together with the rules above. It will be checked against GNU bc 1.07.1 itself with many programs.
