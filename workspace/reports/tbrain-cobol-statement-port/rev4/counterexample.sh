#!/bin/bash
# Findings 1 and 2: run the panel's own reach inputs through the returned tree's
# GnuCOBOL 3.1.2 build stage and through the returned reference; compare bytes.
# Usage: counterexample.sh <returned task dir> <out dir>
set -uo pipefail
task="$1"; out="$2"; mkdir -p "$out"; cd "$out"
docker build -q --target legacy -t cobol-legacy:rev4-returned "$task/tests" >/dev/null || { echo "build failed"; exit 2; }
cp "$task/environment/app/legacy/samples/2025q1-north.dat" f1.dat
printf '10004821X;PAY;1.00;cash\n' > f1.pay
printf 'H20250331NORTH\nC10000001Test Person             D000000000000090+00000000000000\n' > f2.dat
printf '10000001;ADJ;-1.20;x\n10000001;ADJ;-1.50;x\n10000001;REF;-1.20;x\n10000001;FEE;-1.20;x\n10000001;PAY;-1.20;x\n' > f2.pay
docker run --rm -v "$out:/w" cobol-legacy:rev4-returned sh -c 'cd /w && CUSTIN=f1.dat PAYIN=f1.pay STMTOUT=f1.cobol.stmt /legacy/WBILL && CUSTIN=f2.dat PAYIN=f2.pay STMTOUT=f2.cobol.stmt /legacy/WBILL && grep -n "40311912\|^LINE  11 " /expected/generated_01.stmt /expected/generated_04.stmt; grep -n "ADJ 91000003\|ADJ 91000001" /expected/postings_rounding_modes.stmt' > corpus-evidence.txt 2>&1
python3 "$task/solution/wbill.py" f1.dat f1.pay f1.port.stmt
python3 "$task/solution/wbill.py" f2.dat f2.pay f2.port.stmt
rc=0
cmp f1.cobol.stmt f1.port.stmt || rc=1
cmp f2.cobol.stmt f2.port.stmt || rc=1
echo "--- finding 1: COBOL on 10004821X;PAY;1.00;cash (sample readings)"; tail -3 f1.cobol.stmt
echo "--- finding 2: COBOL on ADJ/REF/FEE/PAY -1.20 and ADJ -1.50"; grep "WHOLE" f2.cobol.stmt
echo "--- graded corpus lines the same rules already decide"; cat corpus-evidence.txt
echo "identical=$([ $rc -eq 0 ] && echo yes || echo no)"
exit $rc
