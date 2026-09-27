Our minimal images have no grep, and the scripts that still call it are being pointed at `/app/pygrep/grep.py` instead. Implement it so that `python3 /app/pygrep/grep.py ARGS...` behaves exactly like GNU grep 3.8 run as `grep ARGS...` with `LC_ALL=C` and the same standard input: the same standard output, byte for byte, and the same exit status. What goes to standard error is not compared. The GNU grep manual is in `/app/docs/grep.txt`.

It has to cover everything the manual describes about matching and output, except directory recursion, device handling, `--color`, `--line-buffered`, `-U` and `--exclude`/`--include` style file selection:

- basic, extended and fixed-string patterns (`-G`, `-E`, `-F`), several patterns given with `-e` or `-f` or as lines of one argument, `-i`, `--no-ignore-case`, `-v`, `-w`, `-x`;
- the output controls `-c`, `-l`, `-L`, `-m`, `-o`, `-q`, `-s`, `-b`, `-H`, `-h`, `--label`, `-n`, `-T`, `-Z`, `-z` and the context options `-A`, `-B`, `-C`, `-NUM`, `--group-separator` and `--no-group-separator`;
- `--binary-files`, `-a` and `-I` for input that contains NUL bytes;
- files named on the command line, `-` for standard input, and standard input when no file is named; a named file may not exist.

Options are given as separate arguments or clustered short options, before the patterns and files. Regular-expression matching is POSIX leftmost-longest: of the matches that start at the leftmost possible position, the longest one wins, whichever alternative of a `|` produces it; with several patterns, the match is the leftmost-longest over all of them. Inputs are ASCII text of at most a few hundred lines, apart from occasional NUL bytes. Use only the Python standard library and do not start other programs.

Every check relies only on behaviour that the manual describes, together with the rules above. It will be checked against GNU grep 3.8 itself with many command lines.
