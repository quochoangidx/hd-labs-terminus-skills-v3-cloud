Our minimal build images have no m4, and the build scripts that still run it are being pointed at `/app/pym4/m4.py` instead. Implement it so that `python3 /app/pym4/m4.py [FILE]...` behaves exactly like GNU m4 1.4.19 run as `m4 [FILE]...` with `LC_ALL=C`: the same standard output, byte for byte, and the same exit status. What goes to standard error is not compared. The language chapters of the GNU m4 manual are in `/app/docs/m4.txt`.

It has to cover the language those chapters describe:

- the lexical rules for names, quoted strings, comments and other tokens, macro invocation, argument collection, and rescanning;
- the builtins `define`, `undefine`, `defn`, `pushdef`, `popdef`, `indir`, `builtin`, `ifdef`, `ifelse`, `shift`, `dnl`, `changequote`, `changecom`, `m4wrap`, `include`, `sinclude`, `divert`, `undivert`, `divnum`, `len`, `index`, `regexp`, `substr`, `translit`, `patsubst`, `format`, `incr`, `decr`, `eval`, `errprint`, `__file__`, `__line__`, `__program__` and `m4exit`, together with the predefined `__gnu__` and `__unix__`;
- input from the files named on the command line in order, from `-` for standard input, or from standard input when no file is named.

No command-line options are given, and files named to `include`, `sinclude` or `undivert` are relative to the current directory. Input is ASCII text of at most a few hundred lines, and it always finishes. Use only the Python standard library and do not start other programs.

It will be checked against GNU m4 1.4.19 itself with many inputs.
