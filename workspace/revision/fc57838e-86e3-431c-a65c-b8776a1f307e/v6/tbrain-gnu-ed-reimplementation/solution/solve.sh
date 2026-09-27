#!/bin/bash
# Reference pyed: a pure-Python GNU ed 1.19 for everything in the task.
#
# Area (manual chapter)          File         How
# invoking (3)                   ed.py        -E/-l/-p/-q/-r/-s; initial FILE read with byte count; a
#                                             missing FILE is fatal only when stdin is a regular file
# line addressing (4)            ed.py        ., $, N, +N/-N and repeated +/-, /RE/ and ?RE? with
#                                             wrap-around, 'x marks, ',' ';' '%' ranges, N-tuples keep
#                                             the last two, ';' moves the current address first
# regular expressions (5)        posixre.py   BRE/ERE with GNU escapes and classes, compiled to a
#                                             small program walked depth-first in pattern order,
#                                             each (instruction, position) once per search, so the
#                                             leftmost start and then the longest match win in time
#                                             linear in the line; NOTBOL for repeated matches
# commands (6)                   ed.py        linked line list with an undo stack of add/delete/move
#                                             atoms (undo of undo redoes), cut buffer for x/y, marks
#                                             that die with deleted lines, global active list that
#                                             drops lines touched by the command list, G/V reading
#                                             command lists from stdin with '&' repeat
# substitute (7)                 ed.py        count and g suffixes, % replacement, \N and &, line
#                                             splitting, s repeat form with g/p/r/count
# diagnostics (9)                ed.py        '?' on stdout; exit on first error when stdin is a
#                                             regular file, otherwise continue; q/e/EOF warning once on
#                                             a modified buffer; exit status per -l
#
# Strategy: port the editor's own data structures (a circular list of line nodes and an
# undo stack that relinks them) so current address, marks and undo follow the manual.
set -euo pipefail
install -d /app/pyed
cp /solution/pyed/ed.py /solution/pyed/posixre.py /app/pyed/
