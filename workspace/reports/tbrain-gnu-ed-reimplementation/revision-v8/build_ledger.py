"""revision-ledger.json for the v8 return."""
import json, sys, pathlib, collections
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / ".agent/skills/terminus-regular-task-authoring/scripts"))
from revision_ledger_check import tree_hash  # noqa: E402
RET = ROOT / "workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v8/tbrain-gnu-ed-reimplementation"
REP = ROOT / "workspace/tasks/tbrain-gnu-ed-reimplementation"
CHANNEL = ("prepared in revision-v8/contest-note.md for #terminus-3-submissions; this environment cannot post to the "
           "channel, so the note must be posted by hand before the resubmission is judged")
DOMAIN_GATE = ("tests/scope.py, run at collection by tests/test_outputs.py::load_cases: collection fails if any committed or "
               "generated case uses an excluded option, command, suffix or GNU escape, a % address, a file name starting with !, "
               "a missing FILE with a regular-file stdin, non-ASCII text, a NUL byte or a line over 200 bytes")

def wp(fid, summary, mutant, witness, why, severity="Major"):
    return {"id": fid, "axis": "sound_verifier", "severity": severity, "blocking": True, "summary": summary, "decision": "backed",
            "rationale": why, "reproduction": f"receipts/returned/{mutant}.json", "closure": f"../wrong-paths/{mutant}.json",
            "gate": {"rule": f"wrong path {mutant} must fail {witness}; revision-v8/evidence/coverage-map.json names the graded cases"}}

def static(fid, axis, summary, name, why, gate, severity="Major"):
    return {"id": fid, "axis": axis, "severity": severity, "blocking": True, "summary": summary, "decision": "backed",
            "rationale": why, "reproduction": f"receipts/returned/{name}.json", "closure": f"receipts/repaired/{name}.json",
            "gate": gate}

def dispute(fid, axis, summary, receipt, why, anchor, gate, severity="Major"):
    return {"id": fid, "axis": axis, "severity": severity, "blocking": True, "summary": summary, "decision": "disputed",
            "rationale": why, "reproduction": receipt, "counterexample": receipt,
            "contract_citation": {"file": "instruction.md", "anchor": anchor},
            "contested_in_channel": CHANNEL, "gate": gate}

F = [
 static("1", "sound_verifier", "The scope validator admits a graded script containing the excluded \\> escape.", "excluded-escapes",
    "Right. One committed row (mixed_scripts_6 row 9, ?a?,s/n\\>/&&/3g) survived the v6 removal of the GNU word escapes, because tests/scope.py never looked at escapes. scope.py now rejects any command line holding one of the ten excluded escapes and the row is gone. The flip was not reproduced: a submission that exits on any excluded escape scores 1 on the returned verifier as well (receipts/returned/excluded-escape-submission.json), because GNU ed and the candidate print the same bytes there. So no graded outcome depended on the row, but it broke the stated domain and the scope check missed it, which is the defect repaired.",
    {"rule": DOMAIN_GATE}),
 wp("2", "No graded k command carries a print suffix.", "k-suffix-ignored", "test_addresses",
    "Real gap. Two address cases use kap, kbn and $kapn on a pipe and on a regular-file stdin."),
 {"id": "3", "axis": "sound_verifier", "severity": "Major", "blocking": True,
  "summary": "The import guard admits vendored pure-Python code under /app although the contract says standard library only.",
  "decision": "dropped", "removed_obligation_id": "STDLIB-ONLY-DELIVERED-CODE",
  "rationale": "The rule is there so a submission cannot hand the work to a real ed or to native code. Whether a delivered pure-Python file was written or vendored cannot be observed, and it does not change what the task tests. The instruction now says what the guard checks: 'Import only the Python standard library (its own compiled modules included) and Python source files under /app'. The guard no longer refuses an /app path just because it has a site-packages component (receipts/*/delivered-imports.json).",
  "reproduction": "receipts/returned/delivered-imports.json", "closure": "receipts/repaired/delivered-imports.json",
  "gate": {"not_mechanizable": "whether a restriction's wording matches what its enforcer can observe needs a reading of both; recorded in AGENTS.md section 2"}},
 wp("4", "BRE bounded repeats, \\? and \\+ are not checked on a grouped operand.", "group-interval-refused", "test_regex",
    "Real gap. Basic cases apply \\{2\\}, \\{1,\\}, \\{2,3\\}, \\+ and \\? to groups, nested groups included, with extended twins. Both group mutants (group-interval-refused and group-plus-optional-refused) fail test_regex."),
 wp("5", "No FILE argument contains an internal space.", "filename-first-word", "test_files_and_write",
    "Real gap. w, r, W, e and f take names with an inner space, a double space and a leading extra blank; the files are compared."),
 wp("6", "Basic-regex backreferences \\5 to \\8 are not graded.", "backref-5-8-refused", "test_regex",
    "Real gap. g and v select lines with \\5, \\6, \\7 and \\8 in basic syntax, and \\5 to \\8 in extended syntax."),
 wp("7", "No graded case applies a basic bounded repetition to a parenthesized subexpression.", "group-interval-refused", "test_regex",
    "Real gap; same cases as finding 4."),
 static("8", "coherent_contract", "The verifier grades s!a!b!p although no command argument may start with !.", "bang-argument",
    "Right: the sentence covered more than it meant. The rule is about file names that would run a shell command. The instruction now says 'no file name, on the command line or after a command, starts with `!`', which is what scope.py checks, and s with ! as its delimiter stays graded.",
    {"rule": DOMAIN_GATE}),
 dispute("9", "correct_reference_solution", "The bracket parser treats a first-position hyphen as a range endpoint.", "receipts/returned/reference-findings-9-10.json",
    "Refuted by execution for the third round, now on this finding's own script: with a file holding 0, -s and a regular-file stdin, 1s/[-a]/X/p gives ?, status 1, file unchanged in both GNU ed 1.19 and the returned reference. g/[-a]/p on 0, - and a prints - and a in both. bracket() reads the leading - as an item before it looks for a range.",
    "where the manual and the program disagree the program is what counts", {"rule": "wrong path leading-hyphen-starts-range must fail test_regex"}),
 dispute("10", "correct_reference_solution", "1m1 is a no-op, but the reference sets modified so q fails.", "receipts/returned/reference-findings-9-10.json",
    "Refuted by execution: GNU ed 1.19 marks the buffer modified after 1m1 (and after 1,2m2). With f holding x and a pipe, 1m1 then q prints 2, ?, exits 1 and leaves f unchanged in both GNU ed and the returned reference. The expected result comes from the program, not the reading.",
    "Every expected result comes from running GNU ed 1.19 itself", {"rule": "every expected result is GNU ed 1.19's own output at test time"}),
 wp("11", "The verifier never tests basic \\? or \\+ applied to a parenthesized subexpression.", "group-plus-optional-refused", "test_regex",
    "Real gap; see finding 4."),
 static("12", "coherent_contract", "The generated grammar requires the % address, which the manual never defines.", "percent-address",
    "Right: 138 generated scripts used %. It is gone from the grammar, scope.py rejects a % address, and nothing in the task now relies on it.",
    {"rule": DOMAIN_GATE}, severity="Minor"),
 wp("13", "No case distinguishes a four-slot address parser from an unbounded tuple.", "four-address-slots", "test_addresses",
    "Real gap. 1,2,3,4,5p, 1;2;3;4;5;6n and 3,4,5,6,1,2p are graded.", severity="Minor"),
 static("14", "sound_verifier", "The audit hook does not stop SQLite's extension loading.", "sqlite-extension",
    "Right. The hook now stops sqlite3.enable_load_extension and sqlite3.load_extension, and a probe program, guardcheck/sqlite_ext.py, is in test_launcher_stops_delegation_and_foreign_code. On the returned guard the probe enables loading and exits 0; on the repaired guard it stops with status 120.",
    {"rule": "test_launcher_stops_delegation_and_foreign_code runs guardcheck/sqlite_ext.py and expects status 120"}, severity="Minor"),
 dispute("15", "sound_verifier", "A fixed roster and seeded generator permit a verifier-specific lookup submission.", "receipts/returned/lookup-table-inputs.json",
    "The inputs to such a table live only in the verifier image: the agent image holds the stub and the two manuals, with no case, roster, generator or seed (receipt). Building the table means reading hidden tests, and any finite hidden suite admits that. A seed drawn at grading time would make an imperfect submission's reward vary from run to run, which the determinism axis rejects.",
    "It will be checked that way with many command scripts", {"rule": "tests/ never enters the agent image (environment/Dockerfile copies app/ only)"}, severity="Minor"),
]
F.sort(key=lambda r: int(r["id"]))
ledger = {"schema_version": 1, "task_slug": "tbrain-gnu-ed-reimplementation",
          "report_path": "workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v8/fc57838e-86e3-431c-a65c-b8776a1f307e.md",
          "returned_snapshot_sha256": tree_hash(RET), "repaired_snapshot_sha256": tree_hash(REP),
          "summary": ("15 blocking findings. Seven coverage gaps are backed with cases and wrong paths. Three contract/scope findings are backed: an excluded escape the scope check missed, "
                      "a ! rule worded too widely, and % in the grammar. The SQLite extension route is closed, and the stdlib-only promise for delivered code is dropped. Findings 9, 10 and 15 are disputed with receipts."),
          "findings": F, "previous_findings": []}
(HERE / "revision-ledger.json").write_text(json.dumps(ledger, indent=1) + "\n")
print(len(F), collections.Counter(f["decision"] for f in F))
