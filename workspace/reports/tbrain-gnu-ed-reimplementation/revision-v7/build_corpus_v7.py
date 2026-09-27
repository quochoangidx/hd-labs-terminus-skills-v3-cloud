"""v7: drop every committed row tests/scope.py rejects (plus the slxlyl row the panel read as
an l suffix), and add the focused cases for the v7 findings kept in scope."""
import json, os, sys
sys.path.insert(0, sys.argv[1])
import scope
CASES = os.path.join(sys.argv[1], "cases")
L200 = "y" * 199 + "x"
NEW = {
 "files_and_write": [
  ("1", {"args": ["f.txt"], "fixture": "f_long200", "script": "2p\n2s/x$/Z/\n2p\n$=\nw out\nQ\n", "stdin": "pipe"}),
  ("23", {"args": ["-s", "f.txt"], "fixture": "f_a_other_o", "script": "r oth\\\ner.txt\n,p\nf ne\\\nw.txt\nf\nw\nE oth\\\ner.txt\n,p\ne f.\\\ntxt\n,p\nQ\n", "stdin": "pipe"}),
  ("25", {"args": ["f.txt"], "fixture": "f_12", "script": "1W other.txt\nf\n2W other.txt\nf\nQ\n", "stdin": "pipe"}),
  ("25", {"args": [], "fixture": "no_files_01", "script": "a\nx\n.\nW first.txt\nf\nW second.txt\nf\nQ\n", "stdin": "pipe"}),
 ],
 "append_insert_change": [
  ("17", {"args": ["-s"], "fixture": "no_files_01", "script": "a\n" + L200 + "\n.\ns/x$/Q/\np\nw out\nQ\n", "stdin": "pipe"}),
  ("17", {"args": ["-s"], "fixture": "no_files_01", "script": "a\nq\n.\ns/q/" + "z" * 195 + "/\np\n$=\nQ\n", "stdin": "pipe"}),
 ],
 "regex_extended": [
  ("2", {"args": ["-E", "f.txt"], "fixture": "f_amb", "script": "g/[[.-.]]/p\ng/[[=a=]]b/p\ns/[[.-.]]+/_/\n,p\nQ\n", "stdin": "pipe"}),
  ("3", {"args": ["-E", "f.txt"], "fixture": "f_zyy", "script": "g/y{32768,}|z/p\ng/y{32767,}|z/p\nQ\n", "stdin": "pipe"}),
  ("19", {"args": ["-E"], "fixture": "no_files_01", "script": "a\nabcd\n.\ns/(((a)b)c)(d)/[\\4\\3\\2\\1]/\np\nQ\n", "stdin": "pipe"}),
 ],
 "regex": [
  ("3", {"args": ["f.txt"], "fixture": "f_zyy", "script": "g/y\\{32768,\\}\\|z/p\ng/y\\{32767,\\}\\|z/p\nQ\n", "stdin": "pipe"}),
  ("19", {"args": [], "fixture": "no_files_01", "script": "a\nabcd\n.\ns/\\(\\(\\(a\\)b\\)c\\)\\(d\\)/[\\4\\3\\2\\1]/\np\ng/\\(\\(\\(y\\)\\)\\)\\|[[]/p\nQ\n", "stdin": "pipe"}),
  ("13", {"args": [], "fixture": "no_files_01", "script": "a\nAb\nab\n.\ng/aB/Ip\ns/B/x/gI\n,p\nQ\n", "stdin": "pipe"}),
 ],
 "substitute": [
  ("4", {"args": [], "fixture": "no_files_01", "script": "a\nab\nab\n.\n1s/a/A/\n/b/\nsrp\nspr\n,p\nQ\n", "stdin": "pipe"}),
 ],
 "delete_join_move_copy": [
  ("18", {"args": ["-s"], "fixture": "no_files_01", "script": "a\nx\n.\n" + ",t$\n" * 12 + "$=\n$s/x/y/\n$-1,$p\nw out\nQ\n", "stdin": "pipe"}),
 ],
}
fx = json.load(open(os.path.join(CASES, "fixtures.json")))
fx["f_long200"] = [["f.txt", "a\n" + L200 + "\nb\n"]]
fx["f_a_other_o"] = [["f.txt", "a\n"], ["other.txt", "o\n"]]
fx["f_amb"] = [["f.txt", "a-b\nab\n"]]
roster = json.load(open(os.path.join(CASES, "roster.json")))
dropped, cov, used, fams = {}, {}, set(), {}
for fam in sorted(roster["families"]):
    path = os.path.join(CASES, fam + ".jsonl")
    rows = [json.loads(l) for l in open(path) if l.strip()]
    keep = []
    for i, r in enumerate(rows):
        problems = scope.case_problems({**r, "files": fx[r["fixture"]]})
        if problems or r["script"] == "a\nx\n.\nslxlyl\np\nQ\n":
            dropped[f"{fam}:{i}"] = problems or ["panel read the l delimiter of slxlyl as an l suffix (v7 finding 9)"]
            continue
        keep.append(r)
    for finding, r in NEW.get(fam, []):
        assert not scope.case_problems({**r, "files": fx[r["fixture"]]}), (finding, scope.case_problems({**r, "files": fx[r["fixture"]]}))
        keep.append(r)
        cov.setdefault(finding, {"cases": []})["cases"].append({"id": f"v7-{finding}", "family": fam, "args": r["args"], "stdin": r["stdin"], "script": r["script"], "files": fx[r["fixture"]]})
    with open(path, "w", encoding="utf-8") as out:
        for r in keep:
            out.write(json.dumps(r, ensure_ascii=True) + "\n"); used.add(r["fixture"])
    fams[fam] = len(keep)
fx = {k: v for k, v in sorted(fx.items()) if k in used}
with open(os.path.join(CASES, "fixtures.json"), "w") as out:
    json.dump(fx, out, indent=1, ensure_ascii=True); out.write("\n")
roster = {"families": fams, "fixtures": len(fx), "total": sum(fams.values())}
with open(os.path.join(CASES, "roster.json"), "w") as out:
    json.dump(roster, out, indent=1); out.write("\n")
json.dump(dropped, open("evidence/dropped-rows.json", "w"), indent=1)
json.dump({"schema_version": 1, "task_slug": "tbrain-gnu-ed-reimplementation", "what": "v7 findings answered with cases", "findings": cov}, open("evidence/coverage-map.json", "w"), indent=1)
print(len(dropped), "dropped;", roster)
