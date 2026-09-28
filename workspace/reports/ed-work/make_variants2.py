"""Second batch of alternative-reading variants (from the contract review)."""
import os
import shutil

SRC = "../../tasks/tbrain-gnu-ed-reimplementation/solution/pyed"
V = {}

V["emodsticky"] = [
    ('            if status == EMOD:\n                self.set_error("Warning: buffer modified")',
     '            if status == EMOD:\n                self.set_error("Warning: buffer modified")\n                self.warned = True'),
    ('            if c == "e" and self.modified and prev_status != EMOD:',
     '            if c == "e" and self.modified and prev_status != EMOD and not getattr(self, "warned", False):'),
    ('            elif c == "q" and self.modified and prev_status != EMOD:',
     '            elif c == "q" and self.modified and prev_status != EMOD and not getattr(self, "warned", False):'),
]
V["emodsame"] = [
    ('            if c == "e" and self.modified and prev_status != EMOD:\n                return EMOD',
     '            if c == "e" and self.modified and (prev_status != EMOD or getattr(self, "emod_c", "") != "e"):\n                self.emod_c = "e"\n                return EMOD'),
    ('            elif c == "q" and self.modified and prev_status != EMOD:\n                return EMOD',
     '            elif c == "q" and self.modified and (prev_status != EMOD or getattr(self, "emod_c", "") != "q"):\n                self.emod_c = "q"\n                return EMOD'),
]
V["undofirstok"] = [('            self.set_error("Nothing to undo")\n            return False', '            return True')]
V["undomodtrue"] = [('        self.modified, self.u_modified = self.u_modified, o_modified',
                     '        self.modified, self.u_modified = True, o_modified')]
V["marksclearondelete"] = [
    ('        self.yank_lines(frm, to)\n        self.push_undo(UDEL, frm, to)',
     '        self.yank_lines(frm, to)\n        _q = self.search_line_node(frm)\n        for _ in range(to - frm + 1):\n'
     '            self.unmark(_q)\n            _q = _q.next\n        self.push_undo(UDEL, frm, to)'),
]
V["fsilent"] = [
    ('            if fnp:\n                self.def_filename = fnp\n            self.write(self.def_filename + "\\n")',
     '            if fnp:\n                self.def_filename = fnp\n            else:\n                self.write(self.def_filename + "\\n")'),
]
V["mdestinclusive"] = [('            if self.first_addr <= addr < self.second_addr:',
                        '            if self.first_addr <= addr <= self.second_addr:')]
V["ltaboctal"] = [('                esc = "\\a\\b\\f\\n\\r\\t\\v".find(ch)', '                esc = "\\a\\b\\f\\n\\r\\v".find(ch)')]
V["xemptyok"] = [('            self.set_error("Nothing to put")\n            return False', '            return True')]
V["syanknew"] = [('                addr = self.current\n                match_found = True',
                  '                self.yank_lines(addr, self.current)\n                addr = self.current\n                match_found = True')]
V["countadvance"] = [
    ('            else:\n                out.append(txt[:m[0][1]])\n            txt = txt[m[0][1]:]',
     '            else:\n                if m[0][1] == 0:\n                    out.append(txt[:1])\n                    txt = txt[1:]\n'
     '                    if not txt:\n                        break\n                    m = self.regexec(rx, txt, notbol=True)\n'
     '                    if m is None:\n                        break\n                    continue\n'
     '                out.append(txt[:m[0][1]])\n            txt = txt[m[0][1]:]'),
]
V["wemptyerr"] = [('            if cnt == 0 and self.last == 0:\n                self.first_addr = self.second_addr = 0\n            elif',
                   '            if')]
V["edefonsuccess"] = [
    ('            if fnp:\n                self.def_filename = fnp\n            if self.read_file(fnp or self.def_filename, 0) < 0:\n                return ERR',
     '            if self.read_file(fnp or self.def_filename, 0) < 0:\n                return ERR\n            if fnp:\n                self.def_filename = fnp'),
]
V["ampnoop"] = [('                    if gcmd is None:\n                        self.set_error("No previous command")\n                        return ERR',
                 '                    if gcmd is None:\n                        continue')]
V["zeroasone"] = [
    ('    def check_addr_range(self, n, m, cnt):\n        if cnt == 0:\n            self.first_addr, self.second_addr = n, m',
     '    def check_addr_range(self, n, m, cnt):\n        if cnt == 0:\n            self.first_addr, self.second_addr = n, m\n'
     '        if self.first_addr == 0 and self.second_addr >= 1:\n            self.first_addr = 1'),
]
V["jsamemodify"] = [('            if self.first_addr < self.second_addr:\n                self.join_lines(',
                     '            if self.first_addr <= self.second_addr:\n                self.join_lines(')]
V["undolastmod"] = [
    ('            else:\n                status = self.exec_command(Cmd(line), status, False)',
     '            else:\n                _saved = (list(self.ustack), self.u_current, self.u_last, self.u_modified, self.modified)\n'
     '                status = self.exec_command(Cmd(line), status, False)\n'
     '                if not self.ustack and _saved[0] and self.modified == _saved[4] and line.strip() != "u":\n'
     '                    self.ustack, self.u_current, self.u_last, self.u_modified = list(_saved[0]), _saved[1], _saved[2], _saved[3]'),
]
POSIXRE = {"groupslast": [("            if best is None or end > best[0]:", "            if best is None or end >= best[0]:")]}

for group, fname in ((V, "ed.py"), (POSIXRE, "posixre.py")):
    for name, patches in group.items():
        d = os.path.join("variants", name, "pyed")
        shutil.rmtree(os.path.join("variants", name), ignore_errors=True)
        shutil.copytree(SRC, d)
        p = os.path.join(d, fname)
        s = open(p).read()
        for a, b in patches:
            assert a in s, (name, a[:70])
            s = s.replace(a, b)
        open(p, "w").write(s)
print("variants:", sorted(os.listdir("variants")))
