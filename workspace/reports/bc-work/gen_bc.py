"""Generate bc test programs: one family per area of the manual plus mixed random programs.

Every program is syntactically valid GNU bc, ends with a newline, and stays inside the
ranges the manual states (ibase 2..16, obase 2..999, array indexes 0..65535).
"""
import json
import random
import sys

R = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
VARS = ["a", "b", "c", "x", "y", "n1", "tot"]
ARRS = ["p", "q"]


def num(big=False):
    r = R.random()
    if big or r < 0.05:
        s = str(R.randrange(1, 10)) + "".join(R.choice("0123456789") for _ in range(R.randrange(15, 70)))
        if R.random() < 0.5:
            s += "." + "".join(R.choice("0123456789") for _ in range(R.randrange(1, 30)))
        return s
    if r < 0.35:
        return str(R.randrange(0, 20))
    if r < 0.55:
        return str(R.randrange(0, 1000))
    if r < 0.85:
        ip = str(R.randrange(0, 100)) if R.random() < 0.7 else ""
        return ip + "." + "".join(R.choice("0123456789") for _ in range(R.randrange(1, 7)))
    if r < 0.9:
        return R.choice(["007", "0.50", "000", "12.", ".0", "0.000", "100.00"])
    return R.choice(["A", "F", "1A", "3F.2", "ZZ", "B0", ".A"])


def atom(depth, env):
    r = R.random()
    if r < 0.35:
        return num()
    if r < 0.6:
        return R.choice(env["vars"])
    if r < 0.66:
        return "%s[%d]" % (R.choice(ARRS), R.randrange(0, 6))
    if r < 0.72:
        return R.choice(["scale", "last", "."]) if R.random() < 0.5 else "scale(%s)" % expr(depth - 1, env)
    if r < 0.78:
        return "length(%s)" % expr(depth - 1, env)
    if r < 0.84:
        return "sqrt(%s)" % expr(depth - 1, env)
    if r < 0.9 and env["funcs"]:
        f, k = R.choice(env["funcs"])
        if f in ("fib", "fact"):
            return "%s(%d)" % (f, R.randrange(0, 12))
        return "%s(%s)" % (f, ", ".join(expr(depth - 1, env) for _ in range(k)))
    if r < 0.95:
        v = R.choice(env["vars"])
        return R.choice(["%s++", "%s--", "++%s", "--%s"]) % v
    return "(%s)" % expr(depth - 1, env)


def expr(depth, env):
    if depth <= 0:
        return atom(0, env)
    r = R.random()
    if r < 0.3:
        return atom(depth, env)
    if r < 0.62:
        op = R.choice(["+", "-", "*", "*", "/", "/", "%"])
        return "%s %s %s" % (expr(depth - 1, env), op, expr(depth - 1, env))
    if r < 0.7:
        e = R.choice(["-3", "-2", "-1", "0", "2", "3", "5", "7", "1.5", "10"])
        return "(%s)^%s" % (expr(depth - 1, env), e) if R.random() < 0.7 else "%s^%s" % (atom(0, env), e)
    if r < 0.8:
        op = R.choice(["<", "<=", ">", ">=", "==", "!="])
        return "%s %s %s" % (expr(depth - 1, env), op, expr(depth - 1, env))
    if r < 0.87:
        op = R.choice(["&&", "||"])
        return "%s %s %s" % (expr(depth - 1, env), op, expr(depth - 1, env))
    if r < 0.92:
        return "!%s" % atom(depth - 1, env)
    if r < 0.97:
        return "-(%s)" % atom(depth - 1, env) if R.random() < 0.4 else "- %s" % atom(depth - 1, env)
    v = R.choice(env["vars"])
    return "(%s %s %s)" % (v, R.choice(["=", "+=", "-=", "*=", "/="]), expr(depth - 1, env))


def string():
    parts = []
    for _ in range(R.randrange(1, 4)):
        parts.append(R.choice(["x=", "val ", "--", " ", "result: ", "ab", "\\n", "\\t", "\\q", "\\\\", "[", "]"]))
    return "".join(parts)


def statement(env, depth=2):
    r = R.random()
    if r < 0.28:
        return expr(depth, env)
    if r < 0.48:
        v = R.choice(env["vars"] + ["%s[%d]" % (R.choice(ARRS), R.randrange(0, 6))])
        op = R.choice(["=", "=", "+=", "-=", "*=", "/=", "%=", "^="])
        rhs = R.choice(["2", "3", "-1", "0"]) if op == "^=" else expr(depth, env)
        return "%s %s %s" % (v, op, rhs)
    if r < 0.58:
        items = []
        for _ in range(R.randrange(1, 4)):
            items.append('"%s"' % string() if R.random() < 0.5 else expr(depth - 1, env))
        return "print " + ", ".join(items)
    if r < 0.63:
        return '"%s"' % R.choice(["plain ", "a\\nb", "line\n", "="])
    if r < 0.72:
        return "scale = %d" % R.choice([0, 0, 1, 2, 3, 5, 8, 10, 20])
    if r < 0.78:
        return "obase = %s" % R.choice(["2", "8", "A", "16", "3", "7", "12", "20", "36", "100", "999", "A", "A"])
    if r < 0.82:
        return "ibase = %s" % R.choice(["2", "8", "A", "16", "A", "A", "3"])
    if r < 0.88:
        return "if (%s) %s else %s" % (expr(1, env), simple(env), simple(env))
    if r < 0.93:
        k = R.randrange(1, 5)
        return "for (i = 0; i < %d; i++) { %s; %s }" % (k, simple(env), simple(env))
    if r < 0.96:
        return "j = %d; while (j > 0) { %s; j = j - 1 }" % (R.randrange(0, 4), simple(env))
    return "{ %s; %s }" % (simple(env), simple(env))


def simple(env):
    r = R.random()
    if r < 0.4:
        return "%s = %s" % (R.choice(env["vars"]), expr(1, env))
    if r < 0.7:
        return "print %s, \"\\n\"" % expr(1, env)
    if r < 0.8:
        return expr(1, env)
    if r < 0.9:
        return "%s[%d] += %s" % (R.choice(ARRS), R.randrange(0, 6), expr(1, env))
    return "print \"%s\"" % string()


FUNCS = [
    ("sq", 1, "define sq(v) {\n  return (v * v)\n}"),
    ("fact", 1, "define fact(k) {\n  auto r\n  r = 1\n  while (k > 1) { r *= k; k -= 1 }\n  return (r)\n}"),
    ("mx", 2, "define mx(u, v) { if (u > v) return (u); return (v); }"),
    ("fib", 1, "define fib(k) {\n  if (k < 2) return (k)\n  return (fib(k - 1) + fib(k - 2))\n}"),
    ("peek", 1, "define peek(k) {\n  auto a\n  a = k * 2\n  return (a + b)\n}"),
    ("half", 1, "define half(v) { auto s; s = scale; scale = 3; v = v / 2; scale = s; return v }"),
    ("hx", 0, "define hx() { return (10 + FF) }"),
]


def program(env, nlines):
    lines = []
    for f in env["fdefs"]:
        lines.append(f)
    for _ in range(nlines):
        k = R.randrange(1, 4)
        lines.append("; ".join(statement(env) for _ in range(k)))
    if R.random() < 0.1:
        lines.append(R.choice(["halt", "quit", "if (0) quit", "if (0 == 1) halt"]))
        lines.append("\"after\"")
    return "\n".join(lines) + "\n"


def new_env(with_funcs):
    env = {"vars": R.sample(VARS, 4), "funcs": [], "fdefs": []}
    if with_funcs:
        for name, k, src in R.sample(FUNCS, R.randrange(1, 4)):
            env["funcs"].append((name, k))
            env["fdefs"].append(src)
    return env


# ---- targeted families

def fam_numbers():
    env = new_env(False)
    out = []
    for _ in range(R.randrange(3, 8)):
        base = R.choice(["2", "8", "A", "16", "A", "7", "C"])
        vals = [R.choice(["10", "FF", "1A", "Z", "7", "F.8", "1.1", ".8", "ABC", "0.01", "12.34", "Z.Z", "100", "0", "1", "Q"]) for _ in range(3)]
        out.append("ibase = %s; %s; ibase = A" % (base, "; ".join(vals)))
    out.append(expr(1, env))
    return "\n".join(out) + "\n"


def fam_arith():
    env = new_env(False)
    out = []
    for _ in range(R.randrange(4, 10)):
        out.append("scale = %d; %s %s %s" % (R.choice([0, 1, 2, 4, 7, 12]), num(), R.choice("+-*/%*/"), num()))
    for _ in range(3):
        out.append("scale = %d; (%s)^%s" % (R.choice([0, 2, 5]), R.choice(["-" + num(), num()]), R.choice(["2", "3", "-2", "0", "5", "-1", "1.9"])))
    return "\n".join(out) + "\n"


def fam_functions_builtin():
    out = []
    for _ in range(R.randrange(4, 9)):
        s = R.choice([0, 1, 3, 6, 10])
        out.append("scale = %d; sqrt(%s); length(%s); scale(%s)" % (s, num(), R.choice([num(), "-" + num()]), num()))
    out.append("sqrt(-4)\n\"next\"")
    return "\n".join(out) + "\n"


def fam_printing():
    out = []
    for _ in range(R.randrange(3, 7)):
        ob = R.choice(["2", "3", "8", "16", "7", "17", "20", "25", "100", "999", "36"])
        vals = [R.choice([num(), "-" + num(), num(True), "0", "0.000", "-0.5", "1/3", "2^100"]) for _ in range(3)]
        out.append("scale = %d; obase = %s; %s; obase = A" % (R.choice([0, 2, 5, 10]), ob, "; ".join(vals)))
    out.append("scale = 0; 2^%d" % R.randrange(200, 700))
    out.append("x = 3^%d; x; -x" % R.randrange(100, 300))
    return "\n".join(out) + "\n"


def fam_strings():
    out = []
    for _ in range(R.randrange(3, 7)):
        out.append(R.choice([
            'print "%s", %s, "%s"' % (string(), num(), string()),
            '"%s"' % R.choice(["literal \\n stays", "two\nlines", "tab\there"]),
            'print "%s"' % ("abcdefghij" * R.randrange(3, 9)),
            'print "%s", 2^%d, "\\n"' % ("w" * R.randrange(1, 60), R.randrange(50, 300)),
            'for (i = 0; i < %d; i++) print i, " "' % R.randrange(5, 40),
            'print "\\n"',
        ]))
    return "\n".join(out) + "\n"


def fam_logic():
    env = new_env(False)
    out = []
    for _ in range(R.randrange(4, 9)):
        out.append(R.choice([
            "%s %s %s" % (num(), R.choice(["<", "<=", ">", ">=", "==", "!="]), num()),
            "%s && %s" % (expr(1, env), expr(1, env)),
            "%s || %s" % (expr(1, env), expr(1, env)),
            "!%s" % atom(0, env),
            "a = 3 < 5; a",
            "b = 1 + (2 < 3); b",
            "!0 + 1", "!1 < 2", "-2^2", "2^3^2", "1 < 2 < 3", "3 > 2 > 1",
            "(%s) %s (%s)" % (expr(1, env), R.choice(["&&", "||"]), expr(1, env)),
        ]))
    return "\n".join(out) + "\n"


def fam_assign():
    env = new_env(False)
    out = []
    for _ in range(R.randrange(4, 9)):
        v = R.choice(env["vars"])
        out.append(R.choice([
            "%s = %s; %s" % (v, num(), v),
            "%s %s %s; %s" % (v, R.choice(["+=", "-=", "*=", "/=", "%=", "^="]), R.choice(["2", "3", "0.5", "7"]), v),
            "%s++; %s; ++%s; %s--; --%s" % (v, v, v, v, v),
            "(%s = %s)" % (v, num()),
            "%s = %s = %s; %s" % (v, R.choice(env["vars"]), num(), v),
            "%s; last; .; last = 5; ." % num(),
            "p[%d] = %s; p[%d]++; p[%d]; q[1] += p[%d]; q[1]" % ((lambda k: (k, num(), k, k, k))(R.randrange(0, 9))),
            "scale = %d; scale; scale += 2; scale" % R.randrange(0, 6),
        ]))
    return "\n".join(out) + "\n"


def fam_control():
    env = new_env(False)
    out = []
    for _ in range(R.randrange(3, 6)):
        out.append(R.choice([
            "for (i = 1; i <= %d; i++) { if (i %% 3 == 0) continue; print i, \"\\n\" }" % R.randrange(3, 12),
            "for (i = 0; ; i++) { if (i > %d) break; i }" % R.randrange(0, 6),
            "i = %d; while (i) { i -= 1; if (i == 2) break; i }" % R.randrange(0, 6),
            "if (%s) \"yes\" else \"no\"" % expr(1, env),
            "if (%s) {\n  print \"t\\n\"\n} else {\n  print \"f\\n\"\n}" % expr(1, env),
            "for (i = 0; i < 3; i++)\n  i * 10",
            "{ a = 1\n  b = 2\n  a + b }",
            "x = 5; if (x > 3) if (x > 4) \"big\" else \"mid\"",
        ]))
    if R.random() < 0.4:
        out.append(R.choice(["if (1 == 0) quit", "halt", "quit"]))
        out.append("\"after\"")
    return "\n".join(out) + "\n"


def fam_functions():
    env = new_env(True)
    out = list(env["fdefs"])
    out.append("b = %s" % num())
    for _ in range(R.randrange(3, 7)):
        f, k = R.choice(env["funcs"])
        args = ", ".join(R.choice(["0", "1", "2", "5", "7", "10", "3.5", "-4"]) for _ in range(k))
        if f == "fib":
            args = str(R.randrange(0, 12))
        if f == "fact":
            args = str(R.randrange(0, 25))
        out.append("%s(%s)" % (f, args))
    out.append(R.choice([
        "define void show(v) { print \"<\", v, \">\\n\" }\nshow(3)\nshow(4) ; 5",
        "define set(z[]) { z[0] = 99; return (z[0]) }\nq[0] = 1\nset(q[])\nq[0]",
        "define setv(*z[]) { z[0] = 99; return (z[0]) }\nq[0] = 1\nsetv(q[])\nq[0]",
        "define g() { return }\ng()",
        "define g() { a = 7 }\ng(); a",
        "define r(k) { if (k == 0) return (0); return (k + r(k - 1)) }\nr(%d)" % R.randrange(0, 30),
        "ibase = 16\ndefine c16() { return (10) }\nibase = A\nc16()",
        "define d(v) { return (v * 2) }\nd(4)\ndefine d(v) { return (v * 3) }\nd(4)",
        "undefined(2)\n\"after\"",
    ]))
    return "\n".join(out) + "\n"


def fam_errors():
    env = new_env(False)
    out = []
    for _ in range(R.randrange(3, 6)):
        out.append(R.choice([
            "print \"a\"; 1/0; print \"b\"\n\"c\\n\"",
            "x = 5 % 0; x",
            "{ print \"in\\n\"\n  sqrt(-1)\n  print \"no\\n\" }\n\"yes\\n\"",
            "0^-1; \"after\"",
            "p[-1] = 3; \"x\"",
            "define e(v) { auto t; t = v; return (1 / (v - v)) }\nt = 4; e(2); t",
            "for (i = 0; i < 3; i++) { i; if (i == 1) 1 / 0 }\n\"done\\n\"",
            "%s" % statement(env),
        ]))
    return "\n".join(out) + "\n"


FAMS = {
    "numbers_and_bases": fam_numbers, "arithmetic_and_scale": fam_arith, "builtin_functions": fam_functions_builtin,
    "printing_and_radixes": fam_printing, "strings_and_print": fam_strings, "relational_and_boolean": fam_logic,
    "assignment_and_variables": fam_assign, "control_flow": fam_control, "user_functions": fam_functions,
    "runtime_errors": fam_errors,
}


def main():
    n = int(sys.argv[1])
    cases = []
    for fam, g in FAMS.items():
        for _ in range(n // 20):
            cases.append({"family": fam, "args": [], "stdin": g(), "files": {}})
    for i in range(n // 2):
        env = new_env(R.random() < 0.4)
        src = program(env, R.randrange(3, 12))
        case = {"family": "mixed_%d" % (i % 8 + 1), "args": [], "stdin": src, "files": {}}
        if R.random() < 0.15:
            lines = src.splitlines(True)
            safe = [j for j in range(1, len(lines) + 1) if "".join(lines[:j]).count('"') % 2 == 0]
            k = R.choice(safe)
            case["files"] = {"prog.bc": "".join(lines[:k])}
            case["args"] = ["prog.bc"]
            case["stdin"] = "".join(lines[k:])
        cases.append(case)
    json.dump(cases, sys.stdout)


main()
