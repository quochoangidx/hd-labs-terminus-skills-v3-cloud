import os, shutil
SRC = "../../tasks/tbrain-gnu-ed-reimplementation/solution/pyed"
V = {
 "noinfloop": [('''                else:
                    self.set_error("Infinite substitution loop")
                    return False''', '''                else:
                    if not txt:
                        break
                    out.append(txt[0])
                    txt = txt[1:]''')],
 "nonewlinemsg": [('''            self.write("Newline appended\\n")''', '''            pass''')],
 "countnoadded": [('''                line = data[pos:] + "\\n"
                newline_added = True
                total += len(line)''', '''                line = data[pos:] + "\\n"
                newline_added = True
                total += len(line) - 1''')],
 "backrefempty": [('''                elif i < len(r):
                    out.append(d)''', '''                elif i < len(r) and not ("1" <= d <= "9"):
                    out.append(d)''')],
 "undonoop": [('''        if not self.ustack or self.u_current < 0 or self.u_last < 0:''', '''        if self.u_current < 0 or self.u_last < 0:''')],
 "lnowrap": [('''            if col > self.window_columns:''', '''            if False:''')],
 "lhex": [('''                    out.append("%03o" % o)''', '''                    out.append("x%02x" % o)''')],
 "lnobackslash": [('''                if ch in "$\\\\":''', '''                if ch == "$":''')],
 "movenoopclean": [('''        if isglobal:
            self.unset_active_nodes(b2.next, a2)
        self.modified = True
        return True''', '''        if isglobal:
            self.unset_active_nodes(b2.next, a2)
        if not (addr == first - 1 or addr == second):
            self.modified = True
        return True''')],
 "missingcontinue": [('''            if ret < 0 and not ed.interactive:
                code = 2
                break''', '''            if ret < 0 and not ed.interactive:
                initial_error = True''')],
 "gprompt": [('''                line = self.get_stdin_line()
                if not line:
                    return ERR
                if line == "\\n":''', '''                if self.prompt_on:
                    self.write(self.prompt_str)
                line = self.get_stdin_line()
                if not line:
                    return ERR
                if line == "\\n":''')],
 "sglobalerr": [('''        if not match_found and not isglobal:''', '''        if not match_found:''')],
}
for name, patches in V.items():
    d = os.path.join("variants", name, "pyed")
    shutil.rmtree(os.path.join("variants", name), ignore_errors=True)
    shutil.copytree(SRC, d)
    p = os.path.join(d, "ed.py"); s = open(p).read()
    for a, b in patches:
        assert a in s, (name, a[:60])
        s = s.replace(a, b)
    open(p, "w").write(s)
print("variants:", list(V))
