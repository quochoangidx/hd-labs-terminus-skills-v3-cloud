#!/bin/bash
# Reference repair of /app/src/looptune against /app/docs/control-note.md (LT-7).
#
# Note section            | File           | Change
# ------------------------+----------------+---------------------------------------------------
# 2 proportional term     | terms.py       | P = K*(b*r - y) for 0 <= b <= 1; other weights keep K*b*(r - y)
# 3 integral term         | terms.py       | addition K*h/Ti*e (full error) for Ti > 0; other Ti keep today's result
# 3 integral timing       | controller.py  | additions made after u is formed; terms()["i"] is I at step start
# 4 derivative term       | terms.py       | backward difference on the measurement for Td > 0 and N > 0;
#                         |                | other settings keep today's error-driven forward update
# 4 first step            | controller.py  | y_previous = y on the first step
# 5 limits                | terms.py       | a value above the high limit is held at high, for low < high;
#                         |                | limits at or past each other keep today's hold result
# 5 slew                  | terms.py,      | allowance s*h for s > 0 and no slew on the first step; other
#                         | controller.py  | rates keep today's helper, fed today's previous output
# 6 anti-windup           | terms.py       | h/Tt*(u - v) for Tt > 0; other Tt keep today's result
# 7 manual mode           | controller.py  | I = m - P - D - f and v = m
# 8 retune                | controller.py  | I changes by old P minus new P (sign was reversed)
#
# Strategy: every helper branches only on the range the note writes its rule for,
# and keeps its shipped expression verbatim outside it, as the instruction requires.
set -euo pipefail
cd /
patch -p1 --forward --no-backup-if-mismatch < /solution/fix.patch
