"""Rebuild the rev6 committed corpus: drop out-of-scope rows (by the instrumented scope
scan plus a static argument check), drop the two families that are wholly out of scope,
add the focused v6 cases, prune unused fixtures and rewrite the roster."""
import json, os, sys

CASES = sys.argv[1]
SCOPE = json.load(open(os.path.join(os.path.dirname(__file__), "evidence/scope-scan-returned-corpus.json")))
fixtures = json.load(open(os.path.join(CASES, "fixtures.json")))
roster = json.load(open(os.path.join(CASES, "roster.json")))

def static_out_of_scope(args):
    for a in args:
        if a.startswith("-"):
            if a in ("-", "--") or a.startswith("--") or any(ch not in "Els" for ch in a[1:]):
                return True
    return False

DROP_FAMILIES = {"interactive_global", "odd_files"}
NEW = {
    "addresses": [
        # finding 11: u takes no address
        {"args": ["f.txt"], "fixture": "f_12", "script": "1s/a/A/\n1u\n1p\nQ\n", "stdin": "pipe"},
        {"args": ["-s", "f.txt"], "fixture": "f_12", "script": "1s/a/A/\n1u\n,p\nQ\n", "stdin": "file"},
        # finding 15: joining a marked line invalidates its mark
        {"args": [], "fixture": "no_files_01", "script": "a\nx\ny\n.\n1ka\n1,2j\n'ap\nQ\n", "stdin": "pipe"},
        {"args": [], "fixture": "no_files_01", "script": "a\nx\ny\nz\n.\n2kb\n1,2j\n'bp\n,p\nQ\n", "stdin": "pipe"},
        {"args": [], "fixture": "no_files_01", "script": "a\nx\ny\n.\n1ka\n1,2j\nu\n'ap\nQ\n", "stdin": "pipe"},
        # errata 1 (finding 6): an unset mark fails once the buffer holds a line
        {"args": [], "fixture": "no_files_01", "script": "a\nx\n.\n'a=\nQ\n", "stdin": "pipe"},
        {"args": [], "fixture": "no_files_01", "script": "'a=\na\nx\n.\n'b=\nQ\n", "stdin": "file"},
    ],
    "append_insert_change": [
        # finding 13: input-mode commands honour their print suffix
        {"args": ["-s", "f.txt"], "fixture": "f_09", "script": "1ap\nb\n.\nQ\n", "stdin": "pipe"},
        {"args": ["-s", "f.txt"], "fixture": "f_09", "script": "1in\nb\nc\n.\nQ\n", "stdin": "pipe"},
        {"args": ["-s", "f.txt"], "fixture": "f_12", "script": "1,2cp\nx\ny\n.\n,n\nQ\n", "stdin": "pipe"},
        {"args": ["-s", "f.txt"], "fixture": "f_09", "script": "0ap\n.\n.=\nQ\n", "stdin": "pipe"},
    ],
    "files_and_write": [
        # finding 14: a tab separates the FILE parameter as well as a space
        {"args": ["-s"], "fixture": "no_files_01", "script": "a\nx\n.\nw\tout\nQ\n", "stdin": "pipe"},
        {"args": ["-s", "f.txt"], "fixture": "f_other_02", "script": "$r\tother.txt\n,p\nW\tcopy.txt\nf\tnew.txt\nQ\n", "stdin": "pipe"},
        {"args": ["f.txt"], "fixture": "f_other_02", "script": "e\tother.txt\n,p\nQ\n", "stdin": "pipe"},
        # finding 21: -s also silences E
        {"args": ["-s", "f.txt"], "fixture": "f_other_02", "script": "E other.txt\n,p\nQ\n", "stdin": "pipe"},
        {"args": ["f.txt"], "fixture": "f_other_02", "script": "2d\nE other.txt\n,p\nQ\n", "stdin": "pipe"},
    ],
    "substitute": [
        # finding 17: an omitted final delimiter prints the last line affected
        {"args": ["f.txt"], "fixture": "f_12", "script": "1,2s/[ab]/<&>\nQ\n", "stdin": "pipe"},
        {"args": ["-s", "f.txt"], "fixture": "f_31", "script": ",s/[ac]/X\n.=\nQ\n", "stdin": "pipe"},
        # finding 18: the repeat form takes g, a count, p and r only
        {"args": [], "fixture": "no_files_01", "script": "a\nx\n.\ns/x/y/\nsn\n,p\nQ\n", "stdin": "pipe"},
        {"args": [], "fixture": "no_files_01", "script": "a\nxx\n.\ns/x/y/\nsgp\nsN\nQ\n", "stdin": "pipe"},
    ],
    "regex": [
        # finding 12: a bounded repeat may have a lower bound of zero
        {"args": ["-s", "f.txt"], "fixture": "f_13", "script": "g/a\\{0\\}/p\nQ\n", "stdin": "pipe"},
        {"args": ["-s", "f.txt"], "fixture": "f_20", "script": "g/ab\\{0,1\\}$/p\n,s/b\\{0\\}/-/g\n,p\nQ\n", "stdin": "pipe"},
        # finding 3: a leading or trailing hyphen in a bracket is literal
        {"args": [], "fixture": "no_files_01", "script": "a\na\n0\n-\n.\ng/[-a]/p\nQ\n", "stdin": "pipe"},
        {"args": [], "fixture": "no_files_01", "script": "a\na\n0\n-\n.\ng/[a-]/p\nv/[^-a]/p\nQ\n", "stdin": "pipe"},
    ],
    "global_commands": [
        # errata 18 (finding 4): an s without a match inside a global list is not an error
        {"args": ["-s"], "fixture": "no_files_01", "script": "a\na\nb\n.\ng/./s/a/A/\n,p\nQ\n", "stdin": "file"},
        {"args": ["-s"], "fixture": "no_files_01", "script": "a\na\nb\n.\ng/./s/zzz/y/\\\np\nQ\n", "stdin": "file"},
        {"args": ["-s"], "fixture": "no_files_01", "script": "a\nb\nc\n.\ng/./s/b/B/\n.=\nu\n,p\nQ\n", "stdin": "pipe"},
    ],
}

used = set()
new_roster = {}
dropped = {}
for family in sorted(roster["families"]):
    path = os.path.join(CASES, family + ".jsonl")
    rows = [json.loads(line) for line in open(path) if line.strip()]
    os.remove(path)
    if family in DROP_FAMILIES:
        dropped[family] = len(rows)
        continue
    keep = [r for i, r in enumerate(rows)
            if not SCOPE[f"{family}:{i}"] and not static_out_of_scope(r["args"])]
    dropped[family] = len(rows) - len(keep)
    keep += NEW.get(family, [])
    if not keep:
        continue
    for r in keep:
        used.add(r["fixture"])
    with open(path, "w", encoding="utf-8") as out:
        for r in keep:
            out.write(json.dumps(r, ensure_ascii=True) + "\n")
    new_roster[family] = len(keep)
for family in NEW:
    assert family in new_roster, family
missing = used - set(fixtures)
assert not missing, missing
fixtures = {k: v for k, v in sorted(fixtures.items()) if k in used}
with open(os.path.join(CASES, "fixtures.json"), "w", encoding="utf-8") as out:
    json.dump(fixtures, out, indent=1, ensure_ascii=True)
    out.write("\n")
roster = {"families": new_roster, "fixtures": len(fixtures), "total": sum(new_roster.values())}
with open(os.path.join(CASES, "roster.json"), "w", encoding="utf-8") as out:
    json.dump(roster, out, indent=1)
    out.write("\n")
print(json.dumps({"dropped": dropped, "roster": roster}, indent=1))
