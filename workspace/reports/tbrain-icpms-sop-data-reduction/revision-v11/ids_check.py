"""ids_check.py TASK_DIR: every sealed batch's run ids. Reports exact duplicates (a real SOP section 1
violation) and ids sharing a stem before a hyphen (what the v11 panel misread as duplicates).
Exit 1 only on an exact duplicate; --strict also fails on a shared stem."""
import collections, glob, json, sys
bad = shared = 0
for f in sorted(glob.glob(sys.argv[1] + "/tests/expected/*.jsonl")):
    for i, line in enumerate(open(f)):
        ids = [r["id"] for r in json.loads(line)["batch"]["runs"]]
        dup = [k for k, v in collections.Counter(ids).items() if v > 1]
        stems = {k: v for k, v in collections.Counter(x.split("-")[0] for x in ids if "-" in x and x.split("-")[-1].isdigit() and x[0] == "R").items() if v > 1}
        bad += bool(dup); shared += bool(stems)
        if dup or stems:
            print(f.split("/")[-1], "row", i, "exact duplicates:", dup, "shared R-stems:", stems)
print("exact-duplicate batches:", bad, " batches with shared R-stems:", shared)
sys.exit(1 if bad or ("--strict" in sys.argv and shared) else 0)
