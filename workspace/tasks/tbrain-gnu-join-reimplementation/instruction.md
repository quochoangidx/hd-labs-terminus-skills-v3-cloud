Our minimal images ship without coreutils, and the report scripts that still call `join` are being pointed at `/app/pyjoin/join.py` instead. Implement it so that `python3 /app/pyjoin/join.py ARGS...` behaves exactly like GNU join from coreutils 9.1 run as `join ARGS...` with `LC_ALL=C` and the same standard input: the same standard output, byte for byte, and the same exit status. What goes to standard error is not compared. The join chapter of the coreutils manual is in `/app/docs/join.txt`.

It has to cover every option that chapter describes: `-a`, `-v`, `-e`, `-i`, `-1`, `-2`, `-j`, `-o` (field lists and `auto`), `-t` (including `-t ''` and `-t '\0'`), `-z`, `--header`, `--check-order` and `--nocheck-order`. Options come before the two file operands, each option letter as its own argument followed by its value as the next argument, and either operand may be `-` for standard input.

The input files are always sorted on their join fields the way the chapter says they must be for the options in use. They are ASCII text of at most a few dozen lines, may be empty or lack a final newline, and may have lines with fewer fields than others. Use only the Python standard library and do not start other programs.

Every check relies only on behaviour that the chapter describes, together with the rules above. It will be checked against GNU join itself with many command lines and inputs.
