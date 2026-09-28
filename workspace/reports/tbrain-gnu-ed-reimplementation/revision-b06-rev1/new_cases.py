"""The rows this revision adds, by family, with the two new fixtures. Written into
tests/cases by add_cases.py after edcompare.py shows GNU ed and the reference agree."""
import json
F = json.load(open("/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/tasks/tbrain-gnu-ed-reimplementation/tests/cases/fixtures.json")) if False else None
FIXTURES = {
    "f_run200": [["f.txt", "a" * 200 + "\n" + "x" + "a" * 198 + "y\n" + "ab" * 100 + "\n"]],
    "big_60": [["big.txt", "".join("line %d of sixty\n" % k for k in range(1, 61))]],
}
def row(fixture, args, script, stdin="pipe"):
    return {"args": args, "fixture": fixture, "script": script, "stdin": stdin}
S = ["-s", "f.txt"]
ROWS = {
 "regex": [
  # open-ended and large repeats over a 200-byte run (finding 5)
  row("f_run200", S, "1s/a*/X/p\nu\n1s/a\\+/X/p\nu\n1s/a\\{1,\\}/X/p\nu\n1s/a\\{150,\\}/X/p\nu\n1s/a\\{200\\}/X/p\nu\ng/^a\\{201\\}/p\ng/^a\\{199\\}a$/n\nQ\n"),
  row("f_run200", S, "2s/xa*y/Z/p\nu\n2s/x.*y/Z/p\nu\n2s/a\\{64,\\}/-/p\nu\n3s/\\(ab\\)*/Z/p\nu\n3s/\\(ab\\)\\{1,\\}/Z/p\nu\n3s/\\(ab\\)\\1\\{99\\}/Z/p\nu\n3s/\\(ab\\)\\{100\\}$/Z/p\nQ\n"),
  # a large s count on a long line
  row("f_run200", S, "1s/a/b/150\n1p\n1s/a/c/51\n1p\n3s/b/B/100\n3p\n3s/b/B/101\n3p\nQ\n"),
  # every basic interval bound past the C library's limit, and a reversed pair (finding 8's class)
  row("f_zyy", ["f.txt"], "g/y\\{1,32768\\}\\|z/p\ng/y\\{32767,32768\\}\\|z/p\ng/y\\{3,2\\}\\|z/p\nQ\n"),
  # a back-reference after a bounded group, found only from a later start (finding 1)
  row("no_files_01", [], "a\naaab\nxaabaab\n.\n1s/\\(a\\{1,2\\}\\)\\1b/X/p\n2s/\\(a\\{1,3\\}\\)b\\1b/Y/p\nQ\n"),
 ],
 "regex_extended": [
  row("f_run200", ["-E"] + S, "1s/a*/X/p\nu\n1s/a+/X/p\nu\n1s/a{1,}/X/p\nu\n1s/a{150,}/X/p\nu\n2s/xa+y/Z/p\nu\n3s/(ab)+/Z/p\nu\n3s/(ab){100}/Z/p\nu\n3s/(ab)\\1{99}/Z/p\nQ\n"),
  # extended interval bounds past the limit (finding 8)
  row("f_zyy", ["-E", "f.txt"], "g/y{0,32768}|z/p\ng/y{1,32768}|z/p\ng/y{32767,32768}|z/p\ng/y{3,2}|z/p\nQ\n"),
  row("f_zyy", ["-E", "f.txt"], "g/y{0,32768}|z/p\n,p\n", "file"),
  row("no_files_01", ["-E"], "a\naaab\n.\ns/(a{1,2})\\1b/X/p\nQ\n"),
 ],
 "global_commands": [
  # f inside g and v lists (finding 6)
  row("no_files_01", [], "a\nx\n.\ng/x/f target\nf\nQ\n"),
  row("f_other_02", ["f.txt"], "v/zzz/f other.txt\nf\n2,3g/./f\nQ\n"),
  # g and v nested in either order are refused (finding 7)
  row("no_files_01", [], "a\nx\ny\n.\nv/nomatch/g/x/p\nv/nomatch/v/y/p\ng/x/v/y/p\ng/x/g/x/p\n,p\nQ\n"),
  row("no_files_01", [], "a\nx\n.\nv/nomatch/g/x/p\np\n", "file"),
  # the remaining file and comment commands inside g and v lists
  row("f_other_02", ["f.txt"], "g/./W w.txt\nv/zzz/W w2.txt\ng/1/#note\nv/zzz/# c\nv/zzz/r other.txt\n,n\nQ\n"),
  row("f_other_02", ["f.txt"], "2g/./e other.txt\n,p\nv/zzz/E f.txt\n,p\nQ\n"),
  row("f_other_02", ["f.txt"], "1d\nv/zzz/Q\np\n"),
  row("f_other_02", ["f.txt"], "2,3g/./wq out.txt\np\n"),
 ],
 "addresses": [
  # decimal addresses past line 33 in a 60-line file (finding 12)
  row("big_60", ["-s", "big.txt"], "34p\n45p\n59n\n60p\n61p\n$=\n34,36n\nQ\n"),
  row("big_60", ["-s", "big.txt"], "58,60n\n40p\n", "file"),
  # numeric offsets beyond two (finding 13)
  row("big_60", ["-s", "big.txt"], "1+3p\n1+10p\n$-7p\n.-12p\n10+25-5n\n-3p\n+9p\n1+59p\n1+60p\nQ\n"),
  # runs of four or more bare signs (finding 14)
  row("big_60", ["-s", "big.txt"], "1++++p\n$-----p\n1++++++++++n\n30---+++-p\n.+++++ +p\n1--p\nQ\n"),
  # every lowercase mark, not only a, b and x (finding 10)
  row("f_other_02", S, "1kc\n2kd\n3ke\n4kf\n5kg\n6kh\n7ki\n8kj\n9kk\n10kl\n'cp\n'dp\n'ep\n'fp\n'gp\n'hp\n'ip\n'jp\n'kp\n'lp\nQ\n"),
  row("f_other_02", S, "1km\n2kn\n3ko\n4kp\n5kq\n6kr\n7ks\n8kt\n9ku\n10kv\n1kw\n2kx\n3ky\n4kz\n'm,'vn\n'wp\n'xp\n'yp\n'zp\n'op\n'rp\n'up\nQ\n"),
  row("f_13", S, "1kc\n'cs/./b/\nw out\nQ\n", "file"),
 ],
}
if __name__ == "__main__":
    import sys
    fx = json.load(open(sys.argv[1]))
    fx.update(FIXTURES)
    cases = []
    for fam, rows in ROWS.items():
        for k, r in enumerate(rows):
            cases.append({"id": "%s+%d" % (fam, k), "args": r["args"], "stdin": r["stdin"], "script": r["script"], "files": fx[r["fixture"]]})
    json.dump(cases, open(sys.argv[2], "w"), indent=1)
    print(len(cases), "cases")
