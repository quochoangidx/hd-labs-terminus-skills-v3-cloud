"""revision-ledger.json for the v7 return."""
import json, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / ".agent/skills/terminus-regular-task-authoring/scripts"))
from revision_ledger_check import tree_hash  # noqa: E402
RET = ROOT / "workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v7/tbrain-gnu-ed-reimplementation"
REP = ROOT / "workspace/tasks/tbrain-gnu-ed-reimplementation"
CHANNEL = ("prepared in revision-v7/contest-note.md for #terminus-3-submissions; this environment cannot post to the "
           "channel, so the note must be posted by hand before the resubmission is judged")
DOMAIN_GATE = ("tests/scope.py, run at collection by tests/test_outputs.py::load_cases: collection fails if any committed or "
               "generated case uses an excluded option, command or suffix anywhere in its script, an argument starting "
               "with !, a missing FILE with a regular-file stdin, non-ASCII text, a NUL byte or a line over 200 bytes")

def wp(fid, axis, summary, mutant, witness, why, severity="Major"):
    return {"id": fid, "axis": axis, "severity": severity, "blocking": True, "summary": summary, "decision": "backed",
            "rationale": why, "reproduction": f"receipts/returned/{mutant}.json", "closure": f"../wrong-paths/{mutant}.json",
            "gate": {"rule": f"wrong path {mutant} must fail {witness}; revision-v7/evidence/coverage-map.json names the graded cases"}}

def domain(fid, axis, summary, why):
    return {"id": fid, "axis": axis, "severity": "Major", "blocking": True, "summary": summary, "decision": "backed",
            "rationale": why, "reproduction": "receipts/returned/out-of-domain-cases.json",
            "closure": "receipts/repaired/domain-check.json", "gate": {"rule": DOMAIN_GATE}}

DOM = ("Right, and my miss: the v6 scope scan ran an instrumented reference, so it only saw commands the reference "
       "reached, and these rows reach their l, z, x or y only on a pipe or not at all. Thirty-two committed rows named "
       "an excluded command or a missing FILE with a regular-file stdin; all are gone, the instruction now says the "
       "excluded commands never appear in a script, and the verifier refuses to collect a case that breaks any stated "
       "domain rule.")
F = [
 wp("1", "sound_verifier", "No case checks an input-mode text line near the 200-byte script-line limit.", "stdin-line-cap-199", "test_append_insert_change",
    "Real gap. Two cases type a 200-byte text line and a 200-byte command line; the instruction now says the limit counts the bytes before the newline."),
 wp("2", "sound_verifier", "Collating-element and equivalence-class brackets are verified only under basic regex mode.", "ere-no-collating", "test_regex_extended",
    "Real gap. An extended case uses [[.-.]] and [[=a=]]."),
 wp("3", "sound_verifier", "No case checks that an open-ended basic-regex repetition is rejected when its lower count exceeds 32767.", "open-interval-unchecked", "test_regex",
    "Real gap. y\\{32768,\\} and y{32768,} are now graded next to the accepted 32767 forms."),
 wp("4", "sound_verifier", "The repeat-substitution cases omit the r and p combination.", "repeat-rp-refused", "test_substitute",
    "Real gap. srp and spr are graded."),
 domain("5", "coherent_contract", "The verifier requires GNU behaviour for a nonexistent FILE under regular-file stdin.", DOM),
 domain("6", "coherent_contract", "The verifier requires the excluded l command to work.", DOM),
 domain("7", "coherent_contract", "The corpus contains the excluded l, z, x and y commands.", DOM),
 domain("8", "coherent_contract", "The verifier requires z.", DOM),
 {"id": "9", "axis": "coherent_contract", "severity": "Major", "blocking": True,
  "summary": "The verifier grades l print suffixes (generated.py S_REPEATS 'slxlyl').",
  "decision": "disputed",
  "rationale": "generated.py holds no slxlyl, and its S_REPEATS table holds no l. The one slxlyl in the corpus was a committed substitute case in which l is the s delimiter, not a suffix: GNU ed runs it as s with delimiter l, and tests/scope.py, which rejects the l suffix, accepts it. To end the misreading the row was removed anyway.",
  "reproduction": "receipts/returned/out-of-domain-cases.json", "counterexample": "receipts/returned/out-of-domain-cases.json",
  "contract_citation": {"file": "instruction.md", "anchor": "with the `n` and `p` suffixes and every `s` flag and form"},
  "contested_in_channel": CHANNEL, "gate": {"rule": DOMAIN_GATE}},
 domain("10", "coherent_contract", "The contract excludes l, but the verifier grades a script that executes l.", DOM),
 domain("11", "coherent_contract", "A graded mixed-script case reaches and requires l.", DOM),
 {"id": "12", "axis": "correct_reference_solution", "severity": "Major", "blocking": True,
  "summary": "The bracket parser treats a first-position hyphen as a range operator.", "decision": "disputed",
  "rationale": "Refuted by execution a second time, now on this finding's own scripts: on a file holding '.', g/[-a]/p prints only the byte count and s/[-a]/X/ prints ? in both GNU ed 1.19 and the returned reference. bracket() reads the leading - as an item before it looks for a range.",
  "reproduction": "receipts/returned/reference-findings-12-13-14.json", "counterexample": "receipts/returned/reference-findings-12-13-14.json",
  "contract_citation": {"file": "instruction.md", "anchor": "where the manual and the program disagree the program is what counts"},
  "contested_in_channel": CHANNEL, "gate": {"rule": "wrong path leading-hyphen-starts-range must fail test_regex"}},
]
for fid, summ in (("13", "I-suffixed literal regexes fold high-byte Latin-1 letters with Unicode rules."),
                  ("14", "Case-insensitive matching uses Unicode case folding instead of C-locale rules.")):
    F.append({"id": fid, "axis": "correct_reference_solution", "severity": "Major", "blocking": True, "summary": summ, "decision": "backed",
              "rationale": "Right: GNU ed selects nothing for g/\\xc9/I on a line holding \\xe9, and the returned reference selected it. posixre.py now folds only the ASCII letters, as glibc does in the C locale, and the instruction now says scripts are ASCII text too. An ASCII I case is graded; with scripts ASCII by contract, the Unicode folding cannot be told apart on a valid script, so the closure is the reference receipt against GNU ed on the finding's own byte script.",
              "reproduction": "receipts/returned/reference-findings-12-13-14.json", "closure": "receipts/repaired/reference-findings-12-13-14.json",
              "gate": {"rule": "tests/scope.py fails collection on any non-ASCII script or file; the case-folding table in posixre.py is ASCII-only"}})
for fid, summ in (("15", "A successful s leaves the pre-substitution line in the cut buffer."),
                  ("24", "The verifier never checks that a successful substitution copies its last modified line to the cut buffer.")):
    F.append({"id": fid, "axis": "correct_reference_solution" if fid == "15" else "sound_verifier", "severity": "Major", "blocking": True,
              "summary": summ, "decision": "disputed",
              "rationale": "The cut buffer is observable only through x (and y, which fills it), and the instruction says x and y never appear in a script. Both of the finding's scripts use x, which tests/scope.py rejects as outside the stated domain. No contract-valid script can tell the two cut-buffer contents apart, so the claim is outside what the task promises.",
              "reproduction": "receipts/returned/cut-buffer-scripts-out-of-domain.json", "counterexample": "receipts/returned/cut-buffer-scripts-out-of-domain.json",
              "contract_citation": {"file": "instruction.md", "anchor": "never appear in a script"},
              "contested_in_channel": CHANNEL, "gate": {"rule": DOMAIN_GATE}})
F += [
 wp("16", "sound_verifier", "Starting-file coverage does not distinguish a reader that splits a 200-byte line at byte 199.", "file-line-cap-199", "test_files_and_write",
    "Real gap. A starting file now holds a 200-byte line, printed, substituted and written back."),
 wp("17", "sound_verifier", "Script coverage does not exercise a legal 200-byte command line.", "stdin-line-cap-199", "test_append_insert_change",
    "Real gap. A 200-byte s command line is graded."),
 wp("18", "sound_verifier", "No case grows the buffer enough to reject a small fixed line-count limit.", "line-count-cap-4000", "test_delete_join_move_copy",
    "Real gap. Twelve doublings with t grow the buffer to 4096 lines."),
 wp("19", "sound_verifier", "The regex corpus never nests subexpressions deeper than two.", "nesting-depth-two", "test_regex",
    "Real gap. Three-deep nesting with back-references in the replacement, in basic and extended syntax."),
 domain("20", "sound_verifier", "The suite executes the out-of-scope l command.", DOM),
 domain("21", "sound_verifier", "The verifier supplies a nonexistent FILE with regular-file stdin.", DOM),
 {"id": "22", "axis": "sound_verifier", "severity": "Major", "blocking": True,
  "summary": "The native-code guard exempts standard-library native extension modules.", "decision": "backed",
  "rationale": "The finding read 'without loading native code' as covering the standard library's own compiled modules, which a pure standard-library program cannot avoid (the interpreter loads several at start-up). The rule meant native code outside the standard library, and that is what the guard enforces. The instruction now says so: 'Use only the Python standard library (its own compiled modules included), load no other native code'. The ordinary-program probe imports math to pin it.",
  "reproduction": "receipts/returned/guard-probes.json", "closure": "receipts/repaired/guard-probes.json",
  "gate": {"not_mechanizable": "whether a restriction's wording matches what its enforcer allows needs a reading of both; recorded in AGENTS.md section 2"}},
 wp("23", "sound_verifier", "The suite does not test backslash-newline continuation for e, E, f or r file parameters.", "filename-no-continuation", "test_files_and_write",
    "Real gap. One case continues the file parameter of r, f, E and e over two lines."),
 {"id": "25", "axis": "sound_verifier", "severity": "Minor", "blocking": True,
  "summary": "No targeted case observes whether W preserves an established default filename.", "decision": "disputed",
  "rationale": "Refuted by execution: the finding's wrong implementation (W makes its file the default filename) was scored against the returned verifier and failed test_generated_3 and test_generated_8, whose scripts W to other.txt and then write with a bare w, so the wrong default filename changes the files left behind. Two targeted cases were added anyway.",
  "reproduction": "receipts/returned/W-sets-default-filename.json", "counterexample": "receipts/returned/W-sets-default-filename.json",
  "contract_citation": {"file": "instruction.md", "anchor": "leave the same files with the same contents"},
  "contested_in_channel": CHANNEL, "gate": {"rule": "wrong path W-sets-default-filename must fail test_files_and_write"}},
]
F.sort(key=lambda r: int(r["id"]))
ledger = {"schema_version": 1, "task_slug": "tbrain-gnu-ed-reimplementation",
          "report_path": "workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v7/fc57838e-86e3-431c-a65c-b8776a1f307e.md",
          "returned_snapshot_sha256": tree_hash(RET), "repaired_snapshot_sha256": tree_hash(REP),
          "summary": ("25 blocking findings. Nine were one defect of mine: the v6 scope cut missed committed rows that name an excluded command or a missing FILE with a regular-file stdin. "
                      "They are gone, and collection now fails on any case outside the stated domain. Nine coverage findings are backed with cases and wrong paths, "
                      "the reference now folds case the C-locale way, and the restriction wording now matches what the guard allows. Findings 9, 12, 15, 24 and 25 are disputed with receipts."),
          "findings": F, "previous_findings": []}
(HERE / "revision-ledger.json").write_text(json.dumps(ledger, indent=1) + "\n")
import collections
print(len(F), collections.Counter(f["decision"] for f in F))
