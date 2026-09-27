Our minimal images have no grep, and the scripts that still call it are being pointed at `/app/pygrep/grep.py` instead. Implement it so that `python3 /app/pygrep/grep.py ARGS...` behaves exactly like GNU grep 3.8 run as `grep ARGS...` with `LC_ALL=C` and the same standard input: the same standard output, byte for byte, and the same exit status. What goes to standard error is not compared. The GNU grep manual is in `/app/docs/grep.txt`.

It has to cover everything the manual describes about matching and output, except directory recursion, device handling, `--color`, `--line-buffered`, `-U` and `--exclude`/`--include` style file selection:

- basic, extended and fixed-string patterns (`-G`, `-E`, `-F`), several patterns given with `-e` or `-f` or as lines of one argument, `-i`, `--no-ignore-case`, `-v`, `-w`, `-x`;
- the output controls `-c`, `-l`, `-L`, `-m`, `-o`, `-q`, `-s`, `-b`, `-H`, `-h`, `--label`, `-n`, `-T`, `-Z`, `-z` and the context options `-A`, `-B`, `-C`, `-NUM`, `--group-separator` and `--no-group-separator`;
- `--binary-files`, `-a` and `-I` for input that contains NUL bytes;
- files named on the command line, `-` for standard input, and standard input when no file is named; a named file may not exist.

`-P` is out of scope, and patterns never put a backslash before a character for which the manual gives the backslash no meaning.

Options are given as separate arguments or clustered short options, before the patterns and files. Where options compete, GNU grep 3.8 resolves them as follows:

- Giving two different ones of `-G`, `-E` and `-F` is an error (exit status 2, no output); repeating the same one is fine.
- Apart from `-e` and `-f`, which add patterns each time, an option given more than once counts with its last value, and so do options that set the same thing: of `-H` and `-h`, of `-l` and `-L`, of `-i` and `--no-ignore-case`, of `--group-separator` and `--no-group-separator`, and of `-a`, `-I` and `--binary-files`, the last one given wins. The same holds for repeated `-m` and `--label`.
- `-C NUM` and `-NUM` set both context sizes, the last of them counting. `-A` and `-B` each set one side and take precedence over `-C` and `-NUM` whatever the order.
- `-q` overrides `-l`, `-L` and `-c`; `-l` or `-L` overrides `-c`; `-c` replaces all line output, including that of `-o`.
- `-m` counts selected lines separately in each file, and `-m 0` selects nothing.
- Splitting a pattern list at newlines keeps empty patterns, including a leading or trailing one given with `-e` or as the pattern operand; a pattern file's final newline does not add an empty pattern.
- A group separator also appears between context groups that come from different files.
- A file that cannot be opened is skipped and grep goes on with the next one. The exit status is then 2, unless `-q` has already selected a line.

A file counts as binary when it contains a NUL byte anywhere, unless `-a`, `--binary-files=text` or `-z` is given. With `-I` or `--binary-files=without-match`, a binary file selects no lines at all. Otherwise each NUL byte in a binary file ends a line, as a newline would. Lines are selected as usual, but none of them is printed. Grep stops reading the file at its first selected line, except under `-c`, which counts every selected line as usual.

Regular-expression matching is POSIX leftmost-longest: of the matches that start at the leftmost possible position, the longest one wins, whichever alternative of a `|` produces it; with several patterns, the match is the leftmost-longest over all of them. Inputs are ASCII text of at most a few hundred lines, apart from occasional NUL bytes. Use only the Python standard library, without loading native code (through `ctypes`, for example), and do not start other programs.

Every check relies only on behaviour that the manual describes, together with the rules above. It will be checked against GNU grep 3.8 itself with many command lines.
