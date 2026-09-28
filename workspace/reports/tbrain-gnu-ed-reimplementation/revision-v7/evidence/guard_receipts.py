"""Finding 28: run the nine launcher probes and an ordinary program against the returned
launcher and the repaired one; one receipt per snapshot."""
import json, subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / ".agent/skills/terminus-regular-task-authoring/scripts"))
from revision_ledger_check import tree_hash  # noqa: E402
EV = pathlib.Path(__file__).resolve().parent
NEW = ROOT / "workspace/tasks/tbrain-gnu-ed-reimplementation"
RET = ROOT / "workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v7/tbrain-gnu-ed-reimplementation"
for label, task in (("returned", RET), ("repaired", NEW)):
    cmd = ["docker", "run", "--rm", "-v", f"{task / 'tests'}:/g:ro", "-v", f"{NEW / 'tests/guardcheck'}:/newprobes:ro",
           "-v", f"{EV}:/e:ro", "preflight-verifier-tbrain-gnu-ed-reimplementation", "bash", "/e/guard_probe.sh"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    rows = []
    for line in p.stdout.splitlines():
        name, status, out, err = (line.split("\t") + ["", "", ""])[:4]
        rows.append({"probe": name, "status": int(status), "stdout": out, "stderr_tail": err,
                     "stopped": status == "120"})
    receipt = {"schema_version": 1, "what": f"launcher probes against the {label} guard.py",
               "task_snapshot_sha256": tree_hash(task), "command": " ".join(cmd), "exit_code": p.returncode,
               "rows": rows}
    out = EV.parent / "receipts" / label / "guard-probes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=1))
    print(label, [(r["probe"], r["status"]) for r in rows])
