#!/usr/bin/env python3
"""gen_sweeps.py: candidate class sweeps for return 09c61abb v1 (sound_verifier, 5 Major + 2 Minor).
Each panel finding named one corner of a class; every class is swept whole here:
  f1 line length       -> sweep_long_lines (lines/pattern spaces of any length) + sweep_long_scripts
  f2, f3 numbers       -> sweep_numbers (every numeric parameter at two or more digits)
  f4 exit status 2     -> sweep_exit_status (unreadable file x every way a run can end)
  f5 anchors           -> sweep_anchors (^ and $ at every position the manual names, BRE and ERE)
  f6 options           -> sweep_options (every order of every subset of -n, -E, -s)
  f7 delimiters        -> sweep_delimiters (every printable character and backslash)
plus the three rev8 sweeps of the same verifier classes (classes over all of ASCII, // after
skipped commands, bracket edges). Writes candidates.json and cand-inputs.json; select.py keeps a
case only when GNU sed exits as the case expects, the output equals any manual-derived
expectation, and the unchanged reference agrees."""
import json

B = "\\"
INPUTS = {
    "long": "a" * 1025 + "\n" + "b" * 4100 + "\n" + "ab" * 700 + "c\n" + "short\n",
    "edge64": "a" * 64 + "\n" + "a" * 65 + "\n" + "b" * 127 + "\n" + "b" * 128 + "\n" + "c" * 257 + "\n" + "d" * 1023 + "\n",
    "n30": "".join(f"{i}\n" for i in range(1, 31)),
    "n11": "".join(f"{i}\n" for i in range(1, 12)),
    "runs": "".join("a" * k + "\n" for k in range(8, 15)) + "".join("ab" * k + "\n" for k in range(9, 13)) + "1111111111111\n",
    "ascii": "".join(chr(i) for i in range(1, 128) if i != 10) + "\nplain text\n",
    "delims": "xax\nqzq\nnothing\n",
    "edges": "-\na\nZ\n]\n.\n/\nd\nb\n!\n,\n^\n%\n",
    "rt": "a\nb\nab\nc\nba\n",
    "anch": "b\nbx\nxb\na\nab\nba\nb$x\na^b\n^b\nb$\nx\n",
}
fam = {}
EXPECT = {}

def add(family, opts, script, inp, files=None, status=0, expect=None, script_arg=False):
    row = {"opts": opts, "script": script, "input": inp}
    if files is not None:
        row["files"] = files
    if script_arg:
        row["script_arg"] = True
    fam.setdefault(family, []).append(row)
    EXPECT[json.dumps(row, sort_keys=True)] = {"status": status, "expect": expect}


def group(family, opts, scripts, inp, k, subst=True):
    """k independent checks in one case. An s check runs on a copy of the pattern space kept in
    the hold space and prints its own result (h once, then s;p;g per check); /re/p checks are
    joined as they are. A check that fails to parse fails the whole case."""
    o = opts if "-n" in opts else opts + ["-n"]
    for n in range(0, len(scripts), k):
        chunk = scripts[n:n + k]
        add(family, o, ("h\n" + "\n".join(f"{s}\np\ng" for s in chunk)) if subst else "\n".join(chunk), inp)

# f1: lines and pattern spaces of any length (a 64-, 128-, 1024- or 4096-character reader fails)
for o, s in [(["-n"], "="), ([], "="), ([], "s/b/X/4000"), ([], "$!N;s/\\n/|/"), ([], "h;G;G;s/\\n/+/g"),
             (["-E", "-n"], "/^(ab){700}c$/="), ([], "N;N;N;P;D"), ([], "s/.*/&&/;s/a\\{2050\\}/two/")]:
    add("sweep_long_lines", o, s, "@long")
group("sweep_long_lines", [], ["s/a*/X/", "s/a/X/1025", "s/\\(ab\\)*/[&]/", "s/^a\\{1025\\}$/A/", "s/.$/</"], "@long", 5)
group("sweep_long_lines", [], ["s/a/X/g", "s/[abcd]/X/g", "s/^a\\{65\\}$/A/", "s/^b\\{128\\}$/B/", "s/c/C/257",
                               "s/.$/</", "s/^./>/", "s/.*/&&&&/;s/.*/&&&&/"], "@edge64", 4)
group("sweep_long_lines", ["-E"], ["s/(.)(.*)(.)/\\3\\2\\1/", "s/d{1023}/D/"], "@edge64", 2)
for s in ["$!N;P;D", "1h;1!H;$!d;x;s/\\n/,/g", "G;s/\\n//"]:
    add("sweep_long_lines", [], s, "@edge64")

# f1, same class on the script side: long regexes, replacements, texts, labels, file names, -e counts
add("sweep_long_scripts", [], "s/" + "a" * 70 + "/X/", "@edge64")
add("sweep_long_scripts", [], "s/a/" + "Y" * 600 + "/", "a\nb\n")
add("sweep_long_scripts", [], "s/" + "b" * 127 + "/[&]/", "@edge64")
add("sweep_long_scripts", [], "1a " + "t" * 400, "x\ny\n")
add("sweep_long_scripts", [], "2i\\\n" + "u" * 300 + "\\\n" + "v" * 200, "x\ny\n")
add("sweep_long_scripts", [], "$c\\\n" + "w" * 1100, "x\ny\n")
lab = "l" * 120
add("sweep_long_scripts", [], f"b {lab}\ns/x/X/\n:{lab}\ns/y/Y/", "x\ny\n")
lab2 = "q" * 70
add("sweep_long_scripts", [], f":{lab2}\ns/aa/a/\nt {lab2}", "a" * 77 + "\n")
add("sweep_long_scripts", ["-n"], "/" + "a\\{0,1\\}" * 30 + "b/p", "b\nab\naab\n" + "a" * 40 + "b\n")
add("sweep_long_scripts", [], "\n".join(f"s/{chr(97 + i % 26)}/{i % 10}/" for i in range(70)), "abcdefghijklmnopqrstuvwxyz\n")
add("sweep_long_scripts", ["-s", "-n"], "$=", "", files=[["f" * 200, "a\nb\n"], ["g" * 150 + ".txt", "c\n"]])
add("sweep_long_scripts", [], "s/" + "\\(a\\)" * 9 + "/\\9\\8\\7\\6\\5\\4\\3\\2\\1/", "a" * 12 + "\n")
add("sweep_long_scripts", ["-E"], "s/(" + "|".join("w%d" % i for i in range(60)) + ")+/<&>/g", " ".join("w%d" % i for i in range(0, 60, 7)) + "\n")
add("sweep_long_scripts", [], "{" * 40 + "s/x/X/" + "}" * 40, "x\n")
add("sweep_long_scripts", [], "$a\\\n" + "\\\n".join("line%d" % i for i in range(60)), "x\n")

# f2, f3: every numeric parameter with more than one digit (each address form in its own case,
# so a misread operand cannot hide behind another command's output)
for s in ["10p", "12,15p", "25,$p", "1,+10p", "3,+12p", "/^5$/,+11p", "3,~10p", "11,~12p", "1~10p", "10~3p",
          "12~12p", "0~10p", "2,~25p", "20,+0p", "15,12p", "28,~10p", "1,+99p", "1,~16p", "13,~13p",
          "14,~13p", "/^3$/,~20p", "2~16p", "29~100p", "12,~100p"]:
    pass
N30 = ["10p", "12,15p", "25,$p", "1,+10p", "3,+12p", "/^5$/,+11p", "3,~10p", "11,~12p", "1~10p", "10~3p",
       "12~12p", "0~10p", "2,~25p", "20,+0p", "15,12p", "28,~10p", "1,+99p", "1,~16p", "13,~13p",
       "14,~13p", "/^3$/,~20p", "2~16p", "29~100p", "12,~100p"]
group("sweep_numbers", [], [s[:-1] + "{=;p}" for s in N30], "@n30", 3, subst=False)
group("sweep_numbers", [], [s[:-1] + "{=;p}" for s in ["1,+10p", "1,~10p", "10,+1p", "10,~11p"]], "@n11", 2, subst=False)
for s, st in [("12q5", 5), ("3q42", 42), ("2Q100", 100), ("q255", 255), ("15{p;q17}", 17), ("11Q12", 12), ("30q200", 200)]:
    add("sweep_numbers", ["-n"] if "{" in s else [], s, "@n30", status=st)
group("sweep_numbers", [], ["s/1/X/12", "s/1/X/10g", "s/1/X/13", "s/a\\{10\\}/X/", "s/a\\{2,12\\}/X/", "s/a\\{11,\\}/X/",
                            "s/\\(ab\\)\\{10\\}/X/", "s/a\\{0,10\\}$/X/", "s/a\\{10,10\\}/X/g", "s/1\\{13\\}/X/"], "@runs", 5)
group("sweep_numbers", ["-E"], ["s/a{10}/X/", "s/a{0,15}$/X/", "s/(ab){10,11}/X/", "s/a{12,}/X/",
                                "s/(a{3}){3,4}/X/", "s/a{10,13}/X/g", "s/b{10}/X/"], "@runs", 4)

# f4: once an unreadable named file is reached the status is 2, however the run then ends
X = None
for opts, script, files in [
        ([], "q", [["missing", X], ["f", "x\n"]]),
        ([], "Q", [["missing", X], ["f", "x\n"]]),
        ([], "q0", [["missing", X], ["f", "x\n"]]),
        ([], "Q5", [["missing", X], ["f", "x\n"]]),
        ([], "2q", [["f", "x\n"], ["missing", X], ["g", "y\nz\n"]]),
        ([], "2Q", [["f", "x\n"], ["missing", X], ["g", "y\nz\n"]]),
        ([], "$!N;q", [["f", "x\n"], ["missing", X], ["g", "y\n"]]),
        ([], "n;q", [["f", "x\n"], ["missing", X], ["g", "y\nz\n"]]),
        (["-n"], "/y/{p;q}", [["missing", X], ["f", "x\ny\nz\n"]]),
        ([], "p", [["f", "x\n"], ["missing", X]]),
        ([], "q", [["missing", X], ["other", X], ["f", "x\n"]]),
        (["-s"], "1q", [["missing", X], ["f", "x\ny\n"]]),
        (["-s"], "N", [["f", "x\n"], ["missing", X], ["g", "y\n"]]),
        ([], "q", [["e", ""], ["missing", X], ["f", "x\n"]]),
        ([], "q", [["missing", X], ["-", X]]),
        ([], "$q3", [["missing", X], ["f", "x\ny\n"]]),
        ([], "Q7", [["missing", X]]),
        ([], "q", [["f", "x\n"], ["missing", X]]),
        ([], "Q", [["f", "x\n"], ["missing", X]])]:
    add("sweep_exit_status", opts, script, "stdin line\n", files=files, status=None)

# f5: ^ and $ at every position the manual gives them (whole regex, subexpression, alternative)
# and as ordinary characters elsewhere in a BRE; ERE anchors only where scope.md keeps them
BRE = ["s/b$\\|x/X/", "s/x\\|b$/X/", "s/^b\\|x/X/", "s/x\\|^b/X/", "s/^b$\\|x/X/", "s/x\\|^b$/X/",
       "s/b$\\|a$/X/", "s/^x\\|^a/X/", "s/\\(b$\\|x\\)/X/", "s/\\(^b\\|x\\)/X/", "s/a\\(b$\\)/X/", "s/\\(^b\\)x/X/",
       "s/\\(\\(b\\)$\\|x\\)/X/", "s/b$x/X/", "s/a^b/X/", "s/b\\$x/X/", "s/\\^b/X/", "s/b$/X/g", "s/^b/X/g",
       "s/x\\|b$\\|a/X/g", "s/\\(x\\|b\\)$/X/", "s/^\\(b\\|x\\)/X/", "s/$/E/", "s/^/S/", "s/^$\\|b/X/"]
ERE = ["s/b$|x/X/", "s/x|b$/X/", "s/^b|x/X/", "s/x|^b/X/", "s/(b$|x)/X/", "s/(^b|x)/X/", "s/a(b$)/X/",
       "s/(^b)x/X/", "s/((b)$|x)/X/", "s/b\\$x/X/", "s/a\\^b/X/", "s/^b$|a/X/g", "s/(x|b)$/X/", "s/^(b|x)/X/"]
group("sweep_anchors", [], BRE, "@anch", 5)
group("sweep_anchors", [], ["/" + s[2:s.index("/X/")] + "/p" for s in BRE if "/X/" in s], "@anch", 6, subst=False)
group("sweep_anchors", ["-E"], ERE, "@anch", 5)
group("sweep_anchors", ["-E"], ["/" + s[2:s.index("/X/")] + "/p" for s in ERE], "@anch", 5, subst=False)
for o, s in [([], "N;s/b$\\|x/X/g"), ([], "N;s/^b\\|a/X/g"), (["-E"], "N;s/b$|x/X/g"), (["-E"], "N;s/^x|b/X/g"),
             ([], "$!N;s/\\n\\|$/|/g"), ([], "N;N;s/^\\|$/#/g")]:
    add("sweep_anchors", o, s, "@anch")

# f6: every order of every non-empty subset of -n, -E and -s, as separate arguments
import itertools
OPTS = ["-n", "-E", "-s"]
subsets = [list(p) for k in (1, 2, 3) for c in itertools.combinations(OPTS, k) for p in itertools.permutations(c)]
for opts in subsets:
    add("sweep_options", opts, "$p;s/a|b$/<&>/p", "", files=[["f1", "a\nb\n"], ["f2", "ab\nb\n"]])
add("sweep_options", ["-s", "-E", "-n"], "1p;$=", "", files=[["f1", "a\nb\n"], ["f2", "c\n"], ["f3", "d\ne\n"]], script_arg=True)
add("sweep_options", ["-E", "-s", "-n", "-e", "1h;$G"], "s/(.)$/[\\1]/p", "", files=[["f1", "a\nb\n"], ["f2", "cd\n"]])
add("sweep_options", ["-n", "-n", "-E", "-s"], "$p", "", files=[["f1", "a\n"], ["f2", "b\n"]])

# f7: every single character as the delimiter of s and of a regex address, backslash included.
# Each s check prints its own line, so the expectation is what the manual says each one does.
def grouped_expect(pairs, text, k):
    return ["".join("".join(l.replace(r, p) + "\n" for r, p in pairs[n:n + k]) for l in text.splitlines())
            for n in range(0, len(pairs), k)]
S, A = [], []
for i in range(32, 127):
    d = chr(i)
    r, p = ("q", "z") if d in "xy" else ("x", "y")
    S.append((f"s{d}{r}{d}{p}{d}g", r, p))
    if d != "n":
        A.append(f"{B}{d}{r}{d}p")
K = 12
for n, want in enumerate(grouped_expect([(r, p) for _s, r, p in S], INPUTS["delims"], K)):
    chunk = [s for s, _r, _p in S[n * K:(n + 1) * K]]
    add("sweep_delimiters", ["-n"], "h\n" + "\n".join(f"{s}\np\ng" for s in chunk), "@delims", expect=want)
group("sweep_delimiters", [], A, "@delims", K, subst=False)
for o in ([], ["-E"]):
    group("sweep_delimiters", o, [f"s{d}x{d}Y{d}" for d in "?+*.[]{}()^$|,:#%@!=~_; "], "xax\n", 8)
group("sweep_delimiters", [], [f"s{d}a{B}{d}x{d}<{B}{d}>{d}" for d in ",:#%@!=~_;| "], "a,x\na:x\na#x\na%x\na@x\na!x\na=x\na~x\na_x\na;x\na|x\na x\n", 6)

# rev8 sweeps of the same classes: character classes over all of ASCII, // after skipped
# commands, bracket expressions whose first or last member is - or ]
CLASSES = ["alnum", "alpha", "blank", "cntrl", "digit", "graph", "lower", "print", "punct", "space", "upper", "xdigit"]
group("sweep_classes", [], [f"s/[[:{c}:]]/./g" for c in CLASSES] + [f"s/[^[:{c}:]]/./g" for c in CLASSES], "@ascii", 6)
group("sweep_classes", ["-E"], [f"s/[[:{c}:]]+/<&>/g" for c in ["cntrl", "punct", "space", "print", "graph", "xdigit"]], "@ascii", 6)
group("sweep_classes", [], ["s/\\w/./g", "s/\\W/./g", "s/\\S/./g", "s/./-/g", "s/[ -~]/./g", "s/[^ -~]/./g",
                            "s/[!-/]/./g", "s/[\\t-\\r]/./g", "s/[[:upper:][:cntrl:]]/./g", "s/[^[:alnum:]_]/./g", "s/\\b/|/g"], "@ascii", 6)
for o, s in [([], "1s/a/a/;2s/b/b/;s//Z/"), ([], "2!s/a/a/;2s/b/b/;s//Z/"), ([], "/a/!s/b/b/;s//Z/"),
             ([], "/c/b end\ns/b/b/;:end\ns//Z/"), ([], "s/b/b/;/a/s//Z/"), ([], "s/a/a/;t x\ns/b/b/;:x\ns//Z/g"),
             (["-n"], "$!s/c/c/;2,3s/b/b/;//p"), ([], "/^a$/{s/a/a/;n};s/b/b/;s//[&]/"),
             ([], "/b/s/a/a/;s//Z/"), ([], "4s/c/c/;s/zz*/-/;s//Z/")]:
    add("sweep_empty_regex", o, s, "@rt")
EDGES = ["/[-a]/p", "/[a-]/p", "/[]-a]/p", "/[^-a]/p", "/[--/]/p", "/[!--]/p", "/[%--]/p", "/[]a]/p",
         "/[^]a]/p", "/[a-c-]/p", "/[-]/p", "/[^-]/p", "/[]-]/p", "/[]]/p", "/[^^]/p", "/[a^]/p"]
for o in ([], ["-E"]):
    group("sweep_bracket_edges", o, [e[:-1] + "{=;p}" for e in EDGES], "@edges", 4, subst=False)

json.dump(fam, open("candidates.json", "w"))
json.dump(INPUTS, open("cand-inputs.json", "w"), indent=1)
json.dump(EXPECT, open("cand-expect.json", "w"))
print({k: len(v) for k, v in fam.items()}, "total", sum(map(len, fam.values())))
