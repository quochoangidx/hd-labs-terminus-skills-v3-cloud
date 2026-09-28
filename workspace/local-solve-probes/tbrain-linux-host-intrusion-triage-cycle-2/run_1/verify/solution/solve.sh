#!/bin/bash
# Reference: install solution/triage.py as /app/triage.py.
#
# case-guide rule -> where solution/triage.py implements it
#   1 clocks and zones      read_collection(), epoch(): auth/dpkg local at utc_offset, the rest epoch UTC
#   2 year of a line        date_lines(): anchor the last auth.log line to the collection year, step back on a month decrease
#   3 clock step            analyze(): +N to auth lines before the step line and to host-clock stamps earlier than it (fix())
#   4 logins                read_records() for wtmp/btmp; Accepted lines give method and fingerprint
#   5 hostile address       five btmp failures with the fifth at most 600 s after the first
#   6 initial access        earliest wtmp login from a hostile address
#   7-8, 10 fixed point     attacker keys from attacker accounts' histories -> addresses -> accounts -> escalation
#   9 sessions              login to DEAD_PROCESS on the same line; sudo belongs to the session open on its TTY
#   11 persistence          listed class paths whose ctime lies in an attacker session, minus package-written ones
#   12 first/last activity  min/max over the listed attacker events
set -euo pipefail
cp "$(dirname "$0")/triage.py" /app/triage.py
chmod 0755 /app/triage.py
