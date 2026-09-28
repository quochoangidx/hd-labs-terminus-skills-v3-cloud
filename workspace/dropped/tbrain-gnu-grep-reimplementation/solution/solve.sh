#!/bin/bash
# Reference pygrep: a pure-Python GNU grep 3.8 for the subset in the task.
#
# Area (manual section)            File         How
# pattern syntax (3)               posixre.py   BRE/ERE parser with GNU escapes (\w \W \s \S \b \B \< \>
#                                               \` \'), classes and back-references; thread matcher that
#                                               takes the leftmost match and then the longest
# matcher selection (2.1.1-2.1.2)  grep.py      -G/-E/-F (two different ones: "conflicting matchers"),
#                                               -e/-f/operand split at newlines keeping empty patterns,
#                                               -i/--no-ignore-case, -v, -w (GNU retry: shorter match at
#                                               the same start, then later starts), -x
# output controls (2.1.3-2.1.4)    grep.py      -c/-l/-L/-q precedence, -m per file, -o with -b offsets,
#                                               -H/-h/--label/-n/-T (width from the file size), -Z/-z
# context (2.1.5)                  grep.py      prtext/pending emulation: before/after context, a group
#                                               separator between non-adjacent groups, also across files
# binary files (2.1.7)             grep.py      a NUL anywhere makes the file binary; -I selects nothing;
#                                               otherwise NULs end lines, no line output, stop at the first
#                                               selected line unless -c
# exit status (2.3)                grep.py      0 selected, 1 none, 2 on error unless -q already selected
#
# Strategy: write the tool in the standard library; the regex engine is custom because
# Python's re is leftmost-first, not POSIX leftmost-longest.
set -euo pipefail
install -d /app/pygrep
cp /solution/pygrep/grep.py /solution/pygrep/posixre.py /app/pygrep/
