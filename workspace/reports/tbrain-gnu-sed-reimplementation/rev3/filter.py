# Scope filter for rev3: run every rev2 case through GNU sed 4.9 and the trimmed reference
# (inside the verifier image). A case whose script uses a construct outside the new subset
# makes the reference exit 1 with "outside the subset" -> dropped. A case the reference
# accepts must match GNU byte for byte -> kept; any other difference is a reference bug.
# usage: python3 filter.py <cases-dir> <pysed-dir> <out-dir>
import json, os, subprocess, sys, tempfile, time

cases_dir, pysed, out_dir = sys.argv[1:4]
inputs = json.load(open(os.path.join(cases_dir, "inputs.json")))


def text(v):
    return inputs[v[1:]] if isinstance(v, str) and v.startswith("@") else v


def args(c):
    names = [n for n, _ in c.get("files", [])]
    return c["opts"] + ([c["script"]] if c.get("script_arg") else ["-e", c["script"]]) + c.get("extra", []) + names


def run(cmd, c):
    d = tempfile.mkdtemp()
    for n, t in c.get("files", []):
        if t is not None:
            open(os.path.join(d, n), "w", encoding="latin-1").write(text(t))
    t0 = time.time()
    try:
        p = subprocess.run(cmd + args(c), input=text(c["input"]).encode("latin-1"), capture_output=True,
                           cwd=d, env={"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin"}, timeout=20)
        return p.stdout.decode("latin-1"), p.returncode, p.stderr.decode("latin-1"), round(time.time() - t0, 2)
    except subprocess.TimeoutExpired:
        return None, "timeout", "", 20


report = {"kept": {}, "dropped": {}, "diff": []}
kept_files = {}
for name in sorted(os.listdir(cases_dir)):
    if name == "inputs.json" or not name.endswith(".json"):
        continue
    data = json.load(open(os.path.join(cases_dir, name)))
    kept_files[name] = {}
    for family, rows in data.items():
        for row in rows:
            g = run(["sed"], row)
            r = run(["/usr/local/bin/python3", os.path.join(pysed, "sed.py")], row)
            if r[1] == 1 and "outside the subset" in r[2]:
                report["dropped"].setdefault(family, []).append({"script": row["script"], "why": r[2].strip()[-60:]})
                continue
            if g[:2] != r[:2]:
                report["diff"].append({"file": name, "family": family, "case": row, "gnu": g[:2], "ref": r[:2], "stderr": r[2][-200:]})
                continue
            if r[3] > 1.0:
                report.setdefault("slow", []).append({"family": family, "script": row["script"], "t": r[3]})
            kept_files[name].setdefault(family, []).append(row)
            report["kept"][family] = report["kept"].get(family, 0) + 1
os.makedirs(out_dir, exist_ok=True)
for name, fams in kept_files.items():
    json.dump(fams, open(os.path.join(out_dir, name), "w"), indent=0, ensure_ascii=False)
json.dump(report, open(os.path.join(out_dir, "filter-report.json"), "w"), indent=1)
print("kept", sum(report["kept"].values()), json.dumps(report["kept"], indent=0))
print("dropped", {k: len(v) for k, v in report["dropped"].items()})
print("DIFF", len(report["diff"]))
for d in report["diff"][:40]:
    print("  ", d["family"], repr(d["case"]["opts"]), repr(d["case"]["script"])[:80], "gnu=", repr(d["gnu"])[:80], "ref=", repr(d["ref"])[:80], d["stderr"][-80:].strip())
print("slow", report.get("slow", [])[:10])
