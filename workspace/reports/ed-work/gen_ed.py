import json, random, sys
C = []
TXT = "".join(f"{w}\n" for w in ["alpha one", "beta two", "gamma three", "delta four", "epsilon five", "zeta six", "eta seven", "theta eight", "iota nine", "kappa ten"])
TAB = "a\tb  c\nfoo bar foo\nxx\n\n  lead\ntrail  \nfoofoo\nbar\n"
def c(group, script, args=("-s", "f.txt"), files=None, stdin="pipe"):
    C.append({"group": group, "script": script, "args": list(args), "files": files if files is not None else {"f.txt": TXT}, "stdin": stdin})
def many(group, scripts, **kw):
    for s in scripts: c(group, s, **kw)
# addressing
many("addresses", [",p\n", "p\n", ".p\n", "$p\n", "1p\n3,5p\n", "2;+2p\n", "3,+2n\n", "-p\n--p\n", "4\n+p\n++p\n", "4\n-2,+1p\n", "/two/p\n", "?six?p\n", "5\n/e/p\n//p\n", "5\n?a?p\n??p\n", ";p\n", ",n\n", "2,p\n", ",4p\n", "3;p\n", "0;/alpha/p\n", "1,2,3,4p\n", "3 4p\n", "2+3p\n", "3-p\n", "$-2,$p\n", "4ka\n'a,'a+1p\n", "7kb\n1\n'bp\n", "/o/,/e/p\n", "/nomatch/p\n,p\n", "5,3p\n", "0p\n", "11p\n", "=\n", "3=\n", "/delta/=\n", ".=\n", "2\n;=\n", "$;-3p\n", " 2 , 4 p\n", "2,4 p\n"])
# commands on buffer
many("append_insert_change", ["2a\nnew line\n.\n,p\n", "0a\nfirst\n.\n,p\n", "$a\nlast\n.\n.=\n,n\n", "3i\nins\n.\n,p\n.=\n", "0i\ntop\n.\n,p\n", "2,4c\nrepl\n.\n,p\n.=\n", "5c\n.\n,p\n.=\n", "a\n..\n.\n,p\n", "2a\n\n.\n,l\n", "3a\n.\n=\n", "1i\n.\n=\n", "2,3c\nx\ny\nz\n.\n,n\n"])
many("delete_join_move_copy", ["2,4d\n,p\n.=\n", "$d\n.=\n,p\n", "1,$d\n=\n", "3d\n.p\n", "2,4j\n,p\n.=\n", "3j\n,p\n", "5,5j\n,p\n", "1,3m$\n,p\n.=\n", "4,5m0\n,p\n.=\n", "2m2\n,p\n", "8,9m1\n,p\n", "1,3t$\n,p\n.=\n", "2t0\n,p\n", "4,6t4\n,p\n.=\n", "3,5m4\n,p\n", "1,2y\n$x\n,p\n.=\n", "x\n", "3y\n0x\n,p\n", "2,3y\n5d\nx\n,n\n"])
many("substitute", ["s/one/ONE/\np\n", ",s/e/E/\n,p\n", ",s/e/E/g\n,p\n", ",s/e/E/2\n,p\n", "1,3s/a/[&]/g\n,p\n", "s/x/y/\n,p\n", ",s/\\(.*\\) \\(.*\\)/\\2 \\1/\n,p\n", "2s/two/a\\\nb/\n,n\n.=\n", ",s/a/A/gp\n", "1s/alpha/AL/p\n3s/gamma/%/\n,p\n", "1s/a/b/\n2s//c/\n,p\n", "1s/a/b/\n2s\n,p\n", "1s/a/b/g\n3,5s\n,p\n", "1s/a/b/\n4s//&&/g\n,p\n", ",s/[aeiou]*/_/g\n,p\n", ",s/o*/0/g\n1,3p\n", ",s/$/;/\n,p\n", ",s/^/> /\n1,2p\n", "s|/|x|\n,p\n", "1s/l\\(p\\)h/\\1\\1/\n1p\n", ",s/e/E/3g\n,p\n", "2s/two/2/n\n", "3s/three/3/l\n", "s/ten/TEN/\n.=\n", ",s/\\n/X/\n,p\n", "1,2s/a\\|al/_/g\n1,2p\n", ",s/t\\{1,2\\}/T/\n,p\n", "1s/a/\\&/g\n1p\n", "1s/a/\\//\n1p\n"])
many("global_commands", ["g/e/p\n", "g/a/s/a/A/\\\ns/A/@/\n,p\n", "g/o/d\n,p\n.=\n", "v/e/d\n,p\n", "g/a/m0\n,p\n", "g/./t$\n,n\n", "g/e/s/e/E/gp\n", "g/t/.,+1j\n,p\n", "g/^/a\\\n--\n,p\n", "g/x/p\n.=\n", "g/e/\n.=\n", "2,5g/a/p\n", "g/a/-1p\n", "g/e/n\n", "g/one/s//1/\\\n+s/two/2/\n,p\n", "g/a/u\n,p\n", "g!e!p\n", "gIE\n", "g/A/Ip\n", "v/a/s/$/!/\n,p\n", "g/e/kx\n'xp\n"])
many("interactive_global", ["G/a/\np\ns/a/A/\n&\n\n,p\n", "V/e/\nd\n\n,p\n", "G/o/\n\np\n.=\n", "G/t/\ns/t/T/p\n&\n&\n"])
many("undo", ["2d\nu\n,p\n", "2d\nu\nu\n,p\n", ",s/a/A/g\nu\n,p\n.=\n", "1,2m$\nu\n,p\n", "g/e/d\nu\n,p\n", "u\n,p\n", "3a\nx\n.\nu\n.=\n", "1d\n2d\nu\n,p\n", "2,3j\nu\n,n\n", "4c\nzz\n.\nu\nu\n,p\n"])
many("print_list_number", [",l\n", "1,3n\n", "3\nzp\n" if False else "3z\n", "3z2\n", "z\n", "1z3\n.=\n", "zn\n", "$z\n", "1pn\n", "2ln\n", "1,2#comment\n.=\n", "3\n\n\n=\n", "$\n\n", ",l\n", "5\n+\n+\n", "\n\n\n.=\n"], files={"f.txt": TXT + "\x01tab\there\\back\x7f\n" + "x" * 150 + "\n"})
many("print_list_number", [",l\n", "8l\n"], files={"f.txt": "line with $ dollar\n" + "y" * 69 + "\n" + "z" * 68 + "\\\n" + "w" * 67 + "\t\n"})
many("regex", [",g/^[[:upper:]]/p\n", ",s/[[:digit:]]\\+/#/g\n,p\n", "g/\\<t/p\n", "g/o\\>/p\n", "g/\\bo/p\n", "g/\\w\\W\\w/p\n", ",s/\\(ab\\|a\\)\\(bc\\|c\\)/[\\1|\\2]/\n,p\n", ",s/x*/-/g\n,p\n", "g/\\(o\\).*\\1/p\n", ",s/[^a-z]/_/g\n,p\n", "g/^$/n\n", "g/  *$/l\n", ",s/\\`f/F/\n,p\n", "g/a\\{2,\\}/p\n", ",s/o\\?b/B/g\n,p\n", "g/\\t/p\n", ",s/.\\{3\\}$/!/\n,p\n"], files={"f.txt": TAB + "abc\nABC 12 34\nabab\naaa\n"})
many("regex_extended", [",s/(ab|a)(bc|c)/[\\1|\\2]/\n,p\n", ",s/o+/0/g\n,p\n", "g/a{2,}/p\n", ",s/(o)(o)?/<\\2\\1>/g\n,p\n", "g/^(foo|bar)+$/p\n", ",s/a|b/X/g\n,p\n"], args=("-s", "-E", "f.txt"), files={"f.txt": TAB + "abc\nabab\naaa\n"})
many("files_and_write", ["w out.txt\n", "w\nq\n", "1,3w part.txt\n", "2W part.txt\n4W part.txt\n", "wq copy.txt\n", "$r f.txt\n,n\n", "0r other.txt\n,p\n", "3r missing.txt\n,p\n", "e other.txt\n,p\n", "2d\ne other.txt\n,p\n", "2d\ne other.txt\ne other.txt\n,p\n", "2d\nq\n", "2d\nq\nq\n", "2d\nQ\n", "f\n", "f new.txt\nf\nw\n", "E other.txt\nf\n", "r\n,n\n", "1,2w\n,p\n", "2d\nwq\n", "e\n,p\n", "w other.txt\n", "2d\nw\nq\n"], files={"f.txt": TXT, "other.txt": "o1\no2\no3\n"})
many("files_and_write", ["w out.txt\n", "1,3w part.txt\n", "$r f.txt\n", "e other.txt\n", "r other.txt\nw\n", "f\n", "2d\nq\n"], args=("f.txt",), files={"f.txt": TXT, "other.txt": "o1\no2\no3\n"})
many("errors_and_exit", ["20p\n,p\n", "k\n,p\n", "2d\nq\n,p\n", "s/zzz/y/\n,p\n", ",s/zzz/y/\n,p\n", "g/zzz/d\n,p\n", "/nomatch/\n,p\n", "u\nu\n,p\n", "5,3d\n,p\n", "0d\n,p\n", "bogus\n,p\n", "1,2x\n,p\n", "3kA\n'Ap\n", "e missing.txt\n,p\n", "r missing.txt\n,p\n", "2m1,3\n,p\n", "p x\n", "1,2j3\n,p\n", "=5\n", "s/a/b/q\n,p\n", "1s/a/b/2g3\n", ",p\n2c\nnew\n"], stdin="pipe")
many("errors_and_exit", ["20p\n,p\n", "s/zzz/y/\n,p\n", "2d\nq\n,p\n", "bogus\n,p\n", "u\nu\n,p\n", "e missing.txt\n,p\n", ",p\n"], stdin="file")
many("errors_and_exit", ["s/zzz/y/\n,p\n", "20p\n,p\n"], args=("-s", "-l", "f.txt"), stdin="file")
many("errors_and_exit", ["20p\nh\n,p\n", "H\n20p\n,p\n", "20p\nH\n,p\n"], args=("-s", "f.txt"))
many("errors_and_exit", ["20p\n,p\n", "s/q/x/\n,p\n"], args=("-s", "-v", "f.txt"))
many("options", [",p\nq\n"], args=("-p", "*", "-s", "f.txt"))
many("options", ["P\n,p\nP\n2p\n", "1p\nP\n2p\n"], args=("-s", "f.txt"))
many("options", ["2p\nP\n3p\n"], args=("-p", ">", "f.txt"))
many("options", [",p\n", "w\n", "e other.txt\n,p\n", "w sub/x.txt\n", "w ../x.txt\n,p\n", "r /etc/hostname\n,p\n"], args=("-s", "-r", "f.txt"), files={"f.txt": TXT, "other.txt": "o1\n"})
many("options", ["1,3m$\n,p\n", "2t0\n,p\n", ",l\n", "f\n", "G/a/\np\n\n"], args=("-s", "-G", "f.txt"), files={"f.txt": TXT + "x" * 80 + "\n"})
many("options", [",p\n", "a\nx\n.\nw\n", "f\n", "w new.txt\n"], args=("-s",), files={})
many("options", [",p\n", "a\nx\n.\nw\n", "q\n"], args=("missing.txt",), files={})
many("options", [",p\n", "w\n"], args=("-q", "f.txt"))
many("odd_files", [",l\n", "$a\nadded\n.\nw\n", ",n\n", "w copy.txt\n"], args=("f.txt",), files={"f.txt": "no newline at end"})
many("odd_files", [",l\n", "w\n", "1d\nw\n"], args=("f.txt",), files={"f.txt": ""})
many("odd_files", [",n\n", "g/^$/d\nw\n"], args=("-s", "f.txt"), files={"f.txt": "\n\n\na\n\n"})
# random scripts
rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
def addr():
    r = rng.random()
    if r < 0.25: return ""
    b = rng.choice([".", "$", str(rng.randint(0, 12)), "/e/", "?a?", "/t/", "'a", "+", "-", "/o\\|a/", "/nomatch/", "//"])
    if rng.random() < 0.3: b += rng.choice(["+1", "-1", "+", "-", "++", "+2", "-2"])
    return b
def rng_addr():
    r = rng.random()
    if r < 0.4: return addr()
    return addr() + rng.choice([",", ";"]) + addr()
def cmd():
    k = rng.randrange(20)
    A = rng_addr()
    if k == 0: return A + rng.choice(["p", "n", "l", "pn"])
    if k == 1: return A + "d"
    if k == 2: return A + rng.choice(["a", "i", "c"]) + "\n" + "\n".join(rng.choice(["new", "x y", "", "alpha", "e.e"]) for _ in range(rng.randint(0, 2))) + "\n."
    if k == 3: return A + "s/" + rng.choice(["e", "a", "o*", "^", "$", "\\(.\\)\\(.\\)", "[a-e]\\+", "t\\|th", "", "n\\>"]) + "/" + rng.choice(["E", "&&", "\\2\\1", "", "%", "<&>", "\\\n"]) + "/" + rng.choice(["", "g", "2", "gp", "p", "3g", "n"])
    if k == 4: return A + rng.choice(["m", "t"]) + addr()
    if k == 5: return A + "j"
    if k == 6: return A + "k" + rng.choice("ab")
    if k == 7: return "u"
    if k == 8: return A + rng.choice(["g", "v"]) + "/" + rng.choice(["e", "a", "t", "o", "^.....$"]) + "/" + rng.choice(["p", "d", "s/e/E/", "m0", "t.", "-1p", "j", "n", ".=", "s//X/g"])
    if k == 9: return A + "="
    if k == 10: return A + rng.choice(["y", "x"])
    if k == 11: return A + "z" + rng.choice(["", "2", "5"])
    if k == 12: return rng.choice(["s", "s//&/g", "&" if False else "s/e/%/"])
    if k == 13: return A + "w " + rng.choice(["out.txt", "f.txt", ""])
    if k == 14: return rng.choice(["", A])
    if k == 15: return A + "r " + rng.choice(["other.txt", "missing.txt"])
    return A + rng.choice(["p", "n", "d", "l"])
for i in range(int(sys.argv[2]) if len(sys.argv) > 2 else 200):
    lines = [cmd() for _ in range(rng.randint(3, 9))] + [",n"]
    args = rng.choice([["-s", "f.txt"], ["-s", "f.txt"], ["f.txt"], ["-s", "-E", "f.txt"], ["-s", "-l", "f.txt"]])
    c(f"mixed_{i % 4 + 1}", "\n".join(lines) + "\n", args=args, files={"f.txt": TXT, "other.txt": "o1\no2\n"}, stdin=rng.choice(["pipe", "pipe", "file"]))
out = sys.argv[3] if len(sys.argv) > 3 else "cases_raw.json"
json.dump(C, open(out, "w")); print(len(C))
