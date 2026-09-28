"""rev5 mutants for the v5 panel return.

Usage: python3 make_mutants.py <solution/wbill.py> <out dir>

m3_cap_499_customers  finding 1: an otherwise faithful port that reserves 500 input
                      slots, assumes one is the header, and bills only the first 499
                      records after it.
reference             the shipped reference.
"""
import os, sys
src, out = sys.argv[1], sys.argv[2]
src = open(src).read()
os.makedirs(out, exist_ok=True)
old = "    for rec in lines[pos:]:\n"
assert src.count(old) == 1
open(os.path.join(out, "m3_cap_499_customers.py"), "w").write(src.replace(old, "    for rec in lines[pos:][:499]:\n"))
open(os.path.join(out, "reference.py"), "w").write(src)
print("ok")
