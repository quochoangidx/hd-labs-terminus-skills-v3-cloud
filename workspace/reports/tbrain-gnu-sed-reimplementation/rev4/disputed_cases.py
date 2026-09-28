# Prints the returned-roster cases that already exercise what v5 findings 31, 36 and 40 say is untested.
import json, os, sys
T = sys.argv[1]
inputs = json.load(open(os.path.join(T, "tests/cases/inputs.json")))
want = {
    "31 $ after N in a multi-line space": "s/e/E/;N;tx;s/$/ nx/;b;:x;s/$/ x/",
    "36 BRE exact interval": "/^.\\{5\\}$/p",
    "40 } followed by ;": "1{h;d};G;s/\\n/ /;h;$!d",
}
for n in sorted(os.listdir(os.path.join(T, "tests/cases"))):
    if n == "inputs.json":
        continue
    for fam, rows in json.load(open(os.path.join(T, "tests/cases", n))).items():
        for c in rows:
            for label, script in want.items():
                if c["script"] == script:
                    inp = inputs.get(c["input"][1:], c["input"]) if c["input"].startswith("@") else c["input"]
                    print(f"{label}: {n} {fam} opts={c['opts']} script={script!r} input={inp[:40]!r}")
