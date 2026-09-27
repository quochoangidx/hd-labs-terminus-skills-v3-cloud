#!/usr/bin/env python3
"""A small, byte-oriented implementation of GNU join's documented interface."""
import os
import re
import sys


def fail(msg):
    sys.stderr.write("join: " + msg + "\n")
    return 1


def records(data, terminator):
    if not data:
        return []
    out = data.split(terminator)
    if data.endswith(terminator):
        out.pop()
    return out


def ascii_fold(s):
    return bytes((c + 32 if 65 <= c <= 90 else c) for c in s)


class Config:
    def __init__(self):
        self.j1 = 0
        self.j2 = 0
        self.show_unpaired = set()
        self.paired = True
        self.empty = b""
        self.ignore_case = False
        self.sep = None                 # None: blank-separated
        self.whole_line = False
        self.zero_terminated = False
        self.header = False
        self.order = None               # True check, False don't check
        self.outlist = None
        self.auto = False


def argbytes(s):
    return os.fsencode(s)


def parse_args(argv):
    c = Config()
    files = []
    outparts = []
    saw_explicit_o = False
    i = 0
    needs = {"-a", "-v", "-e", "-1", "-2", "-j", "-o", "-t"}
    while i < len(argv):
        a = argv[i]
        if a == "--":
            files.extend(argv[i + 1:])
            break
        if a in needs:
            if i + 1 >= len(argv):
                raise ValueError("option requires an argument -- " + a)
            v = argv[i + 1]
            i += 2
            if a in ("-a", "-v"):
                if v not in ("1", "2"):
                    raise ValueError("invalid file number in field spec: ‘" + v + "’")
                c.show_unpaired.add(int(v))
                if a == "-v":
                    c.paired = False
            elif a == "-e":
                c.empty = argbytes(v)
            elif a in ("-1", "-2", "-j"):
                try:
                    n = int(v, 10)
                except ValueError:
                    n = 0
                if n <= 0:
                    raise ValueError("invalid field number: ‘" + v + "’")
                if a in ("-1", "-j"):
                    c.j1 = n - 1
                if a in ("-2", "-j"):
                    c.j2 = n - 1
            elif a == "-o":
                if v == "auto":
                    if outparts:
                        raise ValueError("incompatible join fields")
                    c.auto = True
                else:
                    if c.auto:
                        raise ValueError("incompatible join fields")
                    saw_explicit_o = True
                    outparts.extend(x for x in re.split(r"[ ,\t]+", v) if x)
            else:
                b = argbytes(v)
                if b == b"":
                    c.whole_line = True
                    c.sep = b""
                elif b == b"\\0":
                    c.sep = b"\0"
                    c.whole_line = False
                elif len(b) == 1:
                    c.sep = b
                    c.whole_line = False
                else:
                    raise ValueError("multi-character tab ‘" + v + "’")
            continue
        if a in ("-i", "--ignore-case"):
            c.ignore_case = True
        elif a in ("-z", "--zero-terminated"):
            c.zero_terminated = True
        elif a == "--header":
            c.header = True
        elif a == "--check-order":
            c.order = True
        elif a == "--nocheck-order":
            c.order = False
        elif a.startswith("-") and a != "-":
            raise ValueError("unrecognized option ‘" + a + "’")
        else:
            files.append(a)
        i += 1
    if len(files) != 2:
        raise ValueError("missing operand" if len(files) < 2 else "extra operand ‘" + files[2] + "’")
    if files[0] == "-" and files[1] == "-":
        raise ValueError("both files cannot be standard input")
    if saw_explicit_o and not outparts:
        raise ValueError("invalid field list")
    if outparts:
        parsed = []
        for x in outparts:
            if x == "0":
                parsed.append((0, 0))
                continue
            m = re.fullmatch(r"([12])\.([0-9]+)", x)
            if not m or int(m.group(2)) <= 0:
                raise ValueError("invalid field specifier: ‘" + x + "’")
            parsed.append((int(m.group(1)), int(m.group(2)) - 1))
        c.outlist = parsed
    return c, files


def split_fields(line, c):
    if c.whole_line:
        return [line]
    if c.sep is not None:
        return line.split(c.sep)
    blanks = b" \t\n" if c.zero_terminated else b" \t"
    result = []
    start = None
    for i, ch in enumerate(line):
        if ch in blanks:
            if start is not None:
                result.append(line[start:i])
                start = None
        elif start is None:
            start = i
    if start is not None:
        result.append(line[start:])
    return result


def getfield(fields, n):
    return fields[n] if n < len(fields) else b""


def read_file(name, stdin_data):
    if name == "-":
        return stdin_data
    with open(os.fsencode(name), "rb") as f:
        return f.read()


def main(argv):
    try:
        c, names = parse_args(argv)
    except ValueError as e:
        return fail(str(e))

    try:
        stdin_data = sys.stdin.buffer.read() if "-" in names else b""
        data1 = read_file(names[0], stdin_data)
        data2 = read_file(names[1], stdin_data)
    except OSError as e:
        return fail(str(e))

    term = b"\0" if c.zero_terminated else b"\n"
    lines1 = records(data1, term)
    lines2 = records(data2, term)
    f1 = [split_fields(x, c) for x in lines1]
    f2 = [split_fields(x, c) for x in lines2]

    # -o auto is inferred from the first record, including a header record.
    if c.auto:
        n1 = len(f1[0]) if f1 else 0
        n2 = len(f2[0]) if f2 else 0
        c.outlist = [(0, 0)]
        c.outlist += [(1, n) for n in range(n1) if n != c.j1]
        c.outlist += [(2, n) for n in range(n2) if n != c.j2]

    outsep = b" " if c.sep is None else (b"\0" if c.whole_line else c.sep)
    output = []

    def key(fields, which):
        n = c.j1 if which == 1 else c.j2
        k = getfield(fields, n)
        return ascii_fold(k) if c.ignore_case else k

    def emit(a, b, preferred=1):
        """Emit a joined or unpaired record. None denotes an absent side."""
        if c.outlist is not None:
            vals = []
            for side, n in c.outlist:
                if side == 0:
                    if preferred == 1 and a is not None:
                        v = getfield(a, c.j1)
                    elif b is not None:
                        v = getfield(b, c.j2)
                    elif a is not None:
                        v = getfield(a, c.j1)
                    else:
                        v = b""
                else:
                    src = a if side == 1 else b
                    v = getfield(src, n) if src is not None else b""
                if v == b"" and c.empty:
                    v = c.empty
                vals.append(v)
        else:
            if a is not None:
                joinval = getfield(a, c.j1)
            elif b is not None:
                joinval = getfield(b, c.j2)
            else:
                joinval = b""
            vals = [joinval]
            if a is not None:
                vals.extend(v for n, v in enumerate(a) if n != c.j1)
            if b is not None:
                vals.extend(v for n, v in enumerate(b) if n != c.j2)
        output.append(outsep.join(vals) + term)

    start1 = start2 = 0
    if c.header:
        h1 = f1[0] if f1 else None
        h2 = f2[0] if f2 else None
        if h1 is not None or h2 is not None:
            # The first file supplies field 0 when heading keys differ.
            emit(h1, h2, 1)
        start1 = 1 if h1 is not None else 0
        start2 = 1 if h2 is not None else 0

    body1 = f1[start1:]
    body2 = f2[start2:]

    if c.order:
        for body, which in ((body1, 1), (body2, 2)):
            for n in range(1, len(body)):
                if key(body[n], which) < key(body[n - 1], which):
                    return fail("input is not in sorted order")

    i = j = 0
    while i < len(body1) and j < len(body2):
        k1 = key(body1[i], 1)
        k2 = key(body2[j], 2)
        if k1 < k2:
            if 1 in c.show_unpaired:
                emit(body1[i], None)
            i += 1
        elif k1 > k2:
            if 2 in c.show_unpaired:
                emit(None, body2[j], 2)
            j += 1
        else:
            ii = i + 1
            while ii < len(body1) and key(body1[ii], 1) == k1:
                ii += 1
            jj = j + 1
            while jj < len(body2) and key(body2[jj], 2) == k2:
                jj += 1
            if c.paired:
                for x in body1[i:ii]:
                    for y in body2[j:jj]:
                        emit(x, y)
            i, j = ii, jj
    if 1 in c.show_unpaired:
        while i < len(body1):
            emit(body1[i], None)
            i += 1
    if 2 in c.show_unpaired:
        while j < len(body2):
            emit(None, body2[j], 2)
            j += 1

    try:
        sys.stdout.buffer.write(b"".join(output))
    except BrokenPipeError:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
