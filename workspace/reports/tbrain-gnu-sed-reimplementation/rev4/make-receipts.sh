#!/bin/bash
# Writes the v4/v5 ledger receipts (probe, file-layout and coverage receipts).
set -u
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
cd "$ROOT"
R=workspace/reports/tbrain-gnu-sed-reimplementation
RET=cc25e2f5d5ad9b81834392e6feb525673026ac9942c80636336e6b7942b38d1b
REP=$1
L=$R/ledger-receipts-v4
P=$ROOT/$R/rev4/probe
REF_RET=$ROOT/$R/rev4/returned-tree/solution/pysed
REF_REP=$ROOT/workspace/tasks/tbrain-gnu-sed-reimplementation/solution/pysed
rc() { python3 $R/rev4/receipt.py "$@"; }
rc $L/repro-probes-returned.json $RET "the returned reference against GNU sed 4.9 on every probe the v4/v5 findings name: DIFF rows are reference defects, SAME rows are counterexamples to the finding" -- docker run --rm -v $P:/p -v $REF_RET:/ref sedv4 python3 /p/cmp.py /ref /p/all-probes.json
rc $L/repro-files-returned.json $RET "missing or empty files after a q: the returned reference eagerly opens every file" -- docker run --rm -v $P:/p -v $REF_RET:/ref sedv4 python3 /p/cmp.py /ref /p/files.json
rc $L/closure-probes-repaired.json $REP "the repaired reference equals GNU sed 4.9 on every probe the findings name; 1,2q is now rejected like GNU" -- docker run --rm -v $P:/p -v $REF_REP:/ref sedv4 python3 /p/cmp.py /ref /p/all-probes.json
rc $L/closure-files-repaired.json $REP "file layouts: 16 targeted cases plus a 378-case sweep of scripts x missing/empty-file layouts x -s/-n; the repaired reference equals GNU on all 394, including the q/Q-with-two-addresses scripts GNU rejects" -- docker run --rm -v $P:/p -v $REF_REP:/ref sedv4 sh -c "'python3 /p/cmp.py /ref /p/files.json; python3 /p/cmp.py /ref /p/files_sweep.json'"
rc $L/repro-coverage-returned.json $RET "cases in the returned roster that exercise each coverage class the panels named" -- python3 $R/rev4/coverage_scan.py $R/rev4/returned-tree
rc $L/closure-coverage-repaired.json $REP "the same scan over the repaired roster" -- python3 $R/rev4/coverage_scan.py workspace/tasks/tbrain-gnu-sed-reimplementation
rc $L/repro-disputed-coverage-returned.json $RET "the returned-roster cases that already exercise what v5 findings 31, 36 and 40 call untested" -- python3 $R/rev4/disputed_cases.py $R/rev4/returned-tree
rc $L/repro-mutants-returned.json $RET "panel-described wrong implementations (rev4/mut/*) run over the 704 returned cases by rev4/roster_cmp.py in the verifier image (docker run --rm -v \$R/rev4:/r sedv4 python3 /r/roster_cmp.py /r/returned-tree/tests/cases ...); every one but t_stale_after_n passes all 704" -- python3 $R/rev4/summarize_mutants.py $R/rev4/returned-roster-mutants.json
rc $L/closure-mutants-repaired.json $REP "the repaired reference, the two departure variants and the six wrong implementations over the 1,217 repaired cases (same command on workspace/tasks/.../tests/cases): the reference and both departure variants differ from GNU on 0 cases, every wrong implementation fails" -- python3 $R/rev4/summarize_mutants.py $R/rev4/repaired-roster-mutants.json
rc $L/repro-instruction-returned.json $RET "the returned instruction has none of the clauses the contract findings ask for (N at end of input, the numeric-range and T departures, bracket backslashes); the checker exits 1 when any is missing" -- python3 $R/rev4/instruction_clauses.py $R/rev4/returned-tree/instruction.md
rc $L/closure-instruction-repaired.json $REP "the repaired instruction states each of those clauses" -- python3 $R/rev4/instruction_clauses.py workspace/tasks/tbrain-gnu-sed-reimplementation/instruction.md
