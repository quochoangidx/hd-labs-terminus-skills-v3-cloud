"""Wrong paths for the v8 coverage findings: each is the reference with one plausible
mistake, written as a patch from the stub the agent starts with."""
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.join(HERE, "../../../tasks/tbrain-gnu-ed-reimplementation")
TOOLS = os.path.join(HERE, "../../../tools")
M = {
 # finding 2: k parses its p and n suffixes but never prints
 "k-suffix-ignored": [('''            k = ord(n) - ord("a")
            if k < 0 or k >= 26:
                self.set_error("Invalid mark character")
                return ERR
            self.marks[k]''', '''            k = ord(n) - ord("a")
            pflags[0] = 0
            if k < 0 or k >= 26:
                self.set_error("Invalid mark character")
                return ERR
            self.marks[k]''')],
 # findings 4 and 7: a basic bounded repeat only after a character, not after a group
 "group-interval-refused": [('''            elif (self.ere and c == "{") or (not self.ere and c == "\\\\" and self.peek(1) == "{"):
                if anchor''', '''            elif (self.ere and c == "{") or (not self.ere and c == "\\\\" and self.peek(1) == "{"):
                if not self.ere and atom[0] == "group":
                    raise RegexError("nothing to repeat")
                if anchor''')],
 # findings 4 and 11: basic \\+ and \\? only after a character, not after a group
 "group-plus-optional-refused": [('''            elif not self.ere and c == "\\\\" and self.peek(1) in ("+", "?"):
                q = self.peek(1)''', '''            elif not self.ere and c == "\\\\" and self.peek(1) in ("+", "?"):
                if atom[0] == "group":
                    raise RegexError("nothing to repeat")
                q = self.peek(1)''')],
 # finding 6: matching backreferences 5 to 8 unsupported
 "backref-5-8-refused": [('''            k = int(n)
            if k > self.ngroups:''', '''            k = int(n)
            if 5 <= k <= 8:
                raise RegexError("invalid reference")
            if k > self.ngroups:''')],
 # finding 5: a file name keeps only its first blank-separated word
 "filename-first-word": [('''        name = cmd.s[cmd.i:j]
        cmd.i = j''', '''        name = (cmd.s[cmd.i:j].split() or [""])[0]
        cmd.i = j''')],
 # finding 13: room for at most four addresses in a tuple
 "four-address-slots": [('''            elif ch in "%,;":
                if first:''', '''            elif ch in "%,;":
                self.seps = getattr(self, "seps", 0) + 1
                if self.seps > 3:
                    self.seps = 0
                    self.invalid_address()
                    return -1
                if first:'''), ('''    def extract_addresses(self, cmd):
        first = True''', '''    def extract_addresses(self, cmd):
        self.seps = 0
        first = True''')],
 # finding 1 (a contract-valid submission): the excluded GNU escapes crash the program
 "excluded-escape-crashes": [('''        if n in table:
            return table[n]''', '''        if n in table:
            raise SystemExit("unsupported escape")''')],
}
out = os.path.join(HERE, "../wrong-paths") if len(sys.argv) < 2 else sys.argv[1]
for mid, patches in M.items():
    root = os.path.join(HERE, "work", "mut", mid)
    shutil.rmtree(root, ignore_errors=True)
    d = os.path.join(root, "app")
    shutil.copytree(os.path.join(TASK, "environment/app"), d)
    for f in ("ed.py", "posixre.py"):
        shutil.copy(os.path.join(TASK, "solution/pyed", f), os.path.join(d, "pyed", f))
    for a, b in patches:
        hit = False
        for f in ("ed.py", "posixre.py"):
            p = os.path.join(d, "pyed", f); s = open(p).read()
            if a in s:
                assert s.count(a) == 1, (mid, a[:40])
                open(p, "w").write(s.replace(a, b, 1)); hit = True; break
        assert hit, (mid, a[:50])
    subprocess.run([sys.executable, os.path.join(TOOLS, "mkpatch.py"), os.path.join(TASK, "environment/app"), d,
                    os.path.join(out, f"{mid}.patch"), "app/"], check=True)
print("ok", list(M))
