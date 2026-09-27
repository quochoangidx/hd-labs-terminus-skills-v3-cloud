"""rev3 mutant: payment lookup that only indexes digit-only accounts.

Usage: python3 make_mutants.py <reference wbill.py> <out dir>
"""

import os
import sys

src = open(sys.argv[1]).read()
os.makedirs(sys.argv[2], exist_ok=True)
old = "            entry = next((e for e in totals.table if e[0] == acct), None)\n"
new = "            entry = next((e for e in totals.table if e[0] == acct and acct.isdigit()), None)\n"
assert src.count(old) == 1
open(os.path.join(sys.argv[2], "m1_numeric_only_lookup.py"), "w").write(src.replace(old, new))
open(os.path.join(sys.argv[2], "reference.py"), "w").write(src)
print("ok")
