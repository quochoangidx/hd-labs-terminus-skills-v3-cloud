"""Receipts for the v7 findings answered without a wrong path."""
import json, subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / ".agent/skills/terminus-regular-task-authoring/scripts"))
from revision_ledger_check import tree_hash  # noqa: E402
EV = pathlib.Path(__file__).resolve().parent
RET = ROOT / "workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v7/tbrain-gnu-ed-reimplementation"
REP = ROOT / "workspace/tasks/tbrain-gnu-ed-reimplementation"
sys.path.insert(0, str(REP / "tests"))
import scope  # noqa: E402  (the repaired checker, applied to the returned corpus)

def write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=1))

# 1. findings 5-11, 20, 21: the returned corpus steps outside the stated domain
cd = RET / "tests/cases"
fx = json.loads((cd / "fixtures.json").read_text())
roster = json.loads((cd / "roster.json").read_text())
rows = []
for fam in roster["families"]:
    for i, line in enumerate((cd / f"{fam}.jsonl").read_text().splitlines()):
        r = json.loads(line)
        p = scope.case_problems({**r, "files": fx[r["fixture"]]})
        if p:
            rows.append({"case": f"{fam}.jsonl:{i + 1}", "stdin": r["stdin"], "script": r["script"], "problems": p})
write(EV.parent / "receipts/returned/out-of-domain-cases.json",
      {"schema_version": 1, "what": "committed cases of the returned snapshot that leave the domain instruction.md states",
       "task_snapshot_sha256": tree_hash(RET), "command": "python3 revision-v7/evidence/static_receipts.py (repaired tests/scope.py over the returned corpus)",
       "exit_code": 0, "count": len(rows), "rows": rows})
# the same check on the repaired snapshot, as the verifier runs it at collection
sys.path.insert(0, str(REP / "tests"))
p = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'tests'); import test_outputs as t; print(len(t.CASES))"],
                   cwd=REP, capture_output=True, text=True)
write(EV.parent / "receipts/repaired/domain-check.json",
      {"schema_version": 1, "what": "collection of the repaired verifier, which fails if any case leaves the stated domain",
       "task_snapshot_sha256": tree_hash(REP), "command": "python3 -c 'import test_outputs' (collection)", "exit_code": p.returncode,
       "cases_loaded": p.stdout.strip(), "stderr_tail": p.stderr[-400:]})

# 2. findings 12, 13/14: GNU ed against the reference on the findings' own scripts
cases = [
 ["F12-g", [["f.txt"], {"f.txt": ".\n"}, "g/[-a]/p\nQ\n", "file"]],
 ["F12-s", [["f.txt"], {"f.txt": ".\n"}, "s/[-a]/X/\nQ\n", "file"]],
 ["F13", [[], {}, "a\n\xe9\n.\ng/\xc9/Ip\nQ\n", "pipe"]],
 ["F13-ascii", [[], {}, "a\nAb\n.\ng/ab/Ip\ns/B/x/I\np\nQ\n", "pipe"]],
]
(EV / "ref_cases.json").write_text(json.dumps([c for _, c in cases]))
for label, task in (("returned", RET), ("repaired", REP)):
    cmd = ["docker", "run", "--rm", "-v", f"{EV}:/w", "-v", f"{task / 'solution'}:/sol:ro",
           "preflight-verifier-tbrain-gnu-ed-reimplementation", "python3", "/w/cmp.py", "/w/ref_cases.json"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    verdicts = [l.split()[0] for l in out.stdout.splitlines() if l.startswith(("SAME", "DIFF"))]
    write(EV.parent / f"receipts/{label}/reference-findings-12-13-14.json",
          {"schema_version": 1, "what": f"v7 reference findings on the {label} reference, against GNU ed 1.19",
           "task_snapshot_sha256": tree_hash(task), "command": " ".join(cmd), "exit_code": out.returncode,
           "rows": [{"id": l, "case": c, "verdict": v} for (l, c), v in zip(cases, verdicts)], "raw_output": out.stdout})
    print(label, verdicts)

# 3. findings 15 and 24: their scripts need x, which the contract excludes
panel = {"15": "a\nfoo\n.\ns/foo/bar/\nx\n,p\nQ\n", "24": "a\nfoo\n.\ns/foo/bar/\n0x\n,p\nQ\n"}
write(EV.parent / "receipts/returned/cut-buffer-scripts-out-of-domain.json",
      {"schema_version": 1, "what": "the scripts of findings 15 and 24 checked against the stated domain",
       "task_snapshot_sha256": tree_hash(RET), "command": "tests/scope.py case_problems on each script", "exit_code": 0,
       "rows": {k: scope.case_problems({"args": [], "stdin": "pipe", "script": s, "files": []}) for k, s in panel.items()}})
print(len(rows), "returned out-of-domain rows;", p.stdout.strip(), "cases load on the repaired snapshot")
