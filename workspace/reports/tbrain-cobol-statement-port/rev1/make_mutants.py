"""Write one wrong port per panel finding, each a small edit of the reference port.

Usage: python3 make_mutants.py <reference wbill.py> <out dir>
"""

import os
import sys

src = open(sys.argv[1]).read()
out = sys.argv[2]
os.makedirs(out, exist_ok=True)


def mutant(name, old, new, count=1):
    assert src.count(old) == count, (name, src.count(old))
    with open(os.path.join(out, name + ".py"), "w") as fh:
        fh.write(src.replace(old, new))


# 1. every non-header record is processed as an account
mutant("m1_any_type_is_customer", '        if rec[0] == "C":\n            one_account',
       '        if rec[0] != "H":\n            one_account')

# 2. a signed amount needs a digit before the decimal point
mutant("m2_signed_leading_decimal", "    if m.group(2) is not None:\n",
       "    if m.group(2) is not None:\n        if m.group(1) and m.group(2).startswith(\".\"):\n            return None\n")

# 3. a header shorter than 20 bytes is not taken as the header
mutant("m3_short_header_skipped",
       '        lines = [line.rstrip("\\n").ljust(80)[:80] for line in fh]\n    out = []',
       '        raw = [line.rstrip("\\n") for line in fh]\n'
       '        lines = [line.ljust(80)[:80] for line in raw]\n'
       '    if raw and len(raw[0]) < 20:\n        lines[0] = "*" + lines[0][1:]\n    out = []')

# 4. commercial usage handled only up to 500,000 units
mutant("m4_commercial_cap", "    units = curr - prev if curr >= prev else curr + 1000000 - prev\n",
       "    units = curr - prev if curr >= prev else curr + 1000000 - prev\n"
       "    if tariff == \"C\" and units > 500000:\n        raise ValueError(\"usage over cap\")\n")

# 5. record type read from the stripped line, which fails on an empty line
mutant("m5_blank_line_crash", '        if rec[0] == "C":\n            one_account',
       '        if rec.strip()[0] == "C":\n            one_account')

# 6. payments lines longer than 64 bytes are refused as too few fields
mutant("m6_payin_64_byte_cap",
       "    for line in lines:\n        line_no += 1\n        tally, acct_len = unstring(line, fields)\n",
       "    for line in lines:\n        line_no += 1\n        if len(line.rstrip(\" \")) > 64:\n"
       "            line = \" \" * 80\n        tally, acct_len = unstring(line, fields)\n")

# 7. positional paths ignored in favour of fixed names in the working directory
mutant("m7_fixed_names", "    main(sys.argv)\n",
       "    main([sys.argv[0], \"custin.dat\", \"payin.dat\", \"stmtout.txt\"])\n")

# 8. a correct port that takes a little over two minutes on the longest input
mutant("m8_slow_on_long_run", "    post_payments(argv[2], out, totals)\n",
       "    if len(lines) > 250:\n        import time\n        time.sleep(125)\n"
       "    post_payments(argv[2], out, totals)\n")
print("ok")
