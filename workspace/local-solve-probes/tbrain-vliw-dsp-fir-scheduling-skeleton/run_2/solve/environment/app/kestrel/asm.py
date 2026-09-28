"""Assembler for KESTREL-16. See docs/kestrel-isa.md."""

import re

ALU = {"li", "mov", "add", "sub", "addi", "and", "or", "xor", "shl", "sar", "shr", "pkhl",
       "ali", "aadd", "amov", "nop"}
MAC = {"dmac", "dmacz", "mac", "macz"}
MEM = {"ld", "st", "sta"}
CTL = {"loop", "halt"}
UNIT = {**{m: "alu" for m in ALU}, **{m: "mac" for m in MAC}, **{m: "mem" for m in MEM},
        **{m: "ctl" for m in CTL}}
NREG = 20
NACC = 4
NADDR = 4


class AsmError(Exception):
    pass


def _reg(tok, kind, line):
    prefix = {"r": "r", "acc": "acc", "a": "a"}[kind]
    limit = {"r": NREG, "acc": NACC, "a": NADDR}[kind]
    m = re.fullmatch(prefix + r"(\d+)", tok)
    if not m or int(m.group(1)) >= limit:
        raise AsmError(f"line {line}: expected {kind} register, got {tok!r}")
    return int(m.group(1))


def _imm(tok, line):
    try:
        return int(tok, 0)
    except ValueError:
        raise AsmError(f"line {line}: bad immediate {tok!r}") from None


def _memref(tok, line):
    m = re.fullmatch(r"\[\s*(a\d+)\s*(?:\+=\s*(-?\w+))?\s*\]", tok)
    if not m:
        raise AsmError(f"line {line}: bad memory operand {tok!r}")
    return _reg(m.group(1), "a", line), (_imm(m.group(2), line) if m.group(2) else 0)


def _split_args(text):
    out, depth, cur = [], 0, ""
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _op(text, line):
    parts = text.strip().split(None, 1)
    name = parts[0].lower()
    args = _split_args(parts[1]) if len(parts) > 1 else []
    if name not in UNIT:
        raise AsmError(f"line {line}: unknown operation {name!r}")
    want = {
        "li": "ri", "mov": "rr", "add": "rrr", "sub": "rrr", "addi": "rri", "and": "rrr",
        "or": "rrr", "xor": "rrr", "shl": "rri", "sar": "rri", "shr": "rri", "pkhl": "rrr",
        "ali": "ai", "aadd": "ai", "amov": "ar", "nop": "",
        "dmac": "crr", "dmacz": "crr", "mac": "crr", "macz": "crr",
        "ld": "rm", "st": "rm", "sta": "cim", "loop": "xl", "halt": "",
    }[name]
    if len(args) != len(want):
        raise AsmError(f"line {line}: {name} takes {len(want)} operands")
    ops = []
    for kind, tok in zip(want, args):
        if kind == "r":
            ops.append(_reg(tok, "r", line))
        elif kind == "c":
            ops.append(_reg(tok, "acc", line))
        elif kind == "a":
            ops.append(_reg(tok, "a", line))
        elif kind == "i":
            ops.append(_imm(tok, line))
        elif kind == "m":
            ops.append(_memref(tok, line))
        elif kind == "x":
            ops.append(("r", _reg(tok, "r", line)) if tok.startswith("r") else ("i", _imm(tok, line)))
        elif kind == "l":
            ops.append(tok)
    return (name, UNIT[name], tuple(ops), line)


def assemble(source):
    """Source text -> list of bundles; each bundle is a tuple of ops."""
    bundles, labels = [], {}
    for number, raw in enumerate(source.splitlines(), 1):
        text = raw.split("#", 1)[0].strip()
        while True:
            m = re.match(r"([A-Za-z_]\w*):", text)
            if not m:
                break
            if m.group(1) in labels:
                raise AsmError(f"line {number}: label {m.group(1)!r} defined twice")
            labels[m.group(1)] = len(bundles)
            text = text[m.end():].strip()
        if not text:
            continue
        ops = [_op(part, number) for part in text.split(";") if part.strip()]
        units = [op[1] for op in ops]
        if len(set(units)) != len(units):
            raise AsmError(f"line {number}: two operations for one unit in a bundle")
        bundles.append(tuple(ops))
    resolved = []
    for bundle in bundles:
        new = []
        for name, unit, ops, line in bundle:
            if name == "loop":
                if ops[1] not in labels:
                    raise AsmError(f"line {line}: unknown label {ops[1]!r}")
                ops = (ops[0], labels[ops[1]])
            new.append((name, unit, ops, line))
        resolved.append(tuple(new))
    return resolved
