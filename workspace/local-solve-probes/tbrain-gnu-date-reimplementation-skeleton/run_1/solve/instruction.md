Our minimal images ship without coreutils, and the scripts that still call `date` to parse and format timestamps are being pointed at `/app/pydate/date.py` instead. Implement it so that `python3 /app/pydate/date.py ARGS...` behaves exactly like GNU date 9.1 run as `date ARGS...` with `LC_ALL=C` and `TZ=UTC0`: the same standard output, byte for byte, and the same exit status. What goes to standard error is not compared. The date chapters of the coreutils manual, including the full description of date input strings, are in `/app/docs/date.txt`.

It only ever displays dates, never sets the clock. It has to cover:

- `-d STRING` / `--date=STRING` and `-f FILE` / `--file=FILE`, with date strings of every kind the manual's chapter on date input formats describes;
- `-u`, `-I[FMT]` / `--iso-8601[=FMT]`, `-R` / `--rfc-email` and `--rfc-3339=FMT`;
- an output format `+FORMAT` with every conversion specifier, flag, field width and modifier the manual lists.

Every date string names a calendar date including its year, or starts with `@`, so the current time never matters. A day of the week in a string that also names a calendar date has no effect, as in GNU date. The only time zone words are `UTC` and `Z`, while numeric time zone corrections may appear anywhere the manual allows them. A date string may be invalid. Use only the Python standard library and do not start other programs.

It will be checked against GNU date 9.1 itself with many date strings and formats.
