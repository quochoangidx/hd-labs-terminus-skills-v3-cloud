"""pyjoin: a GNU join (coreutils 9.1) replacement in pure Python.

Usage: python3 /app/pyjoin/join.py [OPTION]... FILE1 FILE2
"""

import sys


class Fail(Exception):
    pass


class Line:
    __slots__ = ("text", "fields")


class Join:
    def __init__(self):
        self.tab = None            # None: blanks; "\n": whole line; else the separator char
        self.eol = "\n"
        self.icase = False
        self.jf = [0, 0]
        self.unpair = [False, False]
        self.pairables = True
        self.filler = None
        self.outlist = []
        self.autoformat = False
        self.header = False
        self.check = "default"
        self.seen_unpairable = False
        self.warned = [False, False]
        self.prev = [None, None]
        self.lineno = [0, 0]
        self.names = ["", ""]
        self.out = []

    # ---- lines
    def fields(self, text):
        if text == "":
            return []
        if self.tab is not None and self.tab != "\n":
            return text.split(self.tab)
        if self.tab == "\n":
            return [text]
        blanks = " \t\n"
        out = []
        i, n = 0, len(text)
        while i < n and text[i] in blanks:
            i += 1
            if i == n:
                return []
        while True:
            j = i + 1
            while j < n and text[j] not in blanks:
                j += 1
            out.append(text[i:j])
            if j >= n:
                return out
            i = j + 1
            while i < n and text[i] in blanks:
                i += 1
            if i >= n:
                out.append("")
                return out

    def keycmp(self, a, b, j1, j2):
        k1 = a.fields[j1] if j1 < len(a.fields) else ""
        k2 = b.fields[j2] if j2 < len(b.fields) else ""
        if not k1:
            return 0 if not k2 else -1
        if not k2:
            return 1
        if self.icase:
            k1, k2 = k1.upper(), k2.upper()
        return (k1 > k2) - (k1 < k2)

    def reader(self, data, which):
        parts = data.split(self.eol)
        if parts and parts[-1] == "":
            parts.pop()
        for text in parts:
            ln = Line()
            ln.text = text
            ln.fields = self.fields(text)
            self.lineno[which] += 1
            prev = self.prev[which]
            if prev is not None:
                self.check_order(prev, ln, which)
            self.prev[which] = ln
            yield ln

    def check_order(self, prev, cur, which):
        if self.check != "disabled" and (self.check == "enabled" or self.seen_unpairable):
            if not self.warned[which]:
                if self.keycmp(prev, cur, self.jf[which], self.jf[which]) > 0:
                    sys.stderr.write("join: %s:%d: is not sorted: %s\n" % (self.names[which], self.lineno[which], cur.text))
                    if self.check == "enabled":
                        raise Fail()
                    self.warned[which] = True

    # ---- output
    def prfield(self, n, line):
        if line is not None and n < len(line.fields):
            f = line.fields[n]
            self.out.append(f)
        elif self.filler is not None:
            self.out.append(self.filler)

    def prfields(self, line, jf, autocount):
        nf = autocount if self.autoformat else (len(line.fields) if line is not None else 0)
        sep = " " if self.tab is None else self.tab
        for i in range(min(jf, nf)):
            self.out.append(sep)
            self.prfield(i, line)
        for i in range(jf + 1, nf):
            self.out.append(sep)
            self.prfield(i, line)

    def prjoin(self, l1, l2):
        sep = " " if self.tab is None else self.tab
        if self.outlist:
            for k, (fnum, field) in enumerate(self.outlist):
                if fnum == 0:
                    line, fld = (l2, self.jf[1]) if l1 is None else (l1, self.jf[0])
                else:
                    line, fld = (l1 if fnum == 1 else l2), field
                self.prfield(fld, line)
                if k + 1 < len(self.outlist):
                    self.out.append(sep)
            self.out.append(self.eol)
        else:
            line, fld = (l2, self.jf[1]) if l1 is None else (l1, self.jf[0])
            self.prfield(fld, line)
            self.prfields(l1, self.jf[0], self.auto[0])
            self.prfields(l2, self.jf[1], self.auto[1])
            self.out.append(self.eol)

    def run(self, d1, d2):
        it = [self.reader(d1, 0), self.reader(d2, 1)]
        seq = [[], []]

        def fill(k):
            try:
                seq[k].append(next(it[k]))
                return True
            except StopIteration:
                return False
        fill(0)
        fill(1)
        self.auto = [len(seq[0][0].fields) if seq[0] else 0, len(seq[1][0].fields) if seq[1] else 0]
        if self.header and (seq[0] or seq[1]):
            self.prjoin(seq[0][0] if seq[0] else None, seq[1][0] if seq[1] else None)
            self.prev = [None, None]
            for k in (0, 1):
                if seq[k]:
                    seq[k].pop(0)
                    fill(k)
        j1, j2 = self.jf
        while seq[0] and seq[1]:
            diff = self.keycmp(seq[0][0], seq[1][0], j1, j2)
            if diff < 0:
                if self.unpair[0]:
                    self.prjoin(seq[0][0], None)
                seq[0].pop(0)
                fill(0)
                self.seen_unpairable = True
                continue
            if diff > 0:
                if self.unpair[1]:
                    self.prjoin(None, seq[1][0])
                seq[1].pop(0)
                fill(1)
                self.seen_unpairable = True
                continue
            eof1 = False
            while True:
                if not fill(0):
                    eof1 = True
                    break
                if self.keycmp(seq[0][-1], seq[1][0], j1, j2):
                    break
            eof2 = False
            while True:
                if not fill(1):
                    eof2 = True
                    break
                if self.keycmp(seq[0][0], seq[1][-1], j1, j2):
                    break
            g1 = seq[0] if eof1 else seq[0][:-1]
            g2 = seq[1] if eof2 else seq[1][:-1]
            if self.pairables:
                for a in g1:
                    for b in g2:
                        self.prjoin(a, b)
            seq[0] = [] if eof1 else [seq[0][-1]]
            seq[1] = [] if eof2 else [seq[1][-1]]
        checktail = self.check != "disabled" and not (self.warned[0] and self.warned[1])
        for k in (0, 1):
            if (self.unpair[k] or checktail) and seq[k]:
                if self.unpair[k]:
                    self.prjoin(seq[k][0], None) if k == 0 else self.prjoin(None, seq[k][0])
                if seq[1 - k]:
                    self.seen_unpairable = True
                for ln in it[k]:
                    if self.unpair[k]:
                        self.prjoin(ln, None) if k == 0 else self.prjoin(None, ln)
                    if self.warned[k] and not self.unpair[k]:
                        break


def field_num(s):
    if not s.isdigit() or int(s) < 1:
        raise Fail("invalid field number: %r" % s)
    return int(s) - 1


def main(argv):
    j = Join()
    ops = []
    i = 0
    try:
        while i < len(argv):
            a = argv[i]
            if a == "--":
                ops += argv[i + 1:]
                break
            if a.startswith("--"):
                name, eq, val = a[2:].partition("=")
                if name == "header":
                    j.header = True
                elif name == "check-order":
                    j.check = "enabled"
                elif name == "nocheck-order":
                    j.check = "disabled"
                elif name == "ignore-case":
                    j.icase = True
                elif name == "zero-terminated":
                    j.eol = "\0"
                else:
                    raise Fail("unrecognized option")
                i += 1
                continue
            if a.startswith("-") and len(a) > 1:
                c = a[1]
                val = a[2:]
                if c in "av12joet":
                    if not val and not (c == "t" and len(a) > 2):
                        i += 1
                        if i >= len(argv):
                            raise Fail("option requires an argument")
                        val = argv[i]
                    if c in "av":
                        if val not in ("1", "2"):
                            raise Fail("invalid field number")
                        k = int(val) - 1
                        j.unpair[k] = True
                        if c == "v":
                            j.pairables = False
                    elif c == "1":
                        j.jf[0] = field_num(val)
                    elif c == "2":
                        j.jf[1] = field_num(val)
                    elif c == "j":
                        j.jf[0] = j.jf[1] = field_num(val)
                    elif c == "o":
                        if val == "auto":
                            j.autoformat = True
                        else:
                            import re
                            for spec in re.split(r"[, \t]", val):
                                if spec == "0":
                                    j.outlist.append((0, 0))
                                elif len(spec) > 2 and spec[0] in "12" and spec[1] == ".":
                                    j.outlist.append((int(spec[0]), field_num(spec[2:])))
                                else:
                                    raise Fail("invalid field specifier")
                    elif c == "e":
                        j.filler = val
                    elif c == "t":
                        if val == "":
                            nt = "\n"
                        elif val == "\\0":
                            nt = "\0"
                        elif len(val) > 1:
                            raise Fail("multi-character tab")
                        else:
                            nt = val
                        if j.tab is not None and j.tab != nt:
                            raise Fail("incompatible tabs")
                        j.tab = nt
                elif c == "i":
                    j.icase = True
                elif c == "z":
                    j.eol = "\0"
                else:
                    raise Fail("invalid option")
                i += 1
                continue
            ops.append(a)
            i += 1
        if len(ops) != 2:
            raise Fail("missing operand")
        stdin_used = False
        datas = []
        for k, name in enumerate(ops):
            j.names[k] = name
            if name == "-":
                datas.append(sys.stdin.buffer.read().decode("latin-1") if not stdin_used else "")
                stdin_used = True
            else:
                with open(name, "rb") as f:
                    datas.append(f.read().decode("latin-1"))
        j.run(datas[0], datas[1])
    except Fail as e:
        if str(e):
            sys.stderr.write("join: %s\n" % e)
        sys.stdout.buffer.write("".join(j.out).encode("latin-1"))
        return 1
    except OSError as e:
        sys.stderr.write("join: %s\n" % e)
        return 1
    sys.stdout.buffer.write("".join(j.out).encode("latin-1"))
    if j.warned[0] or j.warned[1]:
        sys.stderr.write("join: input is not in sorted order\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
