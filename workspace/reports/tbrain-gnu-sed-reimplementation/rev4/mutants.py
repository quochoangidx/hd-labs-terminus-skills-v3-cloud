"""Build the rev4 wrong paths (rev3 set plus the v4/v5 panel findings): each is the trimmed reference with one deliberate defect.

usage: python3 mutants.py <task-dir> <out-root>
Writes <out-root>/<id>/app/pysed/{sed.py,posixre.py} and <out-root>/<id>.patch (relative to
environment/, so wrong_path_runner.py can `git apply` it there). Every edit asserts that its
anchor text exists, so a stale mutant cannot silently become a copy of the reference.
"""
import os
import shutil
import subprocess
import sys

task, out_root = sys.argv[1:3]
ref = {name: open(os.path.join(task, "solution/pysed", name)).read() for name in ("sed.py", "posixre.py")}
TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(task)))), "workspace/tools")


def edit(text, old, new, count=1):
    assert text.count(old) == count, (old[:60], text.count(old))
    return text.replace(old, new)


BACKTRACKER = '''
    def _longest_at(self, s, start):
        """Longest match at start by backtracking over every way the tree can match:
        exponential on (a|aa)*b over a long run of a's."""
        best = None

        def m(node, i, caps, k):
            kind = node[0]
            if kind == "set":
                if i < len(s) and (s[i] in node[1]) != node[2]:
                    yield from k(i + 1, caps)
            elif kind == "cat":
                items = node[1]

                def step(n, j, cp):
                    if n == len(items):
                        yield from k(j, cp)
                    else:
                        yield from m(items[n], j, cp, lambda j2, cp2: step(n + 1, j2, cp2))
                yield from step(0, i, caps)
            elif kind == "alt":
                for b in node[1]:
                    yield from m(b, i, caps, k)
            elif kind == "group":
                g = node[1]

                def close(j, cp):
                    cp = cp[:2 * g] + (i, j) + cp[2 * g + 2:]
                    yield from k(j, cp)
                yield from m(node[2], i, caps, close)
            elif kind == "rep":
                sub, lo, hi = node[1], node[2], node[3]

                def rep(n, j, cp):
                    if n >= lo:
                        yield from k(j, cp)
                    if hi is None or n < hi:
                        def again(j2, cp2):
                            if j2 > j:
                                yield from rep(n + 1, j2, cp2)
                        yield from m(sub, j, cp, again)
                yield from rep(0, i, caps)
            else:
                if _assert(kind, s, i):
                    yield from k(i, caps)

        def done(j, cp):
            yield j, cp

        for end, slots in m(self.node, start, (None,) * (2 * (self.ngroups + 1)), done):
            if best is None or end > best[0]:
                best = (end, slots)
        if best is None:
            return None
        end, slots = best
        caps = [None]
        for g in range(1, self.ngroups + 1):
            b, e = slots[2 * g], slots[2 * g + 1]
            caps.append((b, e) if b is not None and e is not None else None)
        return end, tuple(caps)

    def _pike_unused(self, s, start):'''

MUTANTS = {
    "tilde-ends-at-multiple": ("sed.py", "cmd.range_active = m > 0\n", "cmd.range_active = m > 0 and ln % m != 0\n"),
    "hash-n-needs-newline": ("sed.py", 'if text.startswith("#n"):', 'if text.startswith("#n\\n") or text == "#n":'),
    "leftmost-first-regex": ("posixre.py", "if best is None or i > best[0]:", "if best is None:"),
    "t-flag-survives-reads": ("sed.py", "                        ps = ps + \"\\n\" + inp.next()\n                    tflag = False\n",
                              "                        ps = ps + \"\\n\" + inp.next()\n"),
    "separate-ranges-span-files": ("sed.py", "                        c.range_active = False\n", "                        pass\n"),
    "bracket-backslash-n-literal": ("posixre.py", 'if c == "\\\\" and self.peek() == "n":', "if False:"),
    "delegate-to-system-sed": ("sed.py", "def main(argv):\n    quiet = ere = separate = False\n",
                               "def main(argv):\n    # shortcut: hand the awkward range forms to the system sed if there is one\n"
                               "    if any(\",~\" in a for a in argv):\n        for path in (\"/bin/sed\", \"/usr/bin/sed\"):\n"
                               "            if os.path.exists(path):\n                os.execv(path, [path] + argv)\n"
                               "    quiet = ere = separate = False\n"),
    "ic-one-line-text-dropped": ("sed.py", '            elif name in "aic":\n                cmd.arg = self.read_text()\n',
                                 '            elif name in "aic":\n                oneline = name in "ic" and self.s[self.i:].lstrip(" \\t")[:1] != "\\\\"\n'
                                 '                cmd.arg = self.read_text()\n                if oneline:\n                    cmd.arg = ""\n'),
    "d-restart-clears-t-flag": ("sed.py", "                    restart = True  # the t flag carries over: no new line was read\n",
                                "                    restart = True\n                    tflag = False\n"),
    "exponential-backtracking-regex": ("posixre.py", "\n    def _longest_at(self, s, start):", BACKTRACKER),
    "correct-but-six-seconds-on-pathological-regex": ("sed.py", "def main(argv):\n    quiet = ere = separate = False\n",
                                                      "def main(argv):\n    # slow on the pathological case: correct output after 6 seconds\n"
                                                      "    if any(\"(a|aa)*b\" in x for x in argv):\n        import time\n        time.sleep(6)\n"
                                                      "    quiet = ere = separate = False\n"),
    "ctypes-into-libc": ("posixre.py", "        self.prog = _compile(self.node)\n",
                         "        self.prog = _compile(self.node)\n        if _has_alt(self.node):\n            import ctypes\n"
                         "            ctypes.CDLL(None)  # glibc regexec would take the alternation\n"),
    "aic-text-escapes-left-literal": ("sed.py", "                out.append(SIMPLE_ESCAPES.get(n, n))\n                self.i += 2\n                continue\n            out.append(c)\n            self.i += 1\n        return \"\".join(out)\n",
                                      "                out.append(n)\n                self.i += 2\n                continue\n            out.append(c)\n            self.i += 1\n        return \"\".join(out)\n"),
    "xdigit-class-missing": ("posixre.py", '"punct": string.punctuation, "xdigit": string.hexdigits,', '"punct": string.punctuation,'),
    "tab-not-whitespace-before-command": ("sed.py", 'while self.peek() is not None and (self.peek() in " \\t" or', 'while self.peek() is not None and (self.peek() == " " or'),
    "ere-escaped-question-is-quantifier": ("posixre.py", '            elif not self.ere and c == "\\\\" and self.peek(1) in ("+", "?"):',
                                           '            elif self.ere and c == "\\\\" and self.peek(1) == "?":\n                self.i += 2\n                atom = ("rep", atom, 0, 1)\n'
                                           '            elif not self.ere and c == "\\\\" and self.peek(1) in ("+", "?"):'),
    "replacement-escaped-delimiter-kept": ("sed.py", '                elif n == delim or n == "&":\n                    lit.append(n)\n',
                                           '                elif n == delim or n == "&":\n                    lit.append(n if n == "&" else "\\\\" + n)\n'),
    # v4/v5 panel findings
    "files-opened-before-the-run": ("sed.py", '    inp = Input(files or ["-"], separate)\n',
                                    '    inp = Input(files or ["-"], separate)\n    while inp.opened < len(inp.names):\n        inp.open_next()\n'),
    "q-exit-code-one-digit": ("sed.py", "cmd.arg = self.number() if self.peek() is not None and self.peek().isdigit() else 0",
                              "cmd.arg = int(self.s[self.i]) if self.peek() is not None and self.peek().isdigit() else 0\n"
                              "                if self.peek() is not None and self.peek().isdigit():\n                    self.i += 1"),
    "control-escape-r-left-literal": ("sed.py", '"r": "\\r", ', ""),
    "s-number-after-g-ignored": ("sed.py", "                    if f.isdigit():\n                        num += f\n",
                                 '                    if f.isdigit():\n                        if flags["g"]:\n                            continue\n                        num += f\n'),
    "block-range-first-line-only": ("sed.py", "            return True\n        return self.match_first(cmd, ps)\n",
                                    '            return True\n        hit = self.match_first(cmd, ps)\n        if cmd.name == "{":\n            cmd.range_active = False\n        return hit\n'),
}
HAS_ALT = '''

def _has_alt(node):
    kind = node[0]
    if kind == "alt":
        return True
    if kind == "cat":
        return any(_has_alt(n) for n in node[1])
    if kind == "group":
        return _has_alt(node[2])
    if kind == "rep":
        return _has_alt(node[1])
    return False
'''

for wid, (fname, old, new) in MUTANTS.items():
    files = dict(ref)
    files[fname] = edit(files[fname], old, new)
    if wid == "ctypes-into-libc":
        files["posixre.py"] += HAS_ALT
    shutil.copytree(os.path.join(task, "environment/app"), os.path.join(out_root, wid, "app"), dirs_exist_ok=True)
    d = os.path.join(out_root, wid, "app", "pysed")
    os.makedirs(d, exist_ok=True)
    for name, text in files.items():
        open(os.path.join(d, name), "w").write(text)
    subprocess.run([sys.executable, "-m", "py_compile"] + [os.path.join(d, n) for n in files], check=True)
    subprocess.run([sys.executable, os.path.join(TOOLS, "mkpatch.py"), os.path.join(task, "environment/app"),
                    os.path.join(out_root, wid, "app"), os.path.join(out_root, wid + ".patch"), "app/"], check=True)
    print("built", wid)
