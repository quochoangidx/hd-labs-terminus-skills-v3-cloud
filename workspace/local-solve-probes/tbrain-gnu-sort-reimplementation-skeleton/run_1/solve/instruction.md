Our minimal images ship without coreutils, and the scripts that still call `sort` are being pointed at `/app/pysort/sort.py` instead. Implement it so that `python3 /app/pysort/sort.py ARGS...` behaves exactly like GNU sort 9.1 run as `sort ARGS...` with `LC_ALL=C`: the same standard output, byte for byte, and the same exit status. What goes to standard error is not compared. The sort chapters of the coreutils manual are in `/app/docs/sort.txt`.

It has to cover:

- the ordering options `-b`, `-d`, `-f`, `-g`, `-h`, `-i`, `-M`, `-n`, `-r` and `-V`, given globally or attached to a key;
- keys given with `-k POS1[,POS2]` in the full form the manual describes, any number of them, and `-t` with a single character;
- `-s`, `-u`, `-z`, `-c` and `-C`;
- short options clustered or separate (`-nr`, `-k2,2` or `-k 2,2`, `-t:` or `-t :`), and input from files named on the command line, from `-`, or from standard input when no file is named.

Every command line is valid. Input is ASCII text of at most a few hundred lines; it may be empty or lack a final newline, and a named file may not exist. Use only the Python standard library and do not start other programs.

It will be checked against GNU sort 9.1 itself with many command lines over many inputs.
