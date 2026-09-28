"""v8: drop the committed row tests/scope.py now rejects (the \\> escape), and add the
focused cases for the v8 coverage findings."""
import json, os, sys
sys.path.insert(0, sys.argv[1])
import scope
CASES = os.path.join(sys.argv[1], "cases")
E = "no_files_01"
def pc(script, args=(), stdin="pipe", fixture=E):
    return {"args": list(args), "fixture": fixture, "script": script, "stdin": stdin}
NEW = {
 "addresses": [
  ("2", pc("a\nx\ny\n.\n1kap\n2kbn\n'a,'bp\n$kapn\n'ap\nQ\n")),
  ("2", pc("a\nx\ny\n.\n1kap\n'a,.p\nQ\n", stdin="file")),
  ("13", pc("a\n1\n2\n3\n4\n5\n6\n.\n1,2,3,4,5p\n1;2;3;4;5;6n\n3,4,5,6,1,2p\n.=\nQ\n", ["-s"])),
 ],
 "regex": [
  ("4,7", pc("a\nabab\nababab\nab\n.\ng/^\\(ab\\)\\{2\\}$/p\ns/\\(ab\\)\\{2\\}/X/p\n3s/\\(ab\\)\\{1,\\}/Y/p\n1,$s/\\(ab\\)\\{2,3\\}/Z/\n,p\nQ\n")),
  ("4,11", pc("a\nabab\nabc\nc\n.\n1s/\\(ab\\)\\+/X/p\ng/^\\(ab\\)\\?c$/p\n2s/\\(ab\\)\\?c/Q/p\ns/\\(a\\|b\\)\\+/W/g\n,p\nQ\n")),
  ("4,11", pc("a\nxyxyz\n.\ns/\\(x\\(y\\)\\)\\+z/[\\1\\2]/p\ng/\\(xy\\)\\?\\(xy\\)\\{1\\}z/p\nQ\n")),
  ("6", pc("a\nabcdee\nabcdefghhgfe\nabcdefghh\n.\ng/\\(a\\)\\(b\\)\\(c\\)\\(d\\)\\(e\\)\\5/p\ng/\\(a\\)\\(b\\)\\(c\\)\\(d\\)\\(e\\)\\(f\\)\\(g\\)\\(h\\)\\8\\7\\6\\5/n\nv/\\(a\\)\\(b\\)\\(c\\)\\(d\\)\\(e\\)\\(f\\)\\(g\\)\\(h\\)\\8/p\ng/\\(.\\)\\(.\\)\\(.\\)\\(.\\)\\(.\\)\\(.\\)\\6/p\ng/\\(.\\)\\(.\\)\\(.\\)\\(.\\)\\(.\\)\\(.\\)\\(.\\)\\7/p\nQ\n")),
 ],
 "regex_extended": [
  ("4,7,11", pc("a\nabab\nababab\nabc\n.\ng/^(ab){2}$/p\ns/(ab)+/X/p\n3s/(ab)?c/Q/p\n2s/(ab){1,2}/Y/p\n,p\nQ\n", ["-E"])),
  ("6", pc("a\nabcdee\nabcdefghhgfe\n.\ng/(a)(b)(c)(d)(e)\\5/p\ng/(a)(b)(c)(d)(e)(f)(g)(h)\\8\\7\\6\\5/p\nQ\n", ["-E"])),
 ],
 "files_and_write": [
  ("5", pc("a\nx\n.\nw a b\nf\nr a b\n,p\nW c  d\nw  lead\ne a b\n,p\nf\nQ\n", ["-s"])),
  ("5", pc("a\nx\n.\nw a b\nQ\n")),
 ],
}
fx = json.load(open(os.path.join(CASES, "fixtures.json")))
roster = json.load(open(os.path.join(CASES, "roster.json")))
dropped, cov, fams = {}, {}, {}
for fam in sorted(roster["families"]):
    path = os.path.join(CASES, fam + ".jsonl")
    rows = [json.loads(l) for l in open(path) if l.strip()]
    keep = []
    for i, r in enumerate(rows):
        problems = scope.case_problems({**r, "files": fx[r["fixture"]]})
        if problems:
            dropped[f"{fam}:{i}"] = {"script": r["script"], "problems": problems}
            continue
        keep.append(r)
    for finding, r in NEW.get(fam, []):
        p = scope.case_problems({**r, "files": fx[r["fixture"]]})
        assert not p, (finding, p)
        keep.append(r)
        for f in finding.split(","):
            cov.setdefault(f, {"cases": []})["cases"].append({"family": fam, **r})
    with open(path, "w", encoding="utf-8") as out:
        for r in keep:
            out.write(json.dumps(r, ensure_ascii=True) + "\n")
    fams[fam] = len(keep)
roster = {"families": fams, "fixtures": len(fx), "total": sum(fams.values())}
with open(os.path.join(CASES, "roster.json"), "w") as out:
    json.dump(roster, out, indent=1); out.write("\n")
H = os.path.dirname(os.path.abspath(__file__))
json.dump(dropped, open(os.path.join(H, "evidence/dropped-rows.json"), "w"), indent=1)
json.dump({"schema_version": 1, "task_slug": "tbrain-gnu-ed-reimplementation", "what": "v8 findings answered with cases", "findings": cov}, open(os.path.join(H, "evidence/coverage-map.json"), "w"), indent=1)
print(len(dropped), "dropped;", roster)
