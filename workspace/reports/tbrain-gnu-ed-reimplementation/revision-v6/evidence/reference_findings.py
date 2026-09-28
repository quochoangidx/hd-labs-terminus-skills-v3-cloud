"""Run each v6 reference finding's own script through GNU ed 1.19 and the returned reference
inside the verifier image, and write a receipt bound to the returned snapshot."""
import hashlib, json, subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[5]
RET = ROOT / "workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v6/tbrain-gnu-ed-reimplementation"
sys.path.insert(0, str(ROOT / ".agent/skills/terminus-regular-task-authoring/scripts"))
from revision_ledger_check import tree_hash  # noqa: E402
ROWS = [
    ("F3", "bracket [-a] takes the hyphen literally", [], {}, "a\na\n0\n.\ng/[-a]/p\nQ\n", "pipe"),
    ("F3b", "bracket [-a] with the hyphen itself in the buffer", [], {}, "a\na\n0\n-\n.\ng/[-a]/p\nQ\n", "pipe"),
    ("F4", "the finding's script: s without a match inside g, -s, regular-file stdin", ["-s"], {}, "a\na\nb\n.\ng/./s/a/A/\nQ\n", "file"),
    ("F4b", "same, showing the buffer and the list continuing", ["-s"], {}, "a\na\nb\n.\ng/./s/zzz/y/\\\np\n,p\nQ\n", "file"),
    ("F4c", "outside g the same s fails", ["-s"], {}, "a\nb\n.\ns/zzz/y/\n,p\nQ\n", "file"),
    ("F5", "--prompt=X long option", ["--prompt=X"], {}, "q\n", "pipe"),
    ("F6", "the finding's script: unset mark once the buffer holds a line", [], {}, "a\nx\n.\n'a=\nQ\n", "pipe"),
]
cases = [[r[2], r[3], r[4], r[5]] for r in ROWS]
work = pathlib.Path(__file__).resolve().parent
(work / "reference_findings_cases.json").write_text(json.dumps(cases))
cmd = ["docker", "run", "--rm", "-v", f"{work}:/w", "-v", f"{RET / 'solution'}:/sol:ro",
       "preflight-verifier-tbrain-gnu-ed-reimplementation", "python3", "/w/cmp.py", "/w/reference_findings_cases.json"]
p = subprocess.run(cmd, capture_output=True, text=True)
lines = p.stdout.splitlines()
verdicts = [l.split()[0] for l in lines if l.startswith(("SAME", "DIFF"))]
receipt = {"schema_version": 1, "what": "v6 reference findings 3-6 executed against GNU ed 1.19 and the returned reference",
           "task_snapshot_sha256": tree_hash(RET), "command": " ".join(cmd), "exit_code": p.returncode,
           "rows": [{"id": r[0], "about": r[1], "args": r[2], "stdin": r[5], "script": r[4], "verdict": v}
                    for r, v in zip(ROWS, verdicts)], "raw_output": p.stdout}
out = work.parent / "receipts/returned/reference-findings-3-4-5-6.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(receipt, indent=1))
print(p.stdout)
