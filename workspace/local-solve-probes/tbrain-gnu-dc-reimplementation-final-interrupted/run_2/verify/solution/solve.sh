#!/bin/bash
# Reference pydc: a pure-Python GNU dc 1.4.1 for everything in the task.
#
# Area (manual chapter)          How
# invocation (2)                 -e/-f processed in order, then FILE arguments, '-' is stdin; stdin
#                                only when nothing else was given; q ends the run
# printing (3)                   p/n/f with the output radix, groups for radixes above 16, lines
#                                split at 70 columns; P as a base-256 byte stream
# arithmetic (4)                 bc number semantics with Python integers: exact + and -, the
#                                truncating scale rules of * / % ~ ^ |, and v by Newton iteration
#                                at growing scale exactly as the bc library does it
# stack control (5), registers (6), parameters (7)
#                                main stack, per-register stacks each with its own array, R/r, and
#                                i/o/k with their range checks
# strings (8)                    macros, conditionals (including !< != !>), tail calls, and the q/Q
#                                level counting; ? reads a line of standard input
# status inquiry (9), misc (10)  Z/X/z, comments, arrays
#
# Strategy: port the evaluator of GNU dc and the arithmetic of the bc number library,
# keeping numbers as sign, digits and scale so that every scale rule and -0 survive.
set -euo pipefail
install -d /app/pydc
cp /solution/pydc/dc.py /app/pydc/
