#!/bin/bash
# Reference pysed: a pure-Python GNU sed 4.9 for the subset in the task.
#
# Area (manual chapter)          File         How
# options, script assembly (2)   sed.py       -n/-E/-s, -e and --expression joined by newlines; a first
#                                             script line starting with #n forces -n
# commands (3)                   sed.py       parser for addresses, blocks, labels, a/i/c text, s and y;
#                                             executor with pattern and hold space, append queue,
#                                             n/N at end of input, D restarts, t flag reset on each read,
#                                             q/Q exit codes, l wrapping with octal escapes
# addresses (4)                  sed.py       numbers, $, /re/ and \cREc with I/M, first~step,
#                                             addr1,+N, addr1,~N (up to the next multiple after addr1),
#                                             0,/re/; -s makes numbers, $ and ranges per file
# regular expressions (5)        posixre.py   BRE/ERE parser with GNU escapes and classes; exhaustive
#                                             matcher that takes the leftmost match and then the
#                                             longest, groups from the first path reaching that end
# replacement (3.3)              sed.py       & \1-\9 \n and \L \U \l \u \E
#
# Strategy: write the whole tool in the standard library; the regex engine is a custom
# backtracking matcher because Python's re is leftmost-first, not leftmost-longest.
set -euo pipefail
install -d /app/pysed
cp /solution/pysed/sed.py /solution/pysed/posixre.py /app/pysed/
