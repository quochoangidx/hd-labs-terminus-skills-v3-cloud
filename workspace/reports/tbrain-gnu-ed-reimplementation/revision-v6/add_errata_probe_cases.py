"""Both blind solvers read four corners the other way; errata 6, 17, 20 and 21 now state
what GNU ed 1.19 does, and these cases pin each sentence."""
import json, os, sys
CASES = sys.argv[1]
NEW = {
 "substitute": [
  ("6", {"args": [], "fixture": "no_files_01", "script": "a\nab\n.\ns/x*/-/2\np\ns/x*/-/3\np\ns/b*/-/2\np\nQ\n", "stdin": "pipe"}),
  ("20", {"args": [], "fixture": "no_files_01", "script": "a\nab\n.\ns/a/[\\1]/\np\ns/\\(a\\)/\\2/\np\nQ\n", "stdin": "pipe"}),
  ("20", {"args": [], "fixture": "no_files_01", "script": "a\nab\nab\n.\n1s/\\(a\\)\\(x\\)*/[\\2]/\n2s/\\(a\\)\\(x\\)*/[\\3]/\n,p\nQ\n", "stdin": "pipe"}),
  ("20", {"args": ["-E"], "fixture": "no_files_01", "script": "a\nab\n.\ns/(a)/[\\2]/\np\nQ\n", "stdin": "pipe"}),
 ],
 "global_commands": [
  ("17", {"args": [], "fixture": "no_files_01", "script": "a\nab\ncd\n.\ng/./s/b/B\n.=\nQ\n", "stdin": "pipe"}),
  ("17", {"args": [], "fixture": "no_files_01", "script": "a\nx\ny\n.\ng/./s/q/r\n,p\nQ\n", "stdin": "pipe"}),
 ],
 "files_and_write": [
  ("21", {"args": [], "fixture": "f_12", "script": "E nothere.txt\n=\nf\nq\n", "stdin": "pipe"}),
  ("21", {"args": ["f.txt"], "fixture": "f_12", "script": "2d\nE nothere.txt\nu\n=\nq\n", "stdin": "pipe"}),
 ],
}
roster = json.load(open(os.path.join(CASES, "roster.json")))
fx = json.load(open(os.path.join(CASES, "fixtures.json")))
out = {}
for fam, rows in NEW.items():
    with open(os.path.join(CASES, fam + ".jsonl"), "a", encoding="utf-8") as f:
        for entry, r in rows:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")
            out.setdefault(entry, []).append({"id": f"errata-{entry}", "family": fam, "args": r["args"], "stdin": r["stdin"], "script": r["script"], "files": fx[r["fixture"]]})
    roster["families"][fam] += len(rows); roster["total"] += len(rows)
with open(os.path.join(CASES, "roster.json"), "w") as f:
    json.dump(roster, f, indent=1); f.write("\n")
m = json.load(open("evidence/errata-map.json"))
m["findings"]["22"] = m["findings"].pop("20")
for entry, cases in out.items():
    m["findings"].setdefault(entry, {"cases": []})["cases"].extend(cases)
m["what"] = "every entry of environment/app/docs/ed-errata.txt (revision-v6 numbering, 22 entries) names the graded cases that pin it"
json.dump(m, open("evidence/errata-map.json", "w"), indent=1)
print(roster["total"], sorted(m["findings"], key=int))
