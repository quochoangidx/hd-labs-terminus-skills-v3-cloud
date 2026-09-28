#!/bin/bash
# the panel's own distinguishing inputs, run through GNU sed and each mutant in the task image
cd /work
P=python3
t() { m=$1; shift; want=$(printf "$IN" | sed "$@" 2>/dev/null; echo "st=$?"); got=$(printf "$IN" | $P wp-mut/$m/app/pysed/sed.py "$@" 2>/dev/null; echo "st=$?"); ref=$(printf "$IN" | $P ref/sed.py "$@" 2>/dev/null; echo "st=$?"); [ "$want" = "$ref" ] && r=REF-OK || r=REF-DIFF; [ "$want" = "$got" ] && echo "SAME $m $r $*" || echo "DIFF $m $r $* want=$(echo $want|head -c 80) got=$(echo $got|head -c 80)"; }
IN="$(printf 'a%.0s' $(seq 65))\n" t line-cap-64 's/a/X/g'
IN="$(seq 11 | tr '\n' '|' | sed 's/|/\\n/g')" t special-range-one-digit -n '1,+10p'
IN="$(seq 11 | tr '\n' '|' | sed 's/|/\\n/g')" t special-range-one-digit -n '1,~10p'
IN='aaaaaaaaaa\n' t interval-one-digit 's/a\{10\}/X/'
mkdir -p /tmp/q && cd /tmp/q && printf 'x\n' > f && IN='' t2=1; cd /work
q() { m=$1; shift; want=$(cd /tmp/q; sed "$@" 2>/dev/null </dev/null; echo "st=$?"); got=$(cd /tmp/q; $P /work/wp-mut/$m/app/pysed/sed.py "$@" 2>/dev/null </dev/null; echo "st=$?"); ref=$(cd /tmp/q; $P /work/ref/sed.py "$@" 2>/dev/null </dev/null; echo "st=$?"); [ "$want" = "$ref" ] && r=REF-OK || r=REF-DIFF; [ "$want" = "$got" ] && echo "SAME $m $r $*" || echo "DIFF $m $r $* want=$want got=$got"; }
q bare-q-clears-status q missing f
IN='b\n' t bre-dollar-before-alt-literal -n -e 's/a\|b$/X/p'
mkdir -p /tmp/q && printf 'a\n' > /tmp/q/f1 && printf 'b\n' > /tmp/q/f2
q nes-together-drops-s -n -E -s '$p' f1 f2
IN='a\n' t question-delimiter-rejected 's?a?X?'
# the panel's input for f5 puts $ at the end of the whole regex; $ right before \| is this one
IN='b\nbx\n' t bre-dollar-before-alt-literal -n -e 's/b$\|x/X/p'
