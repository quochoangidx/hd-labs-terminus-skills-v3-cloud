Our minimal images ship without `find`, and the maintenance scripts that still call it are being pointed at `/app/pyfind/find.py` instead. Implement it so that `python3 /app/pyfind/find.py ARGS...` behaves exactly like GNU find 4.9.0 run as `find ARGS...` with `LC_ALL=C` and `TZ=UTC`: the same standard output, byte for byte, and the same exit status. What goes to standard error is not compared. The find manual page and the findutils manual are in `/app/docs/`.

It has to cover this part of GNU find, with symbolic links never followed (the default `-P` behaviour):

- starting points followed by an expression, or an expression alone (meaning `.`);
- the options `-depth`, `-maxdepth` and `-mindepth`;
- the tests `-name`, `-iname`, `-path`, `-ipath`, `-wholename`, `-regex`, `-iregex` (with `-regextype` set to `emacs`, `posix-basic` or `posix-extended`), `-type` (`f`, `d`, `l`), `-size`, `-empty`, `-perm` (octal and symbolic modes, plain, `-` and `/` forms), `-mtime`, `-mmin`, `-newer`, `-links`, `-true` and `-false`;
- the operators `( )`, `!`, `-not`, `-a`, `-and`, `-o`, `-or` and `,`, with the implicit `-a` and the implicit `-print`;
- the actions `-print`, `-print0`, `-prune`, `-quit` and `-printf` with the directives `%p %P %f %h %d %s %y %m %M %l %%`, field widths and flags, and the escapes `\n \t \\ \0`.

A directory's entries are visited in the order `os.scandir` lists them, a directory before its contents unless `-depth` is in effect. The trees searched hold regular files, directories and symbolic links, all readable, with assorted names (including leading dots), sizes, permissions, link counts and modification times, none of them within a minute of a minute boundary relative to the time of the run. A starting point may not exist. Use only the Python standard library and do not start other programs.

It will be checked against GNU find 4.9.0 itself with many expressions over many trees.
