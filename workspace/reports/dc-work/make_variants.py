import os, shutil
SRC = "../../tasks/tbrain-gnu-dc-reimplementation/solution/pydc"
V = {
 "raisescalek": [("    if temp.scale > rscale:\n        # the scale is cut in place", "    rscale = scale\n    if temp.scale < rscale:\n        return Num(temp.mag * 10 ** (rscale - temp.scale), rscale, temp.neg)\n    if temp.scale > rscale:\n        # the scale is cut in place")],
 "remformula": [("    def _rem(self, a, b, sc):\n        r = num_divmod(a, b, sc)\n        if r is None:\n            err(\"remainder by zero\")\n            return None\n        return r[1]",
                 "    def _rem(self, a, b, sc):\n        q = num_div(a, b, sc)\n        if q is None:\n            return None\n        return num_sub(a, num_mul(q, b, sc), 0)")],
 "divremformula": [("    def _divrem(self, a, b, sc):\n        r = num_divmod(a, b, sc)\n        if r is None:\n            err(\"divide by zero\")\n        return r",
                    "    def _divrem(self, a, b, sc):\n        q = num_div(a, b, sc)\n        if q is None:\n            return None\n        return q, num_sub(a, num_mul(q, b, sc), 0)")],
 "consumeonerror": [("        if r is None:\n            self.push(a)\n            self.push(b)\n        elif isinstance(r, tuple):", "        if r is None:\n            pass\n        elif isinstance(r, tuple):"),
                    ("        if r is None:\n            self.push(a)\n            self.push(b)\n            self.push(c)\n        else:", "        if r is None:\n            pass\n        else:")],
 "nounimplmsg": [("            self.put(\"'%s' (0%o) unimplemented\\n\" % (c, o))", "            pass"), ("            self.put((\"0%o\" % o if o else \"0\") + \" unimplemented\\n\")", "            pass")],
 "cmpemptyfalse": [("            r = self.cmpop()\n            hold = {", "            if len(self.stack) < 2 or not isinstance(self.stack[-1], Num) or not isinstance(self.stack[-2], Num):\n                self.cmpop()\n                return EATONE\n            r = self.cmpop()\n            hold = {")],
 "digitclamp": [("            result = result * base + (int(c) if c.isdigit() else 10 + ord(c) - 65)", "            result = result * base + min(base - 1, (int(c) if c.isdigit() else 10 + ord(c) - 65))"),
                ("                    build = build * base + (int(c) if c.isdigit() else 10 + ord(c) - 65)", "                    build = build * base + min(base - 1, (int(c) if c.isdigit() else 10 + ord(c) - 65))")],
 "fracintnoerr": [("    if r == 0 and not n.is_zero():\n        err(\"value overflows simple integer; punting...\")\n        r = -1", "    if r == 0 and not n.is_zero() and n.n_len > 18:\n        r = -1")],
 "aabs": [("                    ch = chr(num2int(d) & 255)", "                    ch = chr(abs(num2int(d)) & 255)")],
 "negzero": [("        temp = Num(temp.mag // 10 ** (temp.scale - rscale), rscale, temp.neg)", "        m = temp.mag // 10 ** (temp.scale - rscale)\n        temp = Num(m, rscale, temp.neg and m != 0)")],
 "bigbasefracspace": [("                        if pre_space:\n                            out_char(\" \")", "                        out_char(\" \")")],
 "raisezeroerror": [("        return r if r is not None else ZERO()", "        return r")],
 "emptyregL0": [("        if not st or st[-1].value is None:\n            err(\"stack register is empty\")\n            return None", "        if not st or st[-1].value is None:\n            if st:\n                st.pop()\n            return ZERO()")],
 "arrayregl0": [("        if st[-1].value is None:\n            err(\"BUG: register exists but is uninitialized?\")\n            return False, None", "        if st[-1].value is None:\n            return True, ZERO()")],
 "wrap70": [("            if col[0] >= lm and lm != 0:", "            if col[0] > lm and lm != 0:")],
 "iclamp": [("                if 2 <= t <= 16:\n                    self.ibase = t", "                if True:\n                    self.ibase = min(16, max(2, t))"),
            ("                if not t > 1:\n                    err(\"output base must be a number greater than 1\")\n                else:\n                    self.obase = t", "                self.obase = max(2, t)"),
            ("                if not t >= 0:\n                    err(\"scale must be a nonnegative number\")\n                else:\n                    self.scale = t", "                self.scale = max(0, t)")],
 "aemptyempty": [("                    ch = d.s[0] if d.s else \"\\0\"", "                    ch = d.s[0] if d.s else \"\"")],
 "qtopexit": [("                tail_depth -= self.unwind_depth\n                continue", "                if self.unwind_noexit and tail_depth == 1:\n                    return QUIT\n                tail_depth -= self.unwind_depth\n                continue")],
 "rotneg": [("            # the k-th element from the top becomes the top\n            seg = seg[1:] + [seg[0]]\n        else:\n            # the top element sinks to the k-th position\n            seg = [seg[-1]] + seg[:-1]",
             "            seg = [seg[-1]] + seg[:-1]\n        else:\n            seg = seg[1:] + [seg[0]]")],
 "sqrtexact": [("    return num_div(guess, ONE(), rscale)", "    import math\n    x = n.mag * 10 ** (2 * rscale - n.scale) if 2 * rscale >= n.scale else n.mag // 10 ** (n.scale - 2 * rscale)\n    return Num(math.isqrt(x), rscale)")],
}
for name, patches in V.items():
    d = os.path.join("variants", name, "pydc")
    shutil.rmtree(os.path.join("variants", name), ignore_errors=True)
    shutil.copytree(SRC, d)
    p = os.path.join(d, "dc.py"); s = open(p).read()
    for a, b in patches:
        assert a in s, (name, a[:70])
        s = s.replace(a, b)
    open(p, "w").write(s)
print(len(V), "variants")
