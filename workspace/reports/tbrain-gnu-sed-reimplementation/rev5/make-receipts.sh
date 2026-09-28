#!/bin/bash
# Writes the v6 ledger receipts.
set -u
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
cd "$ROOT"
R=workspace/reports/tbrain-gnu-sed-reimplementation
RET=e93b54684a98ae665ddee8c273ebc90ec9ca2ba26de574867ae9b2a754105d8e
REP=$1
L=$R/ledger-receipts-v6
P=$ROOT/$R/rev5/probe
REF_RET=$ROOT/$R/rev5/returned-tree/solution/pysed
REF_REP=$ROOT/workspace/tasks/tbrain-gnu-sed-reimplementation/solution/pysed
rc() { python3 $R/rev5/receipt.py "$@"; }
rc $L/repro-probes-returned.json $RET "the returned reference against GNU sed 4.9 on every probe the v6 findings name: DIFF rows (5, 8, 11) are reference defects; SAME rows show GNU agreeing with the reference" -- docker run --rm -v $P:/p -v $REF_RET:/ref sedv4 python3 /p/cmp.py /ref /p/v6.json
rc $L/closure-probes-repaired.json $REP "the repaired reference equals GNU sed 4.9 on every v6 probe" -- docker run --rm -v $P:/p -v $REF_REP:/ref sedv4 python3 /p/cmp.py /ref /p/v6.json
rc $L/closure-bracket-sweep-repaired.json $REP "348 bracket expressions: every pair of escape/letter range endpoints, negated and not, BRE and ERE, plus N-joined spaces; the repaired reference equals GNU on all" -- docker run --rm -v $P:/p -v $REF_REP:/ref sedv4 python3 /p/cmp.py /ref /p/bracket_sweep.json
rc $L/repro-coverage-returned.json $RET "cases in the returned roster exercising each v6 coverage class" -- python3 $R/rev5/coverage_scan.py $R/rev5/returned-tree
rc $L/closure-coverage-repaired.json $REP "the same scan over the repaired roster" -- python3 $R/rev5/coverage_scan.py workspace/tasks/tbrain-gnu-sed-reimplementation
rc $L/repro-instruction-returned.json $RET "the returned instruction lacks the clauses the v6 findings needed; the checker exits 1 when any is missing" -- python3 $R/rev5/instruction_clauses.py $R/rev5/returned-tree/instruction.md
rc $L/closure-instruction-repaired.json $REP "the repaired instruction states every clause" -- python3 $R/rev5/instruction_clauses.py workspace/tasks/tbrain-gnu-sed-reimplementation/instruction.md
rc $L/closure-departures-repaired.json $REP "the repaired reference and three alternative readings over the 562 matrix cases (rev5/roster_cmp.py in the verifier image): the reference and plus_closes (the manual's reading of +N/~N after n) differ from GNU on 0 cases, so nothing depends on that departure; q_keeps_append and s_keeps_hold fail, so the newly stated Q and -s rules are graded" -- python3 $R/rev5/summarize_mutants.py $R/rev5/matrix-cmp.json
rc $L/closure-departures-roster-repaired.json $REP "the same readings over the 1,217 non-new roster cases with the repaired reference: reference and plus_closes 0 differences" -- python3 $R/rev5/summarize_mutants.py $R/rev5/roster-departures.json
