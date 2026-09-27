Our minimal images ship without `sed`, and scripts that still call it must be pointed at `/app/pysed/sed.py` instead. Implement it so that `python3 /app/pysed/sed.py ARGS...` behaves exactly like GNU sed 4.9 run as `sed ARGS...` with `LC_ALL=C`: the same standard output, byte for byte, and the same exit status. The GNU sed manual is in `/app/docs/sed.txt`.

It has to cover this part of GNU sed:

- the options `-n` (`--quiet`, `--silent`), `-E` (`-r`, `--regexp-extended`) and `-s` (`--separate`), scripts given with `-e SCRIPT` (repeatable, `--expression=SCRIPT`) or as the first non-option argument, and input from standard input or from files named on the command line;
- every command in chapter 3 of the manual except `e`, `F`, `r`, `R`, `w`, `W` and `v`, with every `s` flag except `e` and `w`, including the one-line and multi-line forms of `a`, `i` and `c`, labels, blocks, `!`, comments and a first line of `#n`;
- every address form in chapter 4, including `first~step`, `addr1,+N`, `addr1,~N` and `0,/regexp/`;
- the regular expressions of chapter 5, basic and extended, with the GNU extensions, escapes, character classes, bracket expressions and back-references, matched as the manual describes, and the special replacement escapes `\L`, `\U`, `\l`, `\u` and `\E`.

Scripts are always valid, input is ASCII text whose lines end with a newline, and there is no other locale. Use only the Python standard library and do not start other programs.

It will be checked against GNU sed 4.9 with many scripts and inputs, from one-line substitutions to multi-line scripts that juggle the hold space, over standard input and several files.
