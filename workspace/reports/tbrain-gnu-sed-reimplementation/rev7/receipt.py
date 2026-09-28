# Runs a shell command and writes a snapshot-bound receipt.
# usage: receipt.py <out.json> <snapshot-sha256> <claim> -- <shell command>
import json, subprocess, sys
out, snap, claim = sys.argv[1:4]
cmd = " ".join(sys.argv[sys.argv.index("--") + 1:])
p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
json.dump({"command": cmd, "exit_code": p.returncode, "task_snapshot_sha256": snap, "claim": claim,
           "line_counts": {k: sum(l.startswith(k) for l in p.stdout.splitlines()) for k in ("SAME", "DIFF")},
           "diff_lines": [l[:300] for l in p.stdout.splitlines() if l.startswith("DIFF")][:60],
           "stdout": p.stdout[-6000:], "stderr": p.stderr[-1500:]}, open(out, "w"), indent=1)
print(out, "exit", p.returncode)
