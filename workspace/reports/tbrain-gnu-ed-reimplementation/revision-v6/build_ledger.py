"""Write revision-ledger.json for the v6 return: one row per numbered finding."""
import json, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / ".agent/skills/terminus-regular-task-authoring/scripts"))
from revision_ledger_check import tree_hash  # noqa: E402
RET = ROOT / "workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v6/tbrain-gnu-ed-reimplementation"
REP = ROOT / "workspace/tasks/tbrain-gnu-ed-reimplementation"
CHANNEL = ("prepared in revision-v6/contest-note.md for #terminus-3-submissions; this environment cannot post "
           "to the channel, so the note must be posted by hand before the resubmission is judged")
NOT_MECH_SCOPE = ("the class is an open-ended contract ('everything the manual describes') graded by a finite corpus: "
                  "whether a promise is core and backed needs semantic judgement, and a phrase match would judge one "
                  "spelling; recorded in AGENTS.md section 2 as a known exposure (grep and dc instructions share the wording)")

def dropped(fid, summary, ob, why):
    return {"id": fid, "axis": "sound_verifier", "severity": "Major", "blocking": True, "summary": summary,
            "decision": "dropped", "removed_obligation_id": ob, "rationale": why,
            "gate": {"not_mechanizable": NOT_MECH_SCOPE}}

def backed(fid, summary, wp, why, witness):
    return {"id": fid, "axis": "sound_verifier", "severity": "Major", "blocking": True, "summary": summary,
            "decision": "backed", "rationale": why,
            "reproduction": f"receipts/returned/{wp}.json", "closure": f"../wrong-paths/{wp}.json",
            "gate": {"rule": f"wrong path {wp} must fail {witness}; revision-v6/evidence/coverage-map.json names the "
                             "graded cases, and generated.py fails collection if any grammar entry is drawn fewer than three times"}}

def disputed(fid, summary, why, extra_gate):
    return {"id": fid, "axis": "correct_reference_solution", "severity": "Major", "blocking": True, "summary": summary,
            "decision": "disputed", "rationale": why,
            "reproduction": "receipts/returned/reference-findings-3-4-5-6.json",
            "counterexample": "receipts/returned/reference-findings-3-4-5-6.json",
            "contract_citation": {"file": "instruction.md", "anchor": "where the manual and the program disagree the program is what counts"},
            "contested_in_channel": CHANNEL, "gate": {"rule": extra_gate}}

F = []
F.append(dropped("1", "No option case checks that -p consumes a hyphen-leading next argument as its prompt string.",
    "PROMPT-AND-OTHER-OPTIONS", "Real gap, but -p is invocation surface, not the editor the task tests. The instruction now names -E, -l and -s as the only options, each a single letter; -p, -q, -r, P and long spellings left with their cases."))
F.append(dropped("2", "The corpus never applies the list command to a line long enough to exercise GNU ed's list-output wrapping.",
    "LIST-COMMAND", "Real gap. l is output formatting (escapes, column wrapping), not editor state, and it drew findings in v1, v2 and now v6. The instruction now says l and the l suffix are never used; the committed and generated cases hold none (scope scan in evidence/)."))
F.append(disputed("3", "The bracket parser interprets a hyphen in the first position as the lower endpoint of a range instead of a literal character.",
    "Refuted by execution: on the finding's own script GNU ed 1.19 and the returned reference both print a (and a then - once - is in the buffer), exit 0, byte for byte. bracket() consumes the leading - as an item before looking for a range. Pinned now by two regex cases, and wrong path leading-hyphen-starts-range shows the verifier rejects the misreading the finding describes.",
    "wrong path leading-hyphen-starts-range must fail test_regex"))
r4 = disputed("4", "A substitution with no match returns success inside a global command list, bypassing the global list's first-error stop.",
    "Refuted by execution as a reference defect: with -s and regular-file stdin GNU ed 1.19 prints nothing and exits 0 on the finding's script, exactly as the reference does; outside a global command the same s fails in both. The finding did expose a real contract gap: the manual calls a substitution without a match an error, and the errata did not say the program departs from that inside a global list. Errata entry 18 now says it, three global_commands cases pin it, and wrong path global-s-without-match-fails is rejected.",
    "errata-map entry 18 names its graded cases (check_coverage_map.py); wrong path global-s-without-match-fails must fail test_global_commands")
F.append(r4)
F.append(dropped("5", "The reference does not accept GNU ed's documented long option spellings, including --prompt=STRING.",
    "PROMPT-AND-OTHER-OPTIONS", "Right about the reference (receipt row F5: GNU prints X and exits 0, the reference rejects the argument). Rather than implement GNU's long-option parser for an option the task does not need, the instruction now allows only -E, -l and -s, each a single letter after one hyphen, so no long spelling is in scope.")
    | {"axis": "correct_reference_solution", "reproduction": "receipts/returned/reference-findings-3-4-5-6.json"})
F.append(disputed("6", "Unset apostrophe marks resolve to address 0 even after the buffer becomes nonempty.",
    "Refuted by execution: on the finding's script both GNU ed 1.19 and the returned reference print ? and exit non-zero. get_line_node_addr returns -1 for an unset mark on a non-empty buffer, so the Invalid address path runs. Errata entry 1 already states this; two address cases now pin both the empty and the non-empty buffer.",
    "errata-map entry 1 names its graded cases; revision-v6/evidence/coverage-map.json finding 6"))
F.append(dropped("7", "The corpus never exercises a line near the permitted 100000-byte length, so a plausible 81920-byte input cap passes.",
    "LONG-LINES", "Real gap against the old bound. A line-length limit says nothing about ed semantics, so the bound is now 200 bytes for starting files and scripts, well inside every plausible cap."))
F.append(dropped("8", "No case joins a still-remembered unterminated line as the last component.", "BINARY-FILES",
    "Real gap. This is the fourth round in which the binary-file newline state drew a Major; it is a corner of io.c, not the editor model. Starting files are now NUL-free text whose every line ends with a newline, and the binary cases left the corpus."))
F.append(dropped("9", "The corpus never reads an unterminated NUL-free file into an already-text buffer.", "BINARY-FILES",
    "Real gap; out of scope now: every line of every starting file ends with a newline."))
F.append(dropped("10", "No case checks the exceptional added-newline byte count when a middle read makes the buffer binary.", "BINARY-FILES",
    "Real gap; out of scope now: no file holds a NUL byte."))
F.append(backed("11", "The corpus does not distinguish an implementation that accepts an address on undo.",
    "addressed-undo-accepted", "Real gap and core (undo). Two address cases run 1u after a substitution, on a pipe and on a regular file; the generator also draws an addressed u.", "test_addresses"))
F.append(backed("12", "No case requires a valid basic bounded repeat whose lower bound is zero.",
    "zero-lower-bound-rejected", "Real gap and core (the regex engine). Two regex cases use \\{0\\} and \\{0,1\\}; the generator draws a\\{0\\} and o\\{0,1\\}.", "test_regex"))
F.append(backed("13", "Combined suffix tests never require an input-mode command to honor its print suffix.",
    "append-suffix-ignored", "Real gap and core (commands and current address). Four cases give a, i, c and an empty 0a a print suffix; the generator draws a, i and c with p, n and pn.", "test_append_insert_change"))
F.append(backed("14", "FILE-parameter separator cases use spaces, leaving the whitespace separator untested for tabs.",
    "tab-separator-rejected", "Real gap. Three cases separate w, r, W, f and e from their file with a tab; the generator draws a tab separator for every file command.", "test_files_and_write"))
F.append(backed("15", "No graded case checks that joining a marked line invalidates its mark.",
    "join-keeps-mark", "Real gap and core (marks). Three cases join a marked first line, a marked second line, and undo the join.", "test_addresses"))
F.append(dropped("16", "The l cases never require escaping a literal backslash.", "LIST-COMMAND",
    "Real gap; l is out of scope now."))
F.append(backed("17", "The omitted-final-delimiter cases do not test that a multi-line substitution prints the last affected line.",
    "open-s-prints-first-line", "Real gap and core (s forms). Two cases run a ranged s with no final delimiter; the generator draws an open s with every address form.", "test_substitute"))
F.append(backed("18", "No case rejects an ordinary substitution suffix that is forbidden on the abbreviated repeat form.",
    "repeat-form-accepts-n", "Real gap and core (s forms). Two cases run sn and sN after an s; the generator draws sn and s followed by a tab.", "test_substitute"))
F.append(dropped("19", "The corpus does not exercise the contract-permitted 100,000-byte line boundary.", "LONG-LINES",
    "Real gap against the old bound; the bound is now 200 bytes."))
F.append(dropped("20", "No case supplies EOF while a matching interactive G or V command is waiting for its command list.", "INTERACTIVE-GLOBAL",
    "Real gap. G and V repeat the global command with lists read from standard input; the active-list semantics stay graded through g and v, and G, V and their EOF rule left the contract."))
F.append({"id": "21", "axis": "sound_verifier", "severity": "Major", "blocking": True,
    "summary": "No graded case verifies that -s suppresses the byte count produced by the uppercase E edit command.",
    "decision": "disputed",
    "rationale": "Refuted by execution: the returned corpus already holds files_and_write case `E other.txt` then `f`, run with -s f.txt. The finding's own wrong implementation (E prints its count under -s) was scored against the returned verifier and failed test_files_and_write on that case: GNU printed other.txt, the wrong implementation printed 9 and then other.txt. Two more E cases were added anyway, with and without -s.",
    "reproduction": "receipts/returned/E-count-ignores-s.json", "counterexample": "receipts/returned/E-count-ignores-s.json",
    "contract_citation": {"file": "instruction.md", "anchor": "the same standard output, byte for byte"},
    "contested_in_channel": CHANNEL,
    "gate": {"rule": "wrong path E-count-ignores-s must fail test_files_and_write (receipt on the returned and on the repaired snapshot)"}})
F.append(dropped("22", "The corpus never distinguishes a \\b that recognizes only word beginnings.", "GNU-WORD-ESCAPES",
    "Real gap. The GNU word and space escapes are conveniences on top of the POSIX engine the task is about; the instruction now says they never appear."))
F.append(dropped("23", "The corpus does not verify that \\w includes digits or that \\W accepts punctuation.", "GNU-WORD-ESCAPES",
    "Real gap; out of scope now."))
F.append(dropped("24", "No case verifies that c copies every line of a deleted range into the cut buffer.", "CUT-BUFFER-XY",
    "Real gap. Without x and y the cut buffer cannot be observed, so it needs no contract; x and y are never used now."))
F.append(dropped("25", "The verifier never observes the cut buffer immediately after d.", "CUT-BUFFER-XY",
    "Real gap; out of scope now."))
F.append(dropped("26", "The verifier never makes GNU ed's initial z window size observable.", "Z-COMMAND",
    "Real gap. z's window is a display default; z is never used now."))
F.append(dropped("27", "The largest tested input line is 70,000 bytes, leaving 70,001-100,000 untested.", "LONG-LINES",
    "Real gap against the old bound; the bound is now 200 bytes."))
F.append({"id": "28", "axis": "sound_verifier", "severity": "Minor", "blocking": True,
    "summary": "The process and native-code guard can be disabled by the candidate because it runs the candidate in the same mutable __main__ module that owns the audit-hook policy.",
    "decision": "backed",
    "rationale": "Right, and wider than reported. On the returned launcher a program that rebinds the launcher's globals and then execs another program runs it, a search of live objects reaches the hook, and _posixsubprocess.fork_exec starts a program with no audit event at all. The launcher now keeps its rules only in the closure of a hook built inside install(), from interpreter functions captured before the program starts; it replaces fork_exec, stops a fresh import of that helper and stops the gc searches, and nine probe programs (four new) check it. Wrong path fork-exec-helper-delegation scores reward 1 on the returned verifier and 0 now.",
    "reproduction": "receipts/returned/guard-probes.json", "closure": "receipts/repaired/guard-probes.json",
    "gate": {"rule": "scripts/task-policy.py tests:audit-hook-process-gap: a tests/*.py that installs an audit hook policing process creation must mention fork_exec and must not pass a module-level function to sys.addaudithook; it fails on the returned snapshot and passes on the repaired one"}})
ledger = {"schema_version": 1, "task_slug": "tbrain-gnu-ed-reimplementation",
          "report_path": "workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v6/fc57838e-86e3-431c-a65c-b8776a1f307e.md",
          "returned_snapshot_sha256": tree_hash(RET), "repaired_snapshot_sha256": tree_hash(REP),
          "summary": ("28 blocking findings, the sixth return on the same axis. Revision v6 takes the reverse move the skill prescribes: "
                      "eight obligations left the contract (binary files, 100,000-byte lines, l, z, x/y, G/V, -p/-q/-r and long options, "
                      "the GNU word escapes), which answers 16 findings; 7 verifier findings on the core are backed with cases, wrong paths "
                      "and a 640-script grammar generator; 3 reference findings and 1 verifier finding are refuted by execution (one also "
                      "added errata entry 18); the launcher bypass is closed and bought a policy rule."),
          "findings": F, "previous_findings": []}
(HERE / "revision-ledger.json").write_text(json.dumps(ledger, indent=1) + "\n")
print(len(F), ledger["returned_snapshot_sha256"][:12], ledger["repaired_snapshot_sha256"][:12])
