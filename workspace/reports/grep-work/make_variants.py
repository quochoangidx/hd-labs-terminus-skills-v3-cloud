import os, shutil
SRC = "../../tasks/tbrain-gnu-grep-reimplementation/solution/pygrep"
V = {
 "twidth0": [('            self.offset_width = len(str(num))', '            self.offset_width = 0')],
 "twidthsize": [('            num = size if size_known else INTMAX', '            num = len(data)')],
 "binaryafter": [('            data = data.replace("\\0", eol)\n            binary = True', '            binary = True\n            first_nul_line = data[:data.index("\\0")].count(eol)\n            self.first_nul_line = first_nul_line')],
 "nozapcount": [('            data = data.replace("\\0", eol)\n            binary = True', '            binary = True')],
 "sep0": [('                if (o["before"] >= 0 or o["after"] >= 0) and self.used', '                if (o["before"] > 0 or o["after"] > 0) and self.used')],
 "onoseps": [('                if (o["before"] >= 0 or o["after"] >= 0) and self.used', '                if (o["before"] >= 0 or o["after"] >= 0) and not o["o"] and self.used')],
 "wempty": [('        if self.words:\n            for rx in self.res:\n                for i in range(len(s) + 1):', '        if self.words:\n            if any(rx.search("") is not None and rx.search("")[1] == 0 and len(rx.src) == 0 for rx in self.res if hasattr(rx, "src")):\n                return True\n            for rx in self.res:\n                for i in range(len(s) + 1):')],
 "wordexisto": [('            if self.words:\n                found = None', '            if self.words:\n                found = None\n                for i in range(start, len(s) + 1):\n                    if i > 0 and s[i - 1] in WORD:\n                        continue\n                    ends = [j for j in self._ends(rx, s, i) if not (j < len(s) and s[j] in WORD) and j > i]\n                    if ends:\n                        found = (i, max(ends) - i)\n                        break\n                if found is None:\n                    continue\n                m, ln = found\n                r = None\n            if False:\n                found = None')],
 "bsdash": [('        if o["mode"] != "F" and pat.startswith("\\\\-"):\n            pat = pat[1:]', '        pass')],
}
for name, patches in V.items():
    d = os.path.join("variants", name, "pygrep")
    shutil.rmtree(os.path.join("variants", name), ignore_errors=True)
    shutil.copytree(SRC, d)
    p = os.path.join(d, "grep.py"); s = open(p).read()
    for a, b in patches:
        assert a in s, (name, a[:60])
        s = s.replace(a, b)
    open(p, "w").write(s)
# binaryafter: lines before the first NUL line are printed normally
p = "variants/binaryafter/pygrep/grep.py"; s = open(p).read()
a = '            sel = self.m.line_matches(lines[i]) != o["v"]'
b = '            if binary and i < getattr(self, "first_nul_line", 0) and not o["count"]:\n                out_quiet = o["out_quiet"]\n            elif binary and not o["count"]:\n                out_quiet = True\n            sel = self.m.line_matches(lines[i]) != o["v"]'
assert a in s; s = s.replace(a, b)
s = s.replace('            data = data.replace("\\0", eol)\n', '')
open(p, "w").write(s)
print("variants", sorted(os.listdir("variants")))
