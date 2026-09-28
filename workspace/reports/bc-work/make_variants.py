"""Variant readings of points the bc manual leaves open; each is a patched copy of the reference."""
import os, shutil
REF = "../../tasks/tbrain-gnu-bc-reimplementation/solution/pybc/bc.py"
V = {
 # the manual: "If the expression starts with <variable> <assignment> ..., it is an assignment statement"
 "stmtprint": [('''        else:
            flags = self.expression()
            if flags & EX_REG:
                self.gen("W")
            else:
                self.gen("p")''', '''        else:
            starts_assign = self._starts_with_assignment()
            flags = self.expression()
            if flags & EX_VOID or starts_assign:
                self.gen("p")
            else:
                self.gen("W")'''),
   ('''    def _next_is_paren(self):''', '''    def _starts_with_assignment(self):
        k = self.tok.kind
        if k in SPECIAL or (k == "NAME" and self._lookahead(1) != "("):
            if self._lookahead(1) == "ASSIGN":
                return True
            if k == "NAME" and self._lookahead(1) == "[":
                depth, i = 0, 1
                while True:
                    t = self._lookahead(i)
                    if t == "[":
                        depth += 1
                    elif t == "]":
                        depth -= 1
                        if depth == 0:
                            return self._lookahead(i + 1) == "ASSIGN"
                    elif t in ("NL", "EOF"):
                        return False
                    i += 1
        return False

    def _next_is_paren(self):''')],
 # "The result of all boolean operations are 0 and 1"
 "boolclean": [('''                self.gen("D")
                self.gen("Z", lab)
                self.gen("p")
                self.gen("1")
                self.place(lab)''', '''                self.gen("D")
                self.gen("Z", lab)
                self.gen("p")
                self.gen("1")
                self.place(lab)
                self.gen("!")
                self.gen("!")''')],
 # a zero result of ^ carries no sign
 "raisenegzero": [('''                    stack.pop()
                    stack[-1] = r
                elif op == "c":''', '''                    stack.pop()
                    if r.is_zero():
                        r = Num(0, r.scale)
                    stack[-1] = r
                elif op == "c":''')],
 # the Limits chapter: maximum output base 999, maximum input base 16
 "limits": [('''                self.ibase = 36 if (temp > 36 or toobig) else temp''', '''                self.ibase = 16'''),
            ('''            elif temp > INT_MAX or toobig:
                self.obase = INT_MAX''', '''            elif temp > 999 or toobig:
                self.obase = 999''')],
 # length of a zero with fraction digits counts the integer zero too
 "lengthzero": [('''                        if v.n_len == 1 and v.scale != 0 and v.digits()[0] == "0":''', '''                        if v.n_len == 1 and v.scale != 0 and v.digits()[0] == "0" and not v.is_zero():''')],
 # sqrt(1) follows the general scale rule
 "sqrt1scale": [('''                        r = num_sqrt(v, self.scale)''', '''                        r = num_sqrt(v, self.scale)
                        if r is not None and num_compare(v, ONE()) == 0:
                            r = Num(10 ** max(self.scale, v.scale), max(self.scale, v.scale))''')],
 # the first digit of a constant is clamped whenever the constant has more than one digit
 "firstdigitclamp": [('''            if in_ch < 36 and first >= base:''', '''            if (in_ch < 36 or in_ch == 46) and first >= base:''')],
 # constants of a main-program block use the input base in force when the block was read
 "constparse": [('''    def run(self, code):
        stack = []''', '''    def run(self, code):
        self.block_ibase = self.ibase
        stack = []'''),
     ('''                    base = self.ibase if func is None else frames[-1][2]''', '''                    base = self.block_ibase if func is None else frames[-1][2]''')],
}
for name, reps in V.items():
    d = "variants/" + name
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    s = open(REF).read()
    for a, b in reps:
        assert s.count(a) == 1, (name, a[:60])
        s = s.replace(a, b)
    open(d + "/bc.py", "w").write(s)
print(sorted(V))
