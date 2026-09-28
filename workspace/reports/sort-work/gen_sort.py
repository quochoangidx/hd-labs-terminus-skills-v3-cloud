import random, json
C = []  # {"group","args","stdin","files"}
def c(group, args, stdin="", files=None):
    C.append({"group": group, "args": args, "stdin": stdin, "files": files or {}})
L = lambda *xs: "".join(x + "\n" for x in xs)
tab = L("  b 10 x", " a  9 y", "c 100 z", "\tb 2 w", "a 9 x", "  a  10 v")
for a in (["-k2,2"], ["-k2"], ["-k2b,2"], ["-b", "-k2,2"], ["-k2,2b"], ["-k2.2,2.2"], ["-k2.2b,2.2"], ["-k1.2,1.3"], ["-k1.1,1.1"], ["-k3,3n"], ["-k2,2n"], ["-k2n", "-k3"], ["-k3.1b,3.1b"], ["-k1,1", "-k3,3r"], ["-k2,1"], ["-k2.3,2.1"], ["-k2.5"], ["-k5"], ["-k1.10,1"], ["-k 2,2", "-k 1,1"], ["-bk2,2"], ["-k2,2.0"], ["-k2,3.1"]):
    c("keys_and_blanks", a, tab)
csv = L("x:10:b:", "y::a:q", ":9:c:", "x:9:b:p", "y:10::", "z", "x:010:b:r", "a:b:c:d:e")
for a in (["-t:", "-k2,2"], ["-t:", "-k2,2n"], ["-t", ":", "-k3,3", "-k1,1"], ["-t:", "-k2"], ["-t:", "-k4,4r"], ["-t:", "-k2.2,2.2"], ["-t:", "-k5"], ["-t:", "-k3,4"], ["-t", " ", "-k2,2"], ["-t:", "-k1,1", "-u"], ["-t:", "-k2n,2", "-k1,1r"]):
    c("separator", a, csv if a[1] != " " else L(" foo bar", "foo  bar", "  a b", "a b", " b a"))
dup = L("b 1", "a 2", "b 1 ", "a 1", "A 2", "b 01", "a 2", "a 10")
for a in (["-k1,1"], ["-k1,1", "-s"], ["-k1,1", "-r"], ["-k1,1r"], ["-r", "-k1,1"], ["-r", "-k2,2n"], ["-k2,2n"], ["-k2,2n", "-s"], ["-n", "-k2,2"], ["-r", "-k2,2n", "-k1,1"], ["-f", "-k1,1"], ["-fk1,1", "-s"], ["-r"], ["-rs"], ["-s"], ["-k2n", "-r"], ["-n", "-r", "-k2,2", "-k1,1f"], ["-b", "-k2,2r"], ["-k1,1", "-k2,2nr", "-r"]):
    c("global_and_key_options", a, dup)
nums = L("10", " 9", "-5", "-0", "0", "", ".5", "-.5", "0.50", "1,000", "999", "+5", "1e3", "  -3.20", "3.2", "abc", "007", "7", "-", "--5", "0.", "-0.0", "12a", "1.2.3")
for a in (["-n"], ["-nr"], ["-n", "-s"], ["-nu"], ["-n", "-k1,1"], ["-g"], ["-gr"], ["-gu"], ["-g", "-s"], ["-h"], ["-hu"]):
    c("numeric", a, nums)
gnum = L("0x10", "16", "0X1F", "1e1", "inf", "-inf", "nan", "-nan", "INF", "Infinity", "  2.5", "abc", "", "-0", "0", "1e-2", "0.01", ".5e1", "0x.8p1", "1e", "x1", "+3", "-1e1", "0x", "9", "1.5E+1")
for a in (["-g"], ["-g", "-s"], ["-gr"], ["-gu"], ["-g", "-k1,1"], ["-n"]):
    c("general_numeric", a, gnum)
hum = L("2000", "1K", "1k", "1023M", "1G", "0.5G", "-1K", "-1M", "-2000", "0", "0K", "1.5K", "1500", "3m", "3M", "2T", "1P", "1E", "1Z", "1Y", "", "K", "-", "10", "  4K", "1KB", "999", "-0.1", "1,5K")
for a in (["-h"], ["-hr"], ["-h", "-s"], ["-hu"], ["-h", "-k1,1"], ["-n"]):
    c("human_numeric", a, hum)
mon = L("feb", " jan", "January", "DEC", "Dece", "xyz", "", "Ja", "mar 3", "MAR 1", "\tapr", "may", "jun", "jul", "Aug", "sEp", "oct", "nov", "dec", "janx", "1jan", "FEBRUARY", "  Nov")
for a in (["-M"], ["-Mr"], ["-M", "-s"], ["-Mu"], ["-M", "-k1,1", "-k2,2n"], ["-k1,1M"], ["-fM"]):
    c("month", a, mon)
ver = L("1.10", "1.9", "1.9a", "1.9.1", "1.09", "1.009", "a1b2", "a01b2", "1.0~rc1", "1.0", "1.0~", "1.0-1", "1.0.0", ".hidden", ".", "..", "file.tar.gz", "file-1.2.tar.gz", "file-1.10.tar.gz", "file-1.2a.tar.gz", "~a", "a~", "a", "A", "_1", "1_", "", "2", "10", "x-1.2~beta.txt", "x-1.2.txt", "0", "00", "abc.1.so", "abc.10.so", "z.9", "z.a", "v1.2.3-rc.1", "v1.2.3")
for a in (["-V"], ["-Vr"], ["-V", "-s"], ["-Vu"], ["-V", "-f"], ["-k1,1V"], ["-t.", "-k2,2V"]):
    c("version", a, ver)
dic = L("b-c", "bc", "b c", "B c", "\x01bc", "b\x7fc", "a.b", "ab", "a\tb", "_x", "x_", "Ab", "aB", "ab ", "a,b", "a~b", "")
for a in (["-d"], ["-i"], ["-f"], ["-df"], ["-fi"], ["-di"], ["-dfu"], ["-fu"], ["-iu"], ["-du"], ["-k1,1d"], ["-dr"], ["-f", "-s"], ["-d", "-s"]):
    c("dictionary_fold_nonprinting", a, dic)
uni = L("b 1", "a 1", "B 1", "a 01", "a 1", "c 2", "c  2", " c 2", "b 1")
for a in (["-u"], ["-u", "-k2,2"], ["-u", "-k2,2n"], ["-u", "-k1,1"], ["-u", "-r"], ["-un", "-k2"], ["-u", "-b", "-k1,1"], ["-u", "-k1,1", "-k2,2n"], ["-us"], ["-u", "-s", "-k2,2"], ["-uk2b,2", "-r"]):
    c("unique", a, uni)
for a in (["-z"], ["-zr"], ["-zn"], ["-z", "-k2,2"], ["-zu"], ["-z", "-t", " ", "-k2,2n"]):
    c("zero_terminated", a, "b 2\na\x00a 10\x00c 1\x00\x00b 2\na\x00a 9")
chk = [L("a", "b", "b", "c"), L("a", "c", "b"), L("1", "10", "9"), L("1", "9", "10"), "", L("b", "a"), L("a", "a")]
for inp in chk:
    for a in (["-c"], ["-C"], ["-cn"], ["-Cu"], ["-cr"], ["-C", "-k1,1"]):
        c("check", a, inp)
F = {"f1": L("b", "a 2", "c"), "f2": "z\ny", "f3": "", "f4": L("a 10", "a 9")}
for a in (["f1", "f2"], ["f2", "f1"], ["f2"], ["f3"], ["-", "f1"], ["f1", "-", "f4"], ["-n", "-k2,2", "f1", "f4", "-"], ["missing"], ["f1", "missing"], ["-u", "f1", "f1"], ["-c", "f2"], ["f4", "-r"], []):
    c("files_and_stdin", a, "m\nk", F)
for a in (["-r"], ["-n"], [], ["-u"]):
    c("files_and_stdin", a, "no newline\nlast")
    c("files_and_stdin", a, "")
# random mixed tables
rng = random.Random(4)
words = ["apple", "Apple", "b", "banana", "BANANA", "cherry", "a-b", "a b", "zeta", "Z", "_x", "x~", "mid"]
def rnum():
    return rng.choice(["0", "-0", "1", "01", "10", "9", "-3", "2.5", "2.50", "-2.5", ".7", "", "100", "1e2", "0x1A", "3K", "2k", "1M", "999", "-1K", "nan", "inf", "5", "12", "007"])
def rver():
    return rng.choice(["1.2", "1.10", "1.2.1", "1.02", "2", "1.2~rc", "1.2a", "1.2-1", "v1", "x.tar.gz", "x-1.tar.gz", ".h", "10"])
def rmon():
    return rng.choice(["jan", "FEB", "mar", "Apr", "dec", "xyz", "Nov", " may", "JUL"])
KEYOPTS = ["", "", "", "n", "r", "b", "f", "d", "g", "h", "M", "V", "nr", "fr", "bn", "i", "bf", "dfr"]
for i in range(140):
    sep = rng.choice([None, None, ":", ","])
    rows = []
    for _ in range(rng.randint(5, 16)):
        cols = [rng.choice(words), rnum(), rver(), rmon(), rng.choice(words) + rnum()]
        rng.shuffle(cols)
        cols = cols[:rng.randint(1, 5)]
        if sep: line = sep.join(cols)
        else: line = "".join(rng.choice([" ", " ", "  ", "\t"]) + x if j or rng.random() < 0.3 else x for j, x in enumerate(cols))
        rows.append(line)
    if rng.random() < 0.3: rows += rng.sample(rows, 2)
    args = []
    if sep: args += ["-t" + sep] if rng.random() < 0.5 else ["-t", sep]
    for _ in range(rng.choice([0, 1, 1, 2, 2, 3])):
        f1 = rng.randint(1, 4); s = f"{f1}"
        if rng.random() < 0.3: s += f".{rng.randint(1, 3)}"
        s += rng.choice(KEYOPTS)
        if rng.random() < 0.7:
            f2 = rng.randint(f1, 5); e = f"{f2}"
            if rng.random() < 0.25: e += f".{rng.randint(0, 3)}"
            e += rng.choice(["", "", "b", rng.choice(KEYOPTS)])
            s += "," + e
        args += rng.choice([["-k" + s], ["-k", s]])
    g = "".join(rng.sample("bdfinrsuMghV", rng.choice([0, 0, 1, 1, 2])))
    for bad in ("gh", "hg", "nM", "Mn", "gM", "Mg", "gn", "ng", "hn", "nh", "hM", "Mh", "Vn", "nV", "Vg", "gV", "Vh", "hV", "VM", "MV", "di", "id"):
        pass
    kinds = [k for k in "nghMV" if k in g]
    if len(kinds) > 1:
        g = g.replace(kinds[1], "")
    if g: args = ["-" + g] + args
    C.append({"group": f"mixed_{i % 4 + 1}", "args": args, "stdin": L(*rows), "files": {}})
json.dump(C, open("cases_raw.json", "w"))
print(len(C))
