# Writes workspace/reports/<slug>/revision-ledger.json for the v5 return (v4 findings carried as previous).
import json
R = "workspace/reports/tbrain-gnu-sed-reimplementation"
RET = "cc25e2f5d5ad9b81834392e6feb525673026ac9942c80636336e6b7942b38d1b"
REP = open(f"{R}/rev4/repaired-snapshot.txt").read().strip()
L = "ledger-receipts-v4/"
CHANNEL = "NOT YET POSTED: draft in rev4/contest-draft.md; the author must post it in #terminus-3-submissions"
CC, RS, SV = "coherent_contract", "correct_reference_solution", "sound_verifier"
MATRIX_GATE = {"rule": "rev4/coverage_scan.py (per-clause coverage classes) and rev4/roster_cmp.py + summarize_mutants.py (panel-described wrong implementations must pass nowhere); task-level, re-run on every roster change"}
NM_COVER = {"not_mechanizable": "whether every enumerated clause of a free-text contract has a discriminating case needs judgement; recorded as a known exposure in AGENTS.md section 6 (sed bullet, item 6)"}

def backed(fid, axis, sev, why, repro, closure, gate=MATRIX_GATE):
    return {"id": fid, "axis": axis, "severity": sev, "blocking": True, "decision": "backed", "rationale": why,
            "reproduction": L + repro, "closure": L + closure, "gate": gate}

def disputed(fid, axis, sev, why, anchor, counter, gate):
    return {"id": fid, "axis": axis, "severity": sev, "blocking": True, "decision": "disputed", "rationale": why,
            "contract_citation": {"file": anchor[0], "anchor": anchor[1]}, "counterexample": L + counter,
            "contested_in_channel": CHANNEL, "gate": gate}

ESC = "backed: the returned roster had no \\a, \\f, \\r or \\v anywhere (coverage scan: 0 cases), and a reference with \\r left literal passed all 704 returned cases; the matrix family matrix_escapes now puts each of the six escapes in the replacement, regex, bracket, address and multi-line and one-line a/i/c text, and the same wrong implementation fails 19 repaired cases"
TEXT = "backed by removing the ambiguity: the y, l and I the finding cites were never commands but text of a multi-line i\\ / c\\ or one-line a (GNU sed takes the rest of the line as text, so they are never run and the returned reference, which rejects y/l/I, still matched GNU on all 704 cases); six such texts are reworded to use only covered commands (y/abc/xyz/ -> s/abc/xyz/, l -> p, /ab/I -> /ab/), so no graded script contains anything that reads as an excluded feature (coverage scan: 6 -> 0)"
EAGER = "backed, real reference defect: the returned reference read every named file before running the script, so a missing file after the one on which q/Q stops set status 2 over the q code (q42 f missing: GNU 42, returned reference 2). sed.py's Input now opens a file only when the next line is needed or when $, n or N asks whether input is left, as GNU does; 394 file-layout probes and matrix_quit's never-reached-missing-file cases match GNU, and the eager reader fails 15 repaired cases"
findings = [
    backed("v5-1", SV, "Major", ESC, "repro-mutants-returned.json", "closure-mutants-repaired.json"),
    backed("v5-2", SV, "Major", ESC, "repro-mutants-returned.json", "closure-mutants-repaired.json"),
    backed("v5-3", SV, "Major", ESC, "repro-mutants-returned.json", "closure-mutants-repaired.json"),
    backed("v5-4", SV, "Major", ESC, "repro-coverage-returned.json", "closure-coverage-repaired.json"),
]
for n in (5, 6, 7, 8, 9, 10, 11, 12, 14):
    findings.append(backed(f"v5-{n}", CC, "Major", TEXT, "repro-coverage-returned.json", "closure-coverage-repaired.json",
                           {"rule": "rev4/coverage_scan.py class aic_text_reading_like_y_l_I must be 0 (the reference parser extracts a/i/c text and the scan flags y/, a lone l or w/r/e, and /re/I or /re/M inside it)"}))
findings.append(backed("v5-13", CC, "Major", "backed: the manual's summary (\"exits without processing\") and its N entry (GNU does not terminate, prints the pattern space) disagree; the instruction now says that with POSIXLY_CORRECT unset, N with no next line ends the cycle there and prints the pattern space unless -n, as the N entry says, which is what GNU does (checked with and without -s)",
                       "repro-instruction-returned.json", "closure-instruction-repaired.json",
                       {"not_mechanizable": "spotting an internal contradiction in a shipped manual needs reading; recorded in AGENTS.md section 6"}))
BR = ("disputed: the reference already equals GNU sed 4.9 here, and both follow the manual. Section 5.5 says the backslash is not special inside a bracket expression "
      "except for the section 5.8 escapes, so [\\w] matches backslash or w, [\\s] backslash or s, [\\]] is the class {\\} followed by a literal ], and [\\/] matches backslash or /; [\\t] is a tab in both. "
      "The instruction now says so in one clause (\\w..\\> outside bracket expressions; the section 5.8 escapes inside them too; any other backslash inside one is ordinary)")
for n in (15, 17, 19, 23, 26):
    findings.append(disputed(f"v5-{n}", RS, "Major", BR, ("instruction.md", "inside a bracket expression any other backslash is an ordinary character"),
                             "repro-probes-returned.json", {"not_mechanizable": "which bracket escapes a regex dialect honours is a semantic reading of the manual; the probes are kept as regression rows in rev4/probe/all-probes.json"}))
for n in (16, 18, 21, 22):
    findings.append(backed(f"v5-{n}", RS, "Major", EAGER, "repro-probes-returned.json", "closure-files-repaired.json",
                           {"rule": "matrix_quit cases with a missing file after the quitting line, and wrong path files-opened-before-the-run (wrong-paths/files-opened-before-the-run.json)"}))
findings.append(backed("v5-20", RS, "Major", "backed as a contract gap: GNU sed 4.9 starts a numeric-first-address range on the first line it sees at or past the number (1{n;n};2,4p prints 3 and 4), which the manual does not describe; the reference follows GNU. The instruction now lists this among the places where GNU departs from its manual and nothing is checked, and a manual-reading variant (ln == addr1 exactly) matches GNU on all 1,217 repaired cases, so no graded case depends on it",
                       "repro-instruction-returned.json", "closure-mutants-repaired.json",
                       {"rule": "departure variants over the whole roster: rev4/mut/num_exact and rev4/mut/t_keeps must differ from GNU on 0 cases (closure-mutants-repaired.json)"}))
findings.append(backed("v5-24", RS, "Major", "backed as a contract gap: GNU sed 4.9 clears the substitution flag on a T that does not branch (the finding's script prints NO under GNU, as under the reference); the manual does not say so. Listed in the instruction as a departure that is not checked; the variant that keeps the flag matches GNU on all 1,217 repaired cases",
                       "repro-instruction-returned.json", "closure-mutants-repaired.json",
                       {"rule": "departure variants over the whole roster: rev4/mut/t_keeps must differ from GNU on 0 cases"}))
findings.append(disputed("v5-25", RS, "Major", "disputed: `b x; /a/p; :x; s//X/` is not a script GNU sed 4.9 runs; it exits 1 (no previous regular expression) exactly as the reference does, so the empty regex is resolved at run time in both. The instruction says scripts never fail, so this input is outside the graded domain",
                         ("instruction.md", "Scripts never fail and always finish"), "repro-probes-returned.json",
                         {"not_mechanizable": "outside-domain claims are answered by the GNU probe, kept in rev4/probe/v5.json"}))
findings.append(backed("v5-27", SV, "Major", "backed: no returned case put a range on a block (scan 0); a reference that keeps a block's range open only on its first line passed all 704 returned cases and fails 20 repaired ones (matrix_blocks: twelve address forms on { } with and without !, and } followed by more commands)",
                       "repro-mutants-returned.json", "closure-mutants-repaired.json"))
findings.append(backed("v5-28", SV, "Major", "backed: no returned s combined a number with g and p (scan 0), and a parser that ignores a number after g passed all 704; matrix_s_flags runs every order of g, p and 2/3 (and 12g, g12, 4p) with and without -n, and that parser fails 16 repaired cases",
                       "repro-mutants-returned.json", "closure-mutants-repaired.json"))
findings.append(backed("v5-29", SV, "Major", ESC, "repro-mutants-returned.json", "closure-mutants-repaired.json"))
for n in (30, 32, 34, 39):
    findings.append(backed(f"v5-{n}", SV, "Major", TEXT, "repro-coverage-returned.json", "closure-coverage-repaired.json",
                           {"rule": "rev4/coverage_scan.py class aic_text_reading_like_y_l_I must be 0"}))
findings.append(disputed("v5-31", SV, "Major", "disputed: the returned roster already graded $ in a multi-line pattern space: branching_and_t_flag runs `s/e/E/;N;tx;s/$/ nx/;b;:x;s/$/ x/` over eight lines, where an engine that also matched $ before the embedded newline would insert the text after the first line. matrix_anchors adds eleven more (N;s/$/E/g, ERE/BRE anchors in groups and alternatives) regardless",
                         ("instruction.md", "the operators of sections 5.3 and 5.4"), "repro-disputed-coverage-returned.json",
                         {"not_mechanizable": "whether an existing case is discriminating for a claimed gap needs reading the case"}))
findings.append(backed("v5-33", SV, "Major", "backed: no returned q/Q had a multi-digit code (scan 0) and a one-digit parser passed all 704; matrix_quit runs q and Q with 0, 1, 5, 42, 100 and 255, with addresses, after a/i text and with never-reached missing files, and that parser fails 22 repaired cases",
                       "repro-mutants-returned.json", "closure-mutants-repaired.json"))
findings.append(backed("v5-35", SV, "Major", "backed: the only returned case with high group numbers used \\9\\8\\1, so \\4-\\7 were never put into a replacement (scan: 0 cases with \\4-\\7); matrix_groups now puts each of \\1-\\9 into a replacement in BRE and ERE, with & and \\& beside them",
                       "repro-coverage-returned.json", "closure-coverage-repaired.json"))
findings.append(disputed("v5-36", SV, "Major", "disputed: the returned roster already had a BRE exact interval, step_and_regex_addresses `/^.\\{5\\}$/p`, which selects exactly the five-letter lines; matrix_intervals adds \\{2\\}, \\{2,\\}, \\{1,3\\}, \\{0,1\\}, \\{0\\}, \\{3,3\\} on single characters and groups in both dialects regardless",
                         ("instruction.md", "the operators of sections 5.3 and 5.4"), "repro-disputed-coverage-returned.json",
                         {"not_mechanizable": "whether an existing case is discriminating for a claimed gap needs reading the case"}))
findings.append(backed("v5-37", SV, "Major", "backed: no returned address used \\W, \\S, \\b, \\B, \\< or \\> (scan 0); matrix_regex_escapes puts each of the eight in s, in single addresses, negated addresses and ranges, in BRE and ERE (38 address cases)",
                       "repro-coverage-returned.json", "closure-coverage-repaired.json"))
findings.append(backed("v5-38", SV, "Major", "backed: as v5-35, \\4-\\7 had no returned case; matrix_groups covers each group number", "repro-coverage-returned.json", "closure-coverage-repaired.json"))
findings.append(disputed("v5-40", SV, "Major", "disputed: four returned cases put ; right after } (hold_space `1{h;d};G;s/\\n/ /;h;$!d` and `$!{h;d};x;G`, branching `1{N;s/a/A/;D};t ok;...`), so a parser that rejects `};` failed them; matrix_blocks adds more regardless",
                         ("instruction.md", "`{` `}` blocks"), "repro-disputed-coverage-returned.json",
                         {"not_mechanizable": "whether an existing case is discriminating for a claimed gap needs reading the case"}))
findings.append(backed("v5-41", RS, "Minor", "backed, real reference defect: `1,2q` was accepted; GNU rejects a q or Q with two addresses (exit 1). The parser now raises for them, and the file-layout sweep that includes `2,$q12`-style scripts matches GNU on all 394",
                       "repro-probes-returned.json", "closure-probes-repaired.json",
                       {"not_mechanizable": "which commands take how many addresses is per-command manual knowledge; the probe stays in rev4/probe/v5.json"}))
findings.append(backed("v5-42", SV, "Minor", "backed: every returned 0,/re/ case either matched on line 1 or never matched, so none ended the range on a later line; matrix_ranges adds 0,/c/d, 0,/c/s/^/>/, 0,/b/{p} and the 1,/re/ counterparts",
                       "repro-coverage-returned.json", "closure-coverage-repaired.json"))
findings.append(backed("v5-43", SV, "Minor", "backed: no returned s used a digit as delimiter (scan 0); matrix_delimiters adds s1a1X1 and fourteen other s and address delimiters, including escaped delimiters inside brackets",
                       "repro-coverage-returned.json", "closure-coverage-repaired.json"))

prev_groups = [
    ("v4-4..12,30,34,38,40", "y/l/I in graded scripts: answered as v5-5..14 (text reworded; they were never commands)"),
    ("v4-13,14,15,17,23", "bracket escapes and leading hyphen: the reference equals GNU and section 5.5 ([-a] was already literal); disputed as v5-15/17/19/23/26, contract clause added"),
    ("v4-16,19", "numeric range start after n: answered as v5-20 (listed as a GNU departure, no case depends on it)"),
    ("v4-18,20,21", "eager file opening overriding q/Q codes: real defect, fixed as v5-16/18/21/22"),
    ("v4-22", "s with a backslash delimiter and an escaped backslash in the replacement: GNU sed itself exits 1 on that script (probe f22), so it is outside 'scripts never fail'; not changed"),
    ("v4-37", "ERE `b|^a`: the manual (section 5.3, inherited by 5.4) makes ^ an anchor after | or (; the instruction now says the unchecked departure is ^/$ anywhere else in an ERE, so the case stays"),
    ("v4-1,2,3,24,25,26,27,28,29,31,32,33,35,36,39,41", "coverage gaps (q42, T after n/N, g2 and other flag orders, range on {, \\a\\f\\r\\v, - beside a file, append flushed by N, more than 32 lines): all covered by the rev4 matrix; the panel-described wrong implementations fail it (closure-mutants-repaired.json)"),
    ("v4-42,43", "guard: /app is now chowned root and go-w before any candidate runs, and the audit hook also blocks native extension modules loaded from outside Python's lib-dynload"),
]
ledger = {
    "schema_version": 1,
    "task_slug": "tbrain-gnu-sed-reimplementation",
    "report_path": "workspace/revision/12e6eda4-8ced-4dcd-928d-7abc22b133a9/v5/12e6eda4-8ced-4dcd-928d-7abc22b133a9.md",
    "returned_snapshot_sha256": RET,
    "repaired_snapshot_sha256": REP,
    "note": "v4 and v5 both judged the rev3 bytes (digest cc25e2f5, the v3 ledger's repaired snapshot). No repair reached the platform between them, so the v4 findings are carried as previous_findings and answered in the same batch. Disputed rows are NOT yet posted to #terminus-3-submissions; see rev4/contest-draft.md.",
    "findings": findings,
    "previous_findings": [{"id": i, "status": "still_open", "response": r} for i, r in prev_groups],
}
json.dump(ledger, open(f"{R}/revision-ledger.json", "w"), indent=1)
print(len(findings), "findings")
