import json, random, sys
N = int(sys.argv[1]); seed = int(sys.argv[2])
rng = random.Random(seed)
C = []
NAMES = ["foo", "bar", "baz", "qux", "x", "y1", "_z"]
VALS = ["W", "x y", "$1!", "(", ",", "`q'", "a,b", "[$@]", "$#", "hello", "", "#", "1+2", "`,'", "dnl", "`(x)'"]
QUOTES = [("`", "'"), ("[", "]"), ("<<", ">>"), ("{", "}")]
def prog():
    lq, rq = "`", "'"
    lines = []
    def q(s, n=1): return lq * n + s + rq * n
    def a(d):
        s = atom(d); r = rng.random()
        if r < 0.45: return q(s)
        if r < 0.55: return q(s, 2)
        if r < 0.62: return rng.choice([" ", "\n ", "\t"]) + s
        return s
    def atom(d):
        if d <= 0 or rng.random() < 0.22:
            return rng.choice(NAMES + ["hello world", "a,b", "(x)", "", "12", "-3", "abc123", "Foo Bar", "x#y", "0x1f", "  sp"])
        k = rng.randrange(22)
        A = lambda: a(d - 1)
        if k == 0: return f"len({A()})"
        if k == 1: return f"index({A()},{q(rng.choice(['o', 'a', '', '1', 'b,']))})"
        if k == 2: return f"substr({A()},{rng.randint(-1, 5)}{',' + str(rng.randint(-2, 6)) if rng.random() < .6 else ''})"
        if k == 3: return f"translit({A()},{q(rng.choice(['a-z', 'o', 'abc', 'z-a', 'a-c-a', '0-9']))}{',' + q(rng.choice(['A-Z', '', 'xy', '9-0', '_'])) if rng.random() < .8 else ''})"
        if k == 4:
            ops = ['+', '*', '-', '/', '%', '**', '<', '==', '!=', '&', '|', '^', '<<', '>>', '&&', '||', '>=']
            e = f"{rng.choice(['', '-', '~', '!'])}{rng.randint(-9, 99)}{rng.choice(ops)}({rng.randint(-5, 9)}{rng.choice(ops)}{rng.randint(1, 5)})"
            return f"eval({q(e) if rng.random()<.5 else e}{',' + str(rng.choice([2, 8, 16, 36, 10])) if rng.random() < .3 else ''}{',' + str(rng.randint(0, 6)) if rng.random() < .15 else ''})"
        if k == 5: return f"ifelse({A()},{A()},{A()}{',' + A() if rng.random()<.7 else ''}{',' + A() + ',' + A() if rng.random()<.2 else ''})"
        if k == 6: return f"patsubst({A()},{q(rng.choice(['o', '[a-z]+', '\\\\w', '^', '\\\\(.\\\\)\\\\(.\\\\)', 'o*', '\\\\<', '[^a-z]', 'b\\\\|o']))}{',' + q(rng.choice(['<\\\\&>', '', '\\\\2\\\\1', '_', '\\\\\\\\'])) if rng.random()<.85 else ''})"
        if k == 7: return f"regexp({A()},{q(rng.choice(['o+', '[0-9]', '\\\\b', '\\\\(.\\\\)$', 'x*', '\\\\w+ \\\\w+']))}{',' + q(rng.choice(['[\\\\&]', '\\\\1\\\\1', '\\\\0', ''])) if rng.random()<.6 else ''})"
        if k == 8: return f"format({q(rng.choice(['%s-%s', '%5s|', '%d', '%x', '%-3s.', '%c%c', '%.2s', '%3d|%-3d', '%o %X', '%%%s']))},{A()},{A()})"
        if k in (9, 10, 11): return f"m{rng.randint(1, 5)}({A()}{',' + A() if rng.random()<.7 else ''}{',' + A() if rng.random()<.3 else ''})"
        if k == 12: return f"shift({A()},{A()},{A()})"
        if k == 13: return f"{rng.choice(['incr', 'decr'])}({rng.randint(-5, 50)})"
        if k == 14: return f"defn({q(rng.choice(NAMES + ['m1', 'm2', 'len', 'nosuch']))})"
        if k == 15: return f"ifdef({q(rng.choice(NAMES + ['m1', 'nosuch']))},{A()},{A()})"
        if k == 16: return f"indir({q(rng.choice(['m1', 'm2', 'len', 'foo']))},{A()})"
        if k == 17: return f"builtin({q(rng.choice(['len', 'eval', 'substr', 'index']))},{A()}{',' + A() if rng.random()<.5 else ''})"
        if k == 18: return rng.choice(NAMES) + rng.choice(["", "()", "(1)", " (1)"])
        if k == 19: return f"cnt({rng.randint(0, 6)})"
        if k == 20: return q(atom(d - 1))
        return rng.choice(["__line__", "divnum", "`'", "$1", "#c\n"])
    BODIES = ["[$1|$2]", "$2$1", "`$1'-`$2'", "$#:$*", "$@", "ifelse(`$1',,empty,`<$1>')", "len(`$1$2')", "translit(`$1',`a-z',`A-Z')", "$1`'$1", "``$1''",
              "define(`last',`$1')", "substr(`$1',1)", "eval($#*10)", "`$@'", "$*", "($3)", "m1($2,$1)", "ifelse($#,0,none,$#,1,`one:$1',`many:$*')", "incr(len(`$*'))", "$1 $10 $11"]
    lines.append("define(`cnt',`ifelse(`$1',0,,`$1`'cnt(decr($1))')')dnl")
    for m in range(1, 6):
        body = rng.choice(BODIES)
        if m == 1 and "m1(" in body: body = "[$1|$2]"
        lines.append(f"define(`m{m}',`{body}')dnl")
    for w in rng.sample(NAMES, rng.randint(1, 5)):
        lines.append(f"{rng.choice(['define', 'pushdef'])}(`{w}',`{rng.choice(VALS)}')dnl")
    for _ in range(rng.randint(4, 10)):
        r = rng.random()
        if r < 0.06:
            nl, nr = rng.choice(QUOTES)
            lines.append(f"changequote({lq}{nl}{rq},{lq}{nr}{rq})dnl" if nl != "`" else f"changequote`'dnl" if False else f"changequote({nl},{nr})dnl")
            lq, rq = nl, nr
        elif r < 0.1:
            lines.append(f"divert({rng.choice([1, 2, -1, 0, 3])})dnl")
        elif r < 0.13:
            lines.append(f"undivert({rng.choice(['', '1', '2', '3'])})")
        elif r < 0.16:
            lines.append(f"m4wrap({q(atom(2) + chr(10))})dnl")
        elif r < 0.19:
            lines.append(f"popdef({q(rng.choice(NAMES))})dnl")
        elif r < 0.22:
            lines.append(f"changecom({q(rng.choice(['#', '/*', '@', '']))}{',' + q(rng.choice(['*/', '', '@'])) if rng.random()<.5 else ''})dnl")
        elif r < 0.25:
            lines.append(f"undefine({q(rng.choice(NAMES + ['m2']))})dnl")
        else:
            lines.append(atom(4) + rng.choice(["", " ", " foo", " x", "|", " # c"]))
    return "\n".join(lines) + "\n"
for i in range(N):
    C.append({"group": f"random_{i % 8 + 1}", "src": prog(), "args": ["in.m4"], "files": {}, "stdin": ""})
json.dump(C, open(f"big_{seed}.json", "w")); print(len(C))
