"""Run cases through GNU ed 1.19 and a tree's reference solution inside the verifier image.
usage: edcompare.py <task-dir> <cases.json> <receipt.json>
Each case: {id, args, stdin: pipe|file, script, files: [[name, text], ...]}"""
import json, os, subprocess, sys, hashlib, pathlib
sys.path.insert(0, "/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/.agent/skills/terminus-regular-task-authoring/scripts")
from revision_ledger_check import tree_hash
task, cases_path, receipt = sys.argv[1:4]
task = os.path.abspath(task)
INNER = r'''
import json, os, subprocess, tempfile, sys
cases = json.load(open("/cases.json"))
def run(cmd, c):
    d = tempfile.mkdtemp()
    for n, t in c["files"]:
        p = os.path.join(d, n); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="latin-1").write(t)
    s = tempfile.mktemp(); open(s, "w", encoding="latin-1").write(c["script"])
    if c["stdin"] == "file":
        r = subprocess.run(cmd + c["args"], stdin=open(s, "rb"), capture_output=True, cwd=d, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin:/usr/local/bin"}, timeout=60)
    else:
        r = subprocess.run(cmd + c["args"], input=c["script"].encode("latin-1"), capture_output=True, cwd=d, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin:/usr/local/bin"}, timeout=60)
    files = {}
    for root, _, names in os.walk(d):
        for n in names:
            files[os.path.relpath(os.path.join(root, n), d)] = open(os.path.join(root, n), encoding="latin-1").read()
    return {"stdout": r.stdout.decode("latin-1"), "zero_status": r.returncode == 0, "files": files}
out = []
for c in cases:
    ed = run(["/usr/bin/ed"], c); ref = run(["python3", "/ref/pyed/ed.py"], c)
    out.append({"id": c["id"], "gnu_ed": ed, "reference": ref, "agree": ed == ref})
print(json.dumps(out))
'''
r = subprocess.run(["docker", "run", "--rm", "-i", "--network", "none",
    "-v", os.path.abspath(cases_path) + ":/cases.json:ro", "-v", task + "/solution:/ref:ro",
    "gnued-ret", "python3", "-c", INNER], capture_output=True, text=True)
if r.returncode:
    print(r.stderr); sys.exit(1)
results = json.loads(r.stdout)
cases = {c["id"]: c for c in json.load(open(cases_path))}
for x in results:
    x["case"] = cases[x["id"]]
json.dump({"schema_version": 1, "task_snapshot_sha256": tree_hash(pathlib.Path(task)), "authority": "GNU ed 1.19 in the verifier image",
           "results": results}, open(receipt, "w"), indent=1)
for x in results:
    print(x["id"], "AGREE" if x["agree"] else "DIFFER", "| ed:", repr(x["gnu_ed"]["stdout"]), x["gnu_ed"]["zero_status"], "| ref:", repr(x["reference"]["stdout"]), x["reference"]["zero_status"])
