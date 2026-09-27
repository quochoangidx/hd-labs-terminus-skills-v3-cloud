import json, random, sys
C = []
def c(group, script, mode="e", stdin="", files=None, args=None):
    if args is None:
        args = ["-e", script] if mode == "e" else ["-f", "s.dc"] if mode == "f" else []
        if mode == "f": files = dict(files or {}, **{"s.dc": script})
        if mode == "stdin": stdin = script + stdin
    C.append({"group": group, "args": args, "stdin": stdin, "files": files or {}})
def many(g, ss, **kw):
    for s in ss: c(g, s, **kw)
many("printing", ["1 2 3 f", "5p", "5n 6n", "[hello]p", "[hi]n", "[abc]P", "65P", "16706P 10P", "0P", "_65P", "256 65 * 66 + P", "1.9P", "[a]p [b]f", "3.14159p", "_0.5p", ".5p", "0.000p", "007p", "1 0 / p", "f", "c f", "12345678901234567890123456789012345678901234567890123456789012345678901234567890p", "2 300^p", "_2 301^p", "1 7 k 3/p"])
many("arithmetic", ["2 3+p", "2 3-p", "_2 3*p", "7 2/p", "7 2%p", "_7 2%p", "7 _2%p", "7 2~f", "_7 2~f", "2 10^p", "2 _2^p", "4k 2 _2^p", "2 0.5^p", "3k 2 0.5^p", "2vp", "9vp", "4k 2vp", "4k 0.0004vp", "_4vp", "0vp", "3 4 5|p", "_3 4 5|p", "3 _1 5|p", "3 4 0|p", "5k 1 3/p", "5k _1 3/p", "1.5 2.25*p", "3k 1.5 2.25*p", "1.123456 1.1*p", "10k 1.123456 1.1*p", "1 0/p", "1 0%p", "5 0~f", "2 1000000^ Zp", "3k 10 3/ 3*p", "0.1 0.2+p", "_0.0 p", "2k 1 3 / 3 * p", "1.10 1.100+p", "100 0.5^p", "4k 2.5 3^p", "4k 2.5 _3^p", "1.5 3^p"])
many("stack_control", ["1 2 3 c f", "1 d f", "1 2 r f", "1 r f", "d", "r", "1 2 3 4 5 z p", "z p", "1 2 3 R f" if False else "1 2 3 c z p", "[a] d f", "1 2 3 cp"])
many("registers", ["5 sa la p la p", "5 sa 6 sa la p", "la p", "1 Sa 2 Sa La p La p", "1 Sa 2 Sa La La f", "La", "1 sa 2 Sa la p Sa f" if False else "1 sa 2 Sa la p La p la p", "5 sa [x] Sa la p", "1 Sa La La p", "3 s. l. p", "3 s  l  p", "1 2 s1 l1 p", "[abc] sx lx p"])
many("arrays", ["5 0:a 0;a p", "5 3:a 2;a p", "1 0:A 0SA 2 0:A LA 0;Ap", "7 1:b 1;b 1;b + p", "0;z p", "5 _1:a", "[s] 2:a 2;a p", "5 1.9:a 1;a p", "1 0:a 2 0Sa 0;a p La 0;a p", "9 100:a 100;a p 99;a p"])
many("parameters", ["16 o 255 p", "2 o 10 p", "16 i FF p", "16 i ff p", "2 i 1011 p", "16 o _255 p", "16 o 0.5 p", "2 o 0.5 p", "3 o 10 p", "3 o 0.1 p", "100 o 12345 p", "1000 o 123456789 p", "17 o 300 p", "16 o 1.1 p", "5k 16 o 1.1 p", "16 i A p", "10 i F p", "16i 1.8p", "8 i 17 p", "I p O p K p", "16 o O p", "5 k K p", "1 o 5 p", "17 i I p", "1 i I p", "_1 k K p", "2.5 k K p", "16 o 12345678901234567890 p", "2 o 12345678901234567890123 p", "16 i 10 i I p", "16 i A0 o 300 p"])
many("strings", ["[1 2+p]x", "[1 2+p] sa la x la x", "[[nested]p]x", "[a[b]c]p", "[]p", "[5]x p", "5 x p", "[p] 3 r x", "[3 4] x f", "[a]Z p", "[abc]X p", "[1p]sa [2p]sb 1 2 <a", "[1p]sa [2p]sb 2 1 <a", "[1p]sa 1 1 =a", "[1p]sa 1 2 =a", "[1p]sa 1 2 !=a", "[1p]sa 1 2 >a", "[1p]sa 2 1 >a", "[1p]sa 1 2 !<a", "[1p]sa 1 2 !>a", "[1p]sa 2 2 !<a", "[x]sa [1p] 1 1 =a", "[q]sa 1 1 =a 5p", "[pq]sq 1 2 3 lqx 9p", "[2Q]sa [lax 7p]sb lbx 8p", "[3Q]sa [lax 7p]sb lbx 8p", "[1Q]sa lax 5p", "[0Q]sa lax 5p", "[_1Q]sa lax 5p", "q 5p", "[q]x 5p", "[[q]x 6p]x 5p", "[li1+dsi p li 5>a]sa 0si lax", "[[q]sq li 3=q li1+si li p lbx]sb 0si lbx 9p", "0 sn [ln 1+ sn ln p ln 4>m]sm lmx", "[ln d p 1- d sn 0<m]sm 5sn lmx", "65 a p", "[abc] a p", "256 65 * 66 + a p", "_65 a p", "0 a Z p", "[1 2 3 4 5 6 7 8 9]x f"])
many("status_inquiry", ["123 Z p", "0.00123 Z p", "_123.45 Z p", "0 Z p", "123.450 X p", "5 X p", "[str] X p", "1 2 3 z p", "0.000 Z p", "1.00 Z p", "100 Z p", "2 100^ Z p", "3k 1 3/ X p", "3k 1 3/ Z p", "16 i FF Z p"])
many("misc_and_comments", ["1 # comment 2p\n3p", "5p #x\n6p", "? p", "[6p] ? x"], stdin="7\n")
many("misc_and_comments", ["1 2 + ? p", "? ? f"], stdin="3 4 +\n[x]\n")
many("errors_and_recovery", ["p 5p", "+ 5p", "1 + p", "5 0/ p 7p", "1 0% p", "Q 5p", "_1v 4p", "1 0.5 | p", "x 3p", "[abc] 1 + p", "5 [a] * f", "0 i I p", "17 i I p", "1 o O p", "_1 k K p", "[q] sq 1 2 <q 5p", "5 X Z z f", "; p", "lz p", "Lz p", "3 sa 1 2 <a 5p", "4 5 6 [x] 7 R f" if False else "4 5 6 Y f", "1 2 ` f", "3.4.5 p"])
# options and files
c("options_and_files", "", args=["-e", "1 2 +p", "-e", "3p"])
c("options_and_files", "", args=["-e", "[x]sa", "-e", "lap"])
c("options_and_files", "", args=["-f", "a.dc"], files={"a.dc": "1 2 + p\n"})
c("options_and_files", "", args=["-f", "a.dc", "-e", "p"], files={"a.dc": "5 6\n"})
c("options_and_files", "", args=["-e", "7", "-f", "a.dc"], files={"a.dc": "p\n"})
c("options_and_files", "", args=["a.dc", "b.dc"], files={"a.dc": "5 sa\n", "b.dc": "la p\n"})
c("options_and_files", "", args=["a.dc"], files={"a.dc": "5 p q 6 p\n"}, stdin="9p\n")
c("options_and_files", "", args=[], stdin="1 2 + p\n")
c("options_and_files", "", args=["missing.dc"], stdin="")
c("options_and_files", "", args=["a.dc", "missing.dc", "b.dc"], files={"a.dc": "1p\n", "b.dc": "2p\n"})
c("options_and_files", "", args=["-e", "5p", "-"], stdin="6p\n")
c("options_and_files", "", args=["-f", "-"], stdin="8p\n")
c("options_and_files", "", args=["-e", "[unterminated"], stdin="")
c("options_and_files", "", args=["a.dc"], files={"a.dc": "[multi\nline string]p\n"})
c("options_and_files", "", args=["a.dc"], files={"a.dc": "1 2\n+\np"})
# random programs
rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
def num():
    r = rng.random()
    if r < 0.4: return str(rng.randint(0, 20))
    if r < 0.55: return "_" + str(rng.randint(1, 50))
    if r < 0.75: return f"{rng.randint(0, 99)}.{rng.randint(0, 999):0{rng.randint(1, 3)}d}"
    if r < 0.85: return str(rng.randint(10**15, 10**30))
    return rng.choice(["0", ".5", "_.25", "1.000", "0.0001", "3.14159265358979"])
OPS = ["+", "-", "*", "/", "%", "~", "^", "v", "|", "d", "r", "c", "z", "Z", "X", "p", "n", "f", "P"]
def prog():
    parts = []
    if rng.random() < 0.4: parts.append(f"{rng.randint(0, 12)}k")
    if rng.random() < 0.25: parts.append(f"{rng.choice([2, 3, 8, 16, 7, 100, 1000])}o")
    for _ in range(rng.randint(4, 14)):
        r = rng.random()
        if r < 0.35: parts.append(num())
        elif r < 0.7:
            op = rng.choice(OPS)
            if op == "^": parts.append(str(rng.randint(-3, 6)).replace("-", "_") + " ^")
            elif op == "|": parts.append(f"{rng.randint(1, 30)} |")
            elif op == "P": parts.append(rng.choice(["[s]P", "65P", "P"]))
            else: parts.append(op)
        elif r < 0.78: parts.append(rng.choice(["sa", "la", "Sa", "La", "sb", "lb", "3:a", "3;a", "0:b", "0;b"]))
        elif r < 0.84: parts.append(rng.choice(["[lap]sm", "lmx", "[d*]x", "[1+]sm 5 lmx", "[2Q]x", "[q]sq"]))
        elif r < 0.9: parts.append(rng.choice(["[3p]st", "1 2 <t", "2 1 <t", "1 1 =t", "1 2 !=t", "3 3 !>t"]))
        elif r < 0.95: parts.append(rng.choice(["K p", "O p", "I p", "z p"]))
        else: parts.append(rng.choice(["[abc]", "[x y]", "[]"]))
    parts.append("f")
    return " ".join(parts)
N = int(sys.argv[2]) if len(sys.argv) > 2 else 200
for i in range(N):
    c(f"mixed_{i % 4 + 1}", prog(), mode=rng.choice(["e", "e", "f", "stdin"]))
json.dump(C, open(sys.argv[3] if len(sys.argv) > 3 else "cases_raw.json", "w")); print(len(C))
