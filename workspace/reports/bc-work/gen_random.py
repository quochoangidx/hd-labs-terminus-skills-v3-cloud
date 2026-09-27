import json, random, sys
rng = random.Random(int(sys.argv[1])); N = int(sys.argv[2])
def num():
    r = rng.random()
    if r < 0.3: return str(rng.randint(0, 99))
    if r < 0.6: return f"{rng.randint(0, 999)}.{rng.randint(0, 9999):0{rng.randint(1, 4)}d}"
    if r < 0.7: return "." + str(rng.randint(1, 999))
    if r < 0.8: return str(rng.randint(100, 10**12))
    return rng.choice(["0", "1", "2", "10", "0.5", "3.14159", "1.000"])
def expr(d=0):
    if d > 3 or rng.random() < 0.3:
        return rng.choice([num(), num(), "x", "y", "a[1]", "a[2]", "last"])
    k = rng.random()
    a, b = expr(d + 1), expr(d + 1)
    if k < 0.5: return f"{a} {rng.choice(['+', '-', '*', '/', '%'])} {b}"
    if k < 0.6: return f"({a})^{rng.randint(-3, 4)}"
    if k < 0.7: return f"-{a}"
    if k < 0.75: return f"sqrt({a}*{a})"
    if k < 0.8: return f"({a} {rng.choice(['<', '>', '==', '!=', '<=', '>='])} {b})"
    if k < 0.85: return f"scale({a})"
    if k < 0.9: return f"length({a})"
    if k < 0.95: return f"({a})"
    return f"f({a})"
def safe_div(e):
    return e
progs = []
while len(progs) < N:
    lines = []
    lines.append("define f(v) { auto w; w = v * 2 + y; return (w / 3) }")
    lines.append(f"scale={rng.choice([0, 0, 1, 2, 3, 5, 10, 20])}")
    lines.append(f"x={num()}; y={num()}; a[1]={num()}; a[2]={num()}")
    for _ in range(rng.randint(1, 6)):
        r = rng.random()
        if r < 0.6: lines.append(expr())
        elif r < 0.7: lines.append(f"x = {expr()}")
        elif r < 0.8: lines.append(f"scale={rng.choice([0, 2, 4, 8])}; {expr()}")
        elif r < 0.85: lines.append(f"sv=scale; scale=0; obase={rng.choice([2, 8, 16, 17, 100])}; ({expr()})/1; obase=10; scale=sv")
        elif r < 0.9: lines.append(f"print {expr()}, \" \", {expr()}, \"\\n\"")
        else: lines.append(f"for (i=0; i<3; i++) {{ x = x * {num()} + i; x }}")
    progs.append({"input": "\n".join(lines) + "\n"})
json.dump(progs, sys.stdout)
