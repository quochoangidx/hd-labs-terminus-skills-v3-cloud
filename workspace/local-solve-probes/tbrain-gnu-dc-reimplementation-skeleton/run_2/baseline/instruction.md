Our minimal images have no dc, and the build and report scripts that still run it are being pointed at `/app/pydc/dc.py` instead. Implement it so that `python3 /app/pydc/dc.py ARGS...` behaves exactly like GNU dc 1.4.1 run as `dc ARGS...` with `LC_ALL=C` and the same standard input. It must produce the same standard output, byte for byte, and its exit status must be zero exactly when GNU dc's is. What goes to standard error is not compared. The GNU dc manual is in `/app/docs/dc.txt`.

It has to cover everything the manual describes except the `!` command:

- the options `-e SCRIPT` and `-f FILE` (each option and its argument as two separate arguments, in any number and order) and plain FILE arguments, with standard input read when no script or file is given;
- every printing, arithmetic, stack, register, parameter, string, status-inquiry and miscellaneous command, including macros, conditional execution, the register stacks and arrays, and `?` reading a line of standard input;
- numbers of any size and precision, in every input and output radix the manual allows, including the way long numbers are broken across lines.

Scripts may contain errors, such as popping an empty stack, and dc carries on after them the way GNU dc does. Scripts always finish. Standard input is never a terminal. Input is ASCII text of at most a few hundred lines. Use only the Python standard library and do not start other programs.

Every check relies only on behaviour that the manual describes, together with the rules above. It will be checked against GNU dc 1.4.1 itself with many scripts.
