# Lists roster cases whose a/i/c text reads like an excluded command (y, l, I-modified address ...),
# and ERE cases with ^ or $ away from the ends of the expression.
import json, re, sys
T = sys.argv[1]
sys.path.insert(0, T + "/solution/pysed")
import sed as S
LOOKS = re.compile(r"y/|(^|[;{}\s,0-9$~+])[lwWrRFev](\s|;|$)|/[IM]([,;{\s]|$)")
for n in ("areas.json", "areas_2.json", "mixed_1_2.json", "mixed_3_4.json"):
    for fam, rows in json.load(open(f"{T}/tests/cases/{n}")).items():
        for i, r in enumerate(rows):
            try:
                cmds, _ = S.ScriptParser(r["script"], "-E" in r["opts"]).parse()
            except Exception as exc:
                print("PARSE-FAIL", n, fam, i, repr(r["script"]), exc)
                continue
            for c in cmds:
                if c.name in "aic" and LOOKS.search(c.arg or ""):
                    print("TEXT", n, fam, i, repr(r["script"]), "text=", repr(c.arg))
            if "-E" in r["opts"] and re.search(r"[|(]\^|\$[|)]|[^\\\[]\^.|.\$[^/]", r["script"]):
                print("ERE", n, fam, i, repr(r["script"]))
