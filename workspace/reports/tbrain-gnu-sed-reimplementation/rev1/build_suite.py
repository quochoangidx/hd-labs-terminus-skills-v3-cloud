"""Write tests/cases/*.json: shared named inputs + one case per line, grouped by family."""
import collections, json, os, sys
T = sys.argv[1]  # task dir
old = json.load(open("old_cases.json")); new = json.load(open("new_cases.json"))
cases = []
for x in old + new:
    x = {k: v for k, v in x.items() if k != "finding"}
    cases.append(x)
# name inputs used by 3+ cases
cnt = collections.Counter(x["input"] for x in cases)
cnt.update(t for x in cases for _, t in x.get("files", []) if t)
names = {}
for text, k in cnt.most_common():
    if k >= 3 and len(text) > 8:
        names[text] = f"@in{len(names) + 1}"
def ref(t):
    return names.get(t, t) if t is not None else None
fam = collections.OrderedDict()
for x in cases:
    row = {"opts": x["opts"], "script": x["script"], "input": ref(x["input"])}
    if "files" in x: row["files"] = [[n, ref(t)] for n, t in x["files"]]
    if x.get("script_arg"): row["script_arg"] = True
    if x.get("extra"): row["extra"] = x["extra"]
    fam.setdefault(x["family"], []).append(row)
d = os.path.join(T, "tests", "cases"); os.makedirs(d, exist_ok=True)
def dump(path, obj):
    lines = ["{"]
    keys = list(obj)
    for i, k in enumerate(keys):
        rows = obj[k]
        if isinstance(rows, str):
            lines.append(f" {json.dumps(k)}: {json.dumps(rows)}" + ("," if i < len(keys) - 1 else ""))
            continue
        lines.append(f" {json.dumps(k)}: [")
        for j, r in enumerate(rows):
            lines.append("  " + json.dumps(r, separators=(", ", ": ")) + ("," if j < len(rows) - 1 else ""))
        lines.append(" ]" + ("," if i < len(keys) - 1 else ""))
    lines.append("}")
    open(path, "w").write("\n".join(lines) + "\n")
dump(os.path.join(d, "inputs.json"), {v[1:]: k for k, v in names.items()})
groups = {"areas.json": [f for f in fam if not f.startswith("mixed")],
          "mixed_1_2.json": ["mixed_scripts_1", "mixed_scripts_2"],
          "mixed_3_4.json": ["mixed_scripts_3", "mixed_scripts_4"]}
for fn, fams in groups.items():
    dump(os.path.join(d, fn), {f: fam[f] for f in fams})
for fn in sorted(os.listdir(d)):
    p = os.path.join(d, fn); print(fn, os.path.getsize(p), sum(1 for _ in open(p)))
print({f: len(v) for f, v in fam.items()}, sum(len(v) for v in fam.values()))
