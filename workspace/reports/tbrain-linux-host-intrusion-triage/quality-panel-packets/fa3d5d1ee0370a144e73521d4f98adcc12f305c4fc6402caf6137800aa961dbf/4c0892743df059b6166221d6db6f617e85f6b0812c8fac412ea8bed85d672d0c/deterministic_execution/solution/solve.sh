#!/bin/bash
# Reference: install solution/triage.py as /app/triage.py.
#
# case-guide rule -> where solution/triage.py implements it
#   1 time                  read_collection(): auth/dpkg local at utc_offset; date_lines(): year of an auth-log
#                           line walked back from the collection time; analyze(): the host-clock error is the
#                           difference between an sshd line and its remote collector copy, the step is the
#                           first line that agrees again, and fix() corrects every earlier host-clock reading
#                           (auth, wtmp, btmp, history stamps, ctimes, dpkg)
#   2 hostile address       five btmp failures with the fifth at most 600 s after the first
#   3 initial access        earliest wtmp login from a hostile address
#   4 sources and accounts  fixed point: intruder addresses -> sessions; keys in intruder accounts' histories
#                           -> fingerprints -> key logins from new addresses; root once escalated
#   5 privilege escalation  first sudo to root whose TTY's open wtmp session is an intruder session, or a root login
#   6 persistence           listed paths of the stated kinds whose ctime lies in an intruder session, minus files
#                           a package lists written within 2 s of its status installed line
#   7 first/last activity   min/max over intruder failures, logins, logouts, sudo lines, stamped history inside
#                           intruder sessions and persistence ctimes (an open session's end is not an event)
set -euo pipefail
cp "$(dirname "$0")/triage.py" /app/triage.py
chmod 0755 /app/triage.py
