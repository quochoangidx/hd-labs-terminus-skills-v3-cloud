#!/usr/bin/env python3
"""gen_sweeps.py OUT_CASES OUT_INPUTS_ADDITIONS: rev8 class sweeps (panel v8 findings 1-5, 7, 9).
Every candidate case is run through GNU sed 4.9 (container sedlab); a case is kept only when
sed exits 0 (or the q/Q code it names) and, for sweeps with a manual-derived expectation, when
sed's output equals what the manual says. Cases are then compared with the reference."""
import json, subprocess, sys

B = "\\"
INPUTS = {
    "long": "a" * 1025 + "\n" + "b" * 4100 + "\n" + "ab" * 700 + "c\n" + "short\n",
    "n30": "".join(f"{i}\n" for i in range(1, 31)),
    "runs": "".join("a" * k + "\n" for k in range(8, 15)) + "".join("ab" * k + "\n" for k in range(9, 13)) + "1111111111111\n",
    "ascii": "".join(chr(i) for i in range(1, 128) if i != 10) + "\nplain text\n",
    "delims": "xax\nqzq\nnothing\n",
    "edges": "-\na\nZ\n]\n.\n/\nd\nb\n!\n,\n^\n%\n",
    "rt": "a\nb\nab\nc\nba\n",
}

def sed(args, inp):
    p = subprocess.run(["docker", "exec", "-i", "-e", "LC_ALL=C", "-w", "/tmp", "sedlab", "sed"] + args,
                       input=inp.encode("latin-1"), capture_output=True)
    return p.stdout.decode("latin-1"), p.returncode

fam = {k: [] for k in ("sweep_long_lines", "sweep_numbers", "sweep_classes", "sweep_delimiters",
                       "sweep_empty_regex", "sweep_bracket_edges")}
dropped = []

def add(family, opts, script, inp, expect=None, status=0):
    out, rc = sed(opts + ["-e", script], INPUTS[inp[1:]] if inp.startswith("@") else inp)
    if rc != status or (expect is not None and out != expect):
        dropped.append((family, opts, script, rc, out[:60], None if expect is None else expect[:60]))
        return
    fam[family].append({"opts": opts, "script": script, "input": inp})

# 1. arbitrarily long lines and pattern spaces
for o, s in [(["-n"], "="), ([], "="), (["-n"], "p"), ([], "s/a*/X/"), ([], "s/b/X/4000"), ([], "s/a/X/1025"),
             ([], "$!N;s/\\n/|/"), ([], "h;G;G;s/\\n/+/g"), (["-n"], "/^a\\{1025\\}$/p"), (["-E", "-n"], "/^(ab){700}c$/="),
             ([], "s/\\(ab\\)*/[&]/"), (["-n"], "$p;1l"[:2]), ([], "N;N;N;P;D"), ([], "s/.*/&&/;s/a\\{2050\\}/two/")]:
    add("sweep_long_lines", o, s, "@long")

# 2. every numeric parameter with more than one digit
for s in ["10p", "12,15p", "25,$p", "1,+10p", "3,+12p", "/^5$/,+11p", "3,~10p", "11,~12p", "1~10p", "10~3p",
          "12~12p", "0~10p", "2,~25p", "20,+0p", "/^7$/,+10p", "15,12p", "28,~10p", "$!{25~2p}"]:
    add("sweep_numbers", ["-n"], s, "@n30")
for s, st in [("12q", 0), ("12q5", 5), ("3q42", 42), ("2Q100", 100), ("q255", 255), ("15{p;q17}", 17), ("11Q12", 12)]:
    add("sweep_numbers", ["-n"] if "{" in s else [], s, "@n30", status=st)
for o, s in [([], "s/1/X/12"), ([], "s/1/X/10g"), ([], "s/1/X/13"), ([], "s/1/X/14"),
             ([], "s/a\\{10\\}/X/"), ([], "s/a\\{2,12\\}/X/"), ([], "s/a\\{11,\\}/X/"), ([], "s/\\(ab\\)\\{10\\}/X/"),
             ([], "s/a\\{0,10\\}$/X/"), (["-E"], "s/a{10}/X/"), (["-E"], "s/a{0,15}$/X/"), (["-E"], "s/(ab){10,11}/X/"),
             (["-E"], "s/a{12,}/X/"), (["-n"], "/^a\\{10,12\\}$/p"), (["-n", "-E"], "/^(ab){11}$/p"), (["-E"], "s/(a{3}){3,4}/X/")]:
    add("sweep_numbers", o, s, "@runs")

# 3. every character class over the whole of ASCII (all bytes 1-127 but newline)
CLASSES = ["alnum", "alpha", "blank", "cntrl", "digit", "graph", "lower", "print", "punct", "space", "upper", "xdigit"]
for c in CLASSES:
    add("sweep_classes", [], f"s/[[:{c}:]]/./g", "@ascii")
    add("sweep_classes", [], f"s/[^[:{c}:]]/./g", "@ascii")
for c in ["cntrl", "punct", "space", "print", "graph", "xdigit"]:
    add("sweep_classes", ["-E"], f"s/[[:{c}:]]+/<&>/g", "@ascii")
for s in ["s/\\w/./g", "s/\\W/./g", "s/\\s/./g", "s/\\S/./g", "s/./-/g", "s/[ -~]/./g", "s/[^ -~]/./g",
          "s/[!-/]/./g", "s/[\\t-\\r]/./g", "s/[[:upper:][:cntrl:]]/./g", "s/[^[:alnum:]_]/./g", "s/\\b/|/g"]:
    add("sweep_classes", [], s, "@ascii")

# 5. every single character as the delimiter of s and of a regex address, backslash included
def subst_expect(r, p, text):
    return "".join(l.replace(r, p) + "\n" for l in text.splitlines())
for i in list(range(32, 127)):
    d = chr(i)
    r, p = ("q", "z") if d in "xy" else ("x", "y")
    add("sweep_delimiters", [], f"s{d}{r}{d}{p}{d}g", "@delims", expect=subst_expect(r, p, INPUTS["delims"]))
    if d != "n":
        want = "".join(l + "\n" for l in INPUTS["delims"].splitlines() if r in l)
        add("sweep_delimiters", ["-n"], f"{B}{d}{r}{d}p", "@delims", expect=want)
for d in ",:#%@!=~_;| ":
    add("sweep_delimiters", [], f"s{d}a{B}{d}x{d}<{B}{d}>{d}", f"a{d}x\nxa{d}xa{d}x\n", expect=f"<{d}>\nx<{d}>a{d}x\n")

# 9. // reuses the regex last used while the script runs, not the one written before it
for o, s in [([], "1s/a/a/;2s/b/b/;s//Z/"), ([], "2!s/a/a/;2s/b/b/;s//Z/"), ([], "/a/!s/b/b/;s//Z/"),
             ([], "/c/b end;s/b/b/;:end;s//Z/"), ([], "s/b/b/;/a/s//Z/"), ([], "s/a/a/;t x;s/b/b/;:x;s//Z/g"),
             (["-n"], "$!s/c/c/;2,3s/b/b/;//p"), ([], "/^a$/{s/a/a/;n};s/b/b/;s//[&]/"),
             ([], "/b/s/a/a/;s//Z/"), ([], "4s/c/c/;s/zz*/-/;s//Z/")]:
    add("sweep_empty_regex", o, s, "@rt")

# 7. bracket expressions whose first or last member is a hyphen, or which begin with ]
for s in ["/[-a]/p", "/[a-]/p", "/[]-a]/p", "/[^-a]/p", "/[--/]/p", "/[!--]/p", "/[%--]/p", "/[]a]/p",
          "/[^]a]/p", "/[a-c-]/p", "/[-]/p", "/[^-]/p", "/[]-]/p", "/[]]/p", "/[^^]/p", "/[a^]/p"]:
    add("sweep_bracket_edges", ["-n"], s, "@edges")
    add("sweep_bracket_edges", ["-n", "-E"], s, "@edges")

out_cases, out_inputs = sys.argv[1:3]
with open(out_cases, "w") as f:
    f.write("{\n")
    items = list(fam.items())
    for n, (k, rows) in enumerate(items):
        f.write(json.dumps(k) + ": [\n" + ",\n".join(json.dumps(r) for r in rows) + "\n]" + (",\n" if n < len(items) - 1 else "\n"))
    f.write("}\n")
json.dump(INPUTS, open(out_inputs, "w"), indent=1)
print({k: len(v) for k, v in fam.items()}, "total", sum(map(len, fam.values())))
for d in dropped:
    print("DROPPED", d)
