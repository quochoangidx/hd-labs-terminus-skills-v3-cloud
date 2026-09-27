"""Check kernel/fir16.s: correctness and cycles against 8N + 64.

Usage: python3 tools/run_fir.py [path/to/fir16.s] [N ...]
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kestrel import Machine, assemble  # noqa: E402

X_BASE, H_BASE, Y_BASE = 0x1000, 0x0100, 0x4000


def pack(lo, hi):
    return ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)


def expected(x, h, n):
    out = []
    for i in range(n):
        v = sum(h[k] * x[i + k] for k in range(16)) >> 15
        out.append((v + (1 << 31)) % (1 << 32) - (1 << 31))
    return out


def run(source, n, x, h):
    memory = {X_BASE + i // 2: pack(x[i], x[i + 1]) for i in range(0, n + 16, 2)}
    memory.update({H_BASE + k // 2: pack(h[k], h[k + 1]) for k in range(0, 16, 2)})
    machine = Machine(assemble(source), memory)
    machine.r[0] = n
    machine.a[0], machine.a[1], machine.a[2] = X_BASE, H_BASE, Y_BASE
    cycles = machine.run()
    return [machine.mem[Y_BASE + i] for i in range(n)], cycles


def main():
    args = sys.argv[1:]
    path = args.pop(0) if args and not args[0].isdigit() else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "kernel", "fir16.s")
    sizes = [int(a) for a in args] or [16, 64, 256]
    source = open(path).read()
    rng = random.Random(1)
    for n in sizes:
        x = [rng.randint(-32768, 32767) for _ in range(n + 16)]
        h = [rng.randint(-32768, 32767) for _ in range(16)]
        out, cycles = run(source, n, x, h)
        ok = out == expected(x, h, n)
        budget = 8 * n + 64
        print(f"N={n:5d}  correct={ok}  cycles={cycles:7d}  budget={budget:7d}  "
              f"{'within' if cycles <= budget else 'OVER'}")


if __name__ == "__main__":
    main()
