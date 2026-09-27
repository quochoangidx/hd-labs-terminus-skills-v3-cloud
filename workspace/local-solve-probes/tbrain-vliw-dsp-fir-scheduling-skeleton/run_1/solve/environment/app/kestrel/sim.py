"""Cycle-accurate simulator for KESTREL-16. See docs/kestrel-isa.md."""

from kestrel.asm import NACC, NADDR, NREG

MASK32 = 0xFFFFFFFF
MEMSIZE = 65536
LAT_ALU = 1
LAT_LD = 3
LAT_ACC_MAC = 1
LAT_ACC_STA = 3
LAT_ADDR = 1


class SimError(Exception):
    pass


def s32(x):
    x &= MASK32
    return x - (1 << 32) if x & 0x80000000 else x


def lo16(x):
    v = x & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def hi16(x):
    v = (x >> 16) & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


class Machine:
    def __init__(self, program, memory=None, max_cycles=5_000_000):
        self.program = program
        self.mem = [0] * MEMSIZE
        if memory:
            for addr, value in memory.items():
                self.mem[addr] = s32(value)
        self.r = [0] * NREG
        self.acc = [0] * NACC
        self.a = [0] * NADDR
        self.ready_r = [0] * NREG
        self.ready_acc_mac = [0] * NACC
        self.ready_acc_sta = [0] * NACC
        self.ready_a = [0] * NADDR
        self.max_cycles = max_cycles
        self.cycles = 0

    def _sources(self, name, ops):
        """(kind, index, reader) for every operand the operation reads."""
        regs = []
        if name in ("mov", "shl", "sar", "shr", "addi"):
            regs = [("r", ops[1])]
        elif name in ("add", "sub", "and", "or", "xor", "pkhl"):
            regs = [("r", ops[1]), ("r", ops[2])]
        elif name == "amov":
            regs = [("r", ops[1])]
        elif name == "aadd":
            regs = [("a", ops[0])]
        elif name in ("dmac", "mac"):
            regs = [("r", ops[1]), ("r", ops[2]), ("accm", ops[0])]
        elif name in ("dmacz", "macz"):
            regs = [("r", ops[1]), ("r", ops[2])]
        elif name == "ld":
            regs = [("a", ops[1][0])]
        elif name == "st":
            regs = [("r", ops[0]), ("a", ops[1][0])]
        elif name == "sta":
            regs = [("accs", ops[0]), ("a", ops[2][0])]
        elif name == "loop" and ops[0][0] == "r":
            regs = [("r", ops[0][1])]
        return regs

    def _ready(self, kind, index):
        return {"r": self.ready_r, "a": self.ready_a, "accm": self.ready_acc_mac,
                "accs": self.ready_acc_sta}[kind][index]

    def run(self):
        pc = 0
        issue = -1
        loop_start = loop_end = None
        loop_left = 0
        n = len(self.program)
        while True:
            if pc >= n:
                raise SimError("ran off the end of the program without halt")
            bundle = self.program[pc]
            earliest = issue + 1
            for name, _unit, ops, _line in bundle:
                for kind, index in self._sources(name, ops):
                    earliest = max(earliest, self._ready(kind, index))
            issue = earliest
            if issue >= self.max_cycles:
                raise SimError("cycle limit exceeded")
            writes = []
            halted = False
            new_loop = None
            for name, _unit, ops, line in bundle:
                r, a, acc = self.r, self.a, self.acc
                if name == "li":
                    writes.append(("r", ops[0], s32(ops[1]), LAT_ALU))
                elif name == "mov":
                    writes.append(("r", ops[0], r[ops[1]], LAT_ALU))
                elif name == "add":
                    writes.append(("r", ops[0], s32(r[ops[1]] + r[ops[2]]), LAT_ALU))
                elif name == "sub":
                    writes.append(("r", ops[0], s32(r[ops[1]] - r[ops[2]]), LAT_ALU))
                elif name == "addi":
                    writes.append(("r", ops[0], s32(r[ops[1]] + ops[2]), LAT_ALU))
                elif name == "and":
                    writes.append(("r", ops[0], s32(r[ops[1]] & r[ops[2]]), LAT_ALU))
                elif name == "or":
                    writes.append(("r", ops[0], s32(r[ops[1]] | r[ops[2]]), LAT_ALU))
                elif name == "xor":
                    writes.append(("r", ops[0], s32(r[ops[1]] ^ r[ops[2]]), LAT_ALU))
                elif name == "shl":
                    writes.append(("r", ops[0], s32(r[ops[1]] << (ops[2] & 31)), LAT_ALU))
                elif name == "sar":
                    writes.append(("r", ops[0], s32(r[ops[1]] >> (ops[2] & 31)), LAT_ALU))
                elif name == "shr":
                    writes.append(("r", ops[0], s32((r[ops[1]] & MASK32) >> (ops[2] & 31)), LAT_ALU))
                elif name == "pkhl":
                    value = ((r[ops[2]] & 0xFFFF) << 16) | ((r[ops[1]] >> 16) & 0xFFFF)
                    writes.append(("r", ops[0], s32(value), LAT_ALU))
                elif name == "ali":
                    writes.append(("a", ops[0], ops[1] % MEMSIZE, LAT_ALU))
                elif name == "aadd":
                    writes.append(("a", ops[0], (a[ops[0]] + ops[1]) % MEMSIZE, LAT_ALU))
                elif name == "amov":
                    writes.append(("a", ops[0], r[ops[1]] % MEMSIZE, LAT_ALU))
                elif name in ("dmac", "dmacz", "mac", "macz"):
                    x, y = r[ops[1]], r[ops[2]]
                    prod = lo16(x) * lo16(y)
                    if name.startswith("dmac"):
                        prod += hi16(x) * hi16(y)
                    base = 0 if name.endswith("z") else acc[ops[0]]
                    writes.append(("acc", ops[0], base + prod, None))
                elif name == "ld":
                    ax, step = ops[1]
                    writes.append(("r", ops[0], self.mem[a[ax]], LAT_LD))
                    if step:
                        writes.append(("a", ax, (a[ax] + step) % MEMSIZE, LAT_ADDR))
                elif name == "st":
                    ax, step = ops[1]
                    writes.append(("mem", a[ax], r[ops[0]], 0))
                    if step:
                        writes.append(("a", ax, (a[ax] + step) % MEMSIZE, LAT_ADDR))
                elif name == "sta":
                    ax, step = ops[2]
                    writes.append(("mem", a[ax], s32(acc[ops[0]] >> ops[1]), 0))
                    if step:
                        writes.append(("a", ax, (a[ax] + step) % MEMSIZE, LAT_ADDR))
                elif name == "loop":
                    count = ops[0][1] if ops[0][0] == "i" else r[ops[0][1]]
                    if count < 1:
                        raise SimError(f"line {line}: loop count must be at least 1")
                    if loop_left:
                        raise SimError(f"line {line}: loop started inside a loop")
                    if ops[1] <= pc:
                        raise SimError(f"line {line}: loop end must follow the loop instruction")
                    new_loop = (pc + 1, ops[1], count)
                elif name == "halt":
                    halted = True
            targets = set()
            for kind, index, value, lat in writes:
                key = (kind, index)
                if kind != "mem" and key in targets:
                    raise SimError(f"bundle at line {bundle[0][3]}: two writes to one register")
                targets.add(key)
                if kind == "r":
                    self.r[index] = value
                    self.ready_r[index] = issue + lat
                elif kind == "a":
                    self.a[index] = value
                    self.ready_a[index] = issue + lat
                elif kind == "acc":
                    self.acc[index] = value
                    self.ready_acc_mac[index] = issue + LAT_ACC_MAC
                    self.ready_acc_sta[index] = issue + LAT_ACC_STA
                elif kind == "mem":
                    self.mem[index] = value
            if halted:
                self.cycles = issue + 1
                return self.cycles
            if new_loop:
                loop_start, loop_end, loop_left = new_loop
            if loop_left and pc == loop_end:
                loop_left -= 1
                pc = loop_start if loop_left else pc + 1
            else:
                pc += 1
