Our minimal images have no ed, and the maintenance scripts that still pipe edit commands into it are being pointed at `/app/pyed/ed.py` instead. Implement it so that `python3 /app/pyed/ed.py [OPTIONS] [FILE]` behaves exactly like GNU ed 1.19 run as `ed [OPTIONS] [FILE]` with `LC_ALL=C` and the same standard input. It must produce the same standard output, byte for byte, and the same exit status, and leave the same files with the same contents in the current directory. What goes to standard error is not compared. The GNU ed manual is in `/app/docs/ed.txt`.

It has to cover everything the manual describes except shell commands:

- the options `-E`, `-G`, `-l`, `-p STRING`, `-q`, `-r`, `-s` and `-v`, each given as its own argument before the optional FILE;
- every form of line address and address range;
- basic and extended regular expressions, with matching that is POSIX leftmost-longest: of the matches that start at the leftmost possible position, the longest one wins, whichever alternative of a `|` produces it;
- every command, command suffix and `s` flag, including the global commands, undo, marks and the interactive forms `G` and `V`, which read their command lists from standard input like any other line.

The `!` command, and FILE or command arguments that start with `!`, never appear. Standard input is never a terminal. Sometimes it is a regular file and sometimes a pipe. The files involved are ASCII text of at most a few dozen lines each, and some of them may not exist. Use only the Python standard library and do not start other programs.

It will be checked against GNU ed 1.19 itself with many command scripts.
