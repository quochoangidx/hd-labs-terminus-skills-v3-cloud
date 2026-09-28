# Writes workspace/reports/<slug>/revision-ledger.json for the v6 return.
import json
R = "workspace/reports/tbrain-gnu-sed-reimplementation"
RET = "e93b54684a98ae665ddee8c273ebc90ec9ca2ba26de574867ae9b2a754105d8e"
REP = open(f"{R}/rev5/repaired-snapshot.txt").read().strip()
L = "ledger-receipts-v6/"
CC, RS, SV = "coherent_contract", "correct_reference_solution", "sound_verifier"
def row(fid, axis, sev, why, repro, closure, gate):
    return {"id": fid, "axis": axis, "severity": sev, "blocking": True, "decision": "backed", "rationale": why,
            "reproduction": L + repro, "closure": L + closure, "gate": gate}
COV = {"rule": "rev5/coverage_scan.py classes must be non-zero on every roster change (task-level)"}
STATED = {"not_mechanizable": "which open points of a manual the binary settles, and how, needs a reading plus a GNU probe; recorded in AGENTS.md section 6 (sed bullet)"}
BR = ("backed, real reference defect: posixre.py decoded \\n only as a bracket range's lower end, so [\\t-\\n] and [\\n-\\n] took the backslash as the upper end "
      "and matched A (GNU: tab..newline only). The upper end is now decoded too; a 348-case sweep of escape/letter range endpoints matches GNU, "
      "matrix_brackets adds ranges ending in \\n, \\r, \\t and \\a, and the old parser (wrong path bracket-range-end-newline-literal) fails test_matrix_brackets")
F = [
    row("v6-1", SV, "Major", "backed: no returned case ran a command after q/Q in the same cycle (scan 0); matrix_quit adds q;p, Q;p, 2q;p, $q;=, 2{p;q};p and /b/Q;p", "repro-coverage-returned.json", "closure-coverage-repaired.json", COV),
    row("v6-2", RS, "Major", "backed as a contract gap: GNU sed 4.9 also drops text queued by a when Q quits (-e 'a hello' -e Q prints nothing), as the reference does; the manual only says Q does not print the pattern space. The instruction now says Q drops queued a text as well, and the reading that flushes it fails 3 matrix cases", "repro-instruction-returned.json", "closure-departures-repaired.json", STATED),
    row("v6-3", RS, "Major", "backed as a contract gap: GNU sed 4.9 starts every -s file with an empty hold space (/a/h;2g on 'a' and 'b c' prints a, b and an empty line), as the reference does; the manual's -s entry does not mention hold space. The instruction now states it, and the reading that keeps the hold space fails 2 matrix cases (matrix_files -s cases)", "repro-instruction-returned.json", "closure-departures-repaired.json", STATED),
    row("v6-4", RS, "Major", "backed as a contract gap: GNU sed 4.9 keeps an addr1,+N range open after N reads past its end (1,+1p;1N prints a and c), as the reference does, which the manual does not describe. Listed in the instruction as a departure that is not checked; the manual's reading (plus_closes) differs from GNU on 0 of 1,266 cases", "repro-instruction-returned.json", "closure-departures-roster-repaired.json", {"rule": "departure variants over the whole roster must differ from GNU on 0 cases (rev5/mut/plus_closes)"}),
    row("v6-5", RS, "Major", BR, "repro-probes-returned.json", "closure-bracket-sweep-repaired.json", {"rule": "wrong path bracket-range-end-newline-literal (wrong-paths/bracket-range-end-newline-literal.json) and rev5/probe/bracket_sweep.json"}),
    row("v6-6", RS, "Major", "backed as v6-3: GNU empties the hold space per -s file; now stated in the instruction and graded", "repro-instruction-returned.json", "closure-departures-repaired.json", STATED),
    row("v6-7", RS, "Major", "backed as v6-4 (1,+1p;n;n and 1,~2p;n;n print 1 and 4 under GNU as under the reference); listed as not checked, no case depends on it", "repro-instruction-returned.json", "closure-departures-roster-repaired.json", {"rule": "rev5/mut/plus_closes must differ from GNU on 0 cases"}),
    row("v6-8", RS, "Major", BR, "repro-probes-returned.json", "closure-probes-repaired.json", {"rule": "wrong path bracket-range-end-newline-literal"}),
    row("v6-9", RS, "Major", "backed as a contract gap: GNU sed 4.9 returns 2, not 42, for q42 after an unreadable file was reached (q42 missing good -> x, status 2), as the reference does; the manual lists status 2 and the q code without saying which wins. The instruction now says 2 wins once an unreadable named file was reached; matrix_quit has 17 such cases", "repro-instruction-returned.json", "closure-instruction-repaired.json", STATED),
    row("v6-10", RS, "Major", "backed as a contract gap: GNU sed 4.9 exits 1 on 2,/x/p; //p (no previous regular expression), as the reference does, because // repeats the last regex *used at run time*; the panel read it as the preceding regex in the script. The instruction now says so, which also puts such scripts outside 'scripts never fail'", "repro-probes-returned.json", "closure-instruction-repaired.json", STATED),
    row("v6-11", RS, "Major", BR, "repro-probes-returned.json", "closure-probes-repaired.json", {"rule": "wrong path bracket-range-end-newline-literal"}),
    row("v6-12", SV, "Minor", "backed: the returned t x ; and T x ; cases never took the branch; matrix_t_flag adds taken t/T/b branches to labels followed by spaces before ;, and labels with spaces around them", "repro-coverage-returned.json", "closure-coverage-repaired.json", COV),
    row("v6-13", SV, "Minor", "backed: the returned guard left the verifier image's site-packages on sys.path, so a candidate could import pytest's dependencies; the wrong path imports-verifier-package (imports pluggy on -E scripts) got reward 1 from the returned verifier. The candidate now runs with python3 -S and site-packages stripped from sys.path, and the same wrong path fails test_matrix_intervals", "repro-imports-verifier-package-returned.json", "closure-coverage-repaired.json", {"rule": "wrong path imports-verifier-package (wrong-paths/imports-verifier-package.json)"}),
    row("v6-14", SV, "Minor", "backed: no returned case used ~ as a delimiter (scan 0); matrix_delimiters adds ~, =, ^, . and & for both addresses and s", "repro-coverage-returned.json", "closure-coverage-repaired.json", COV),
]
ledger = {
    "schema_version": 1, "task_slug": "tbrain-gnu-sed-reimplementation",
    "report_path": "workspace/revision/12e6eda4-8ced-4dcd-928d-7abc22b133a9/v6/12e6eda4-8ced-4dcd-928d-7abc22b133a9.md",
    "returned_snapshot_sha256": RET, "repaired_snapshot_sha256": REP,
    "note": "v6 judged rev4 (digest e93b5468): 14 blocking findings, down from 43, with coherent_contract, protected_ground_truth and deterministic_execution clean. One real reference defect (\\n as a bracket range's upper end); five GNU-settled points the manual leaves open are now stated or listed as unchecked; the rest are coverage and the site-packages guard.",
    "findings": F,
    "previous_findings": [
        {"id": "v5-15,17,19,23,26", "status": "closed", "response": "bracket backslash disputes: not raised in v6 after rev4's clause; the contest draft (rev4/contest-draft.md) is no longer needed for them"},
        {"id": "v5-25", "status": "still_open", "response": "re-raised as v6-10; answered by stating that // repeats the last regex used at run time"},
        {"id": "v5-31,36,40", "status": "closed", "response": "coverage disputes not raised in v6"},
    ],
}
json.dump(ledger, open(f"{R}/revision-ledger.json", "w"), indent=1)
print(len(F), "findings")
