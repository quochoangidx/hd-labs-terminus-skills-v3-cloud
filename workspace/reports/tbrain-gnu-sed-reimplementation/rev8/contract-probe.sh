#!/bin/bash
# contract-probe.sh <container>: the three reference findings (6, 7, 8) run through GNU sed 4.9 and
# the mounted reference, plus what the mounted docs say about each.
C=$1
t() { inp=$1; shift
  s=$(printf "$inp" | docker exec -i -e LC_ALL=C $C sed "$@" 2>/dev/null | od -An -c | tr -s ' ')
  gs=$(printf "$inp" | docker exec -i -e LC_ALL=C $C sed "$@" >/dev/null 2>&1; echo $?)
  r=$(printf "$inp" | docker exec -i -e LC_ALL=C $C python3 /ref/sed.py "$@" 2>/dev/null | od -An -c | tr -s ' ')
  rs=$(printf "$inp" | docker exec -i -e LC_ALL=C $C python3 /ref/sed.py "$@" >/dev/null 2>&1; echo $?)
  echo "sed $* : gnu=[$s] status=$gs ref=[$r] status=$rs"; }
echo "== finding 6: 0 as the second address"
t 'x\n' -n '1,0p'
echo "== finding 7: leading hyphen in a bracket expression"
t 'Z\n-\na\n' -n '/[-a]/p'
echo "== finding 8: backslash delimiter with an escaped backslash inside"
t 'a\\b\n' -n '\\a\\\\b\\p'
echo "== manual, zero address"; docker exec $C grep -n "only places where the" -A2 /docs/sed.txt
echo "== manual, delimiter"; docker exec $C grep -n "each must be escaped by a backslash" /docs/sed.txt
echo "== scope departures"; docker exec $C grep -o "second address of a range\|a backslash as the delimiter of a regular expression that itself contains a backslash" /docs/scope.md || echo "scope.md: neither is listed"
