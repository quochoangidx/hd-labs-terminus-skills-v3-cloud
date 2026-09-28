Our minimal images ship without `sed`, and the scripts that still call it are being pointed at `/app/pysed/sed.py` instead. Implement it so that `python3 /app/pysed/sed.py ARGS...` behaves exactly like GNU sed 4.9 run as `sed ARGS...` with `LC_ALL=C`: the same standard output, byte for byte, and the same exit status. What goes to standard error is not compared. The GNU sed 4.9 manual is in `/app/docs/sed.txt`.

It has to cover this part of GNU sed:

- the options `-n`, `-E` and `-s`, each given as its own argument before the script, and scripts given with `-e SCRIPT` (repeatable, the pieces joined by newlines) or as the first non-option argument, followed by the names of input files, or none to read standard input;
- every command in chapter 3 of the manual except `e`, `F`, `r`, `R`, `w`, `W` and `v`, with every `s` flag except `e` and `w`, including the one-line and multi-line forms of `a`, `i` and `c`, labels, blocks, `!`, comments and a script whose first two characters are `#n`;
- every address form in chapter 4, including `first~step`, `addr1,+N`, `addr1,~N` and `0,/regexp/`;
- the regular expressions of chapter 5, basic and extended, with the GNU extensions, escapes, character classes, bracket expressions and back-references, and the special replacement escapes `\L`, `\U`, `\l`, `\u` and `\E`. Matching is POSIX leftmost-longest: of the matches that start at the leftmost possible position, the longest one wins, whichever alternative of a `|` produces it.

Scripts never fail and always finish. Input is at most a few dozen lines of ASCII text, each ending with a newline; files may be empty, and a file named on the command line may not exist. Nothing sets `POSIXLY_CORRECT`. Use only the Python standard library, do not start other programs, and finish each run within a few seconds.

It will be checked against GNU sed 4.9 itself with about a thousand scripts and inputs, from one-line substitutions to multi-line scripts that juggle the hold space, over standard input and several files. Every check relies only on behaviour that the manual describes, together with the matching rule above.
