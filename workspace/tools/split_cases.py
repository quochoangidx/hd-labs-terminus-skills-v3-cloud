"""split_cases.py <task-dir>

Split tests/cases.json into tests/cases/<family>-<n>.jsonl files of one case per line,
each well under the panel's per-file read limit, and pin the roster: test_outputs.py
loads every chunk and fails at collection unless the per-family counts equal ROSTER.
"""
import collections
import json
import os
import re
import sys

LIMIT = 50_000
task = sys.argv[1]
tests = os.path.join(task, "tests")
cases = json.load(open(os.path.join(tests, "cases.json"), encoding="utf-8"))
out_dir = os.path.join(tests, "cases")
if os.path.isdir(out_dir):
    for name in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, name))
os.makedirs(out_dir, exist_ok=True)

by_family = collections.OrderedDict()
for case in cases:
    by_family.setdefault(case["family"], []).append(case)
for family, items in by_family.items():
    chunk, size, n = [], 0, 1
    for case in items:
        line = json.dumps(case, ensure_ascii=True, separators=(",", ":")) + "\n"
        if chunk and size + len(line) > LIMIT:
            open(os.path.join(out_dir, "%s-%d.jsonl" % (family, n)), "w").write("".join(chunk))
            chunk, size, n = [], 0, n + 1
        chunk.append(line)
        size += len(line)
    open(os.path.join(out_dir, "%s-%d.jsonl" % (family, n)), "w").write("".join(chunk))
roster = {f: len(v) for f, v in by_family.items()}
os.remove(os.path.join(tests, "cases.json"))

p = os.path.join(tests, "test_outputs.py")
t = open(p).read()
old = re.search(r'with open\(os\.path\.join\(HERE, "cases\.json"\), encoding="utf-8"\) as handle:\n    CASES = json\.load\(handle\)\n', t)
if old:
    roster_src = "ROSTER = {\n" + "".join('    "%s": %d,\n' % kv for kv in roster.items()) + "}\n"
    new = (roster_src + "\n\ndef load_cases():\n"
           '    """Read every case chunk (one JSON case per line) and pin the roster."""\n'
           "    cases = []\n"
           '    folder = os.path.join(HERE, "cases")\n'
           "    for name in sorted(os.listdir(folder)):\n"
           '        if name.endswith(".jsonl"):\n'
           '            with open(os.path.join(folder, name), encoding="utf-8") as handle:\n'
           "                cases.extend(json.loads(line) for line in handle if line.strip())\n"
           "    counts = {}\n"
           "    for case in cases:\n"
           '        counts[case["family"]] = counts.get(case["family"], 0) + 1\n'
           '    assert counts == ROSTER, f"case roster mismatch: {counts} != {ROSTER}"\n'
           "    return cases\n\n\n"
           "CASES = load_cases()\n")
    t = t[:old.start()] + new + t[old.end():]
    open(p, "w").write(t)
print(len(cases), "cases in", len(os.listdir(out_dir)), "files; largest",
      max(os.path.getsize(os.path.join(out_dir, f)) for f in os.listdir(out_dir)))
