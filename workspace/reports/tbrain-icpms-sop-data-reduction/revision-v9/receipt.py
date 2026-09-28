"""receipt.py OUT.json TASK_DIR -- CMD...: run CMD, record command, exit code, output and the task snapshot."""
import json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / ".agent/skills/terminus-regular-task-authoring/scripts"))
out, task = sys.argv[1], sys.argv[2]
cmd = sys.argv[sys.argv.index("--") + 1:]
snap = subprocess.run([sys.executable, str(REPO / ".agent/skills/terminus-regular-task-authoring/scripts/revision_ledger_check.py"), task, "x", "--print-snapshot"],
                      capture_output=True, text=True, cwd=REPO).stdout.strip()
proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
Path(out).write_text(json.dumps({"command": " ".join(cmd), "exit_code": proc.returncode, "task_dir": task,
                                 "task_snapshot_sha256": snap, "stdout": proc.stdout[-6000:], "stderr": proc.stderr[-2000:]}, indent=1) + "\n")
print(proc.stdout, proc.stderr[-500:], "exit", proc.returncode)
