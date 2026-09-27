"""Authoring step for rev2: grow long_run to the 500-record bound on both sides.

The instruction now bounds each input at 500 records. long_run keeps its first
302 reading records (header + 301 accounts) and gains 198 more accounts, so the
extract holds exactly 500 records; its payments export becomes 500 postings
spread over the whole account table, ending on the last account, so a port that
caps either file at any smaller size writes different bytes. Expected statements
are still produced by the job step itself when the verifier image is built.

Usage: python3 rev2_cases.py <task>/tests/cases
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mkrec import cust  # noqa: E402

OUT = sys.argv[1]
rng = random.Random(20250925)
SURNAMES = ["Okafor", "Lindgren", "Haddad", "Novak", "Fitzgerald", "Tanaka", "Moreau", "Sokolova",
            "Adeyemi", "Carvalho", "Mbatha", "Quinlan", "Reyes", "Horvath", "Byrne", "Nakamura"]
FIRST = ["Amara", "Lars", "Nadia", "Petr", "Siobhan", "Hiro", "Claude", "Irina", "Tunde", "Ines"]
FIRMS = ["BAKERY", "COLD STORE", "LAUNDRY", "BREWERY", "SCHOOL", "LEISURE CENTRE", "DAIRY", "HOTEL"]
LIMIT = 500

path = os.path.join(OUT, "long_run.dat")
rows = open(path).read().split("\n")[:-1]
assert len(rows) == 302 and rows[0].startswith("H"), len(rows)
seen = {r[1:9] for r in rows[1:]}
while len(rows) < LIMIT:
    acct = f"{rng.randint(10000000, 99999999)}"
    if acct in seen:
        continue
    seen.add(acct)
    t = rng.choice("DDDDDLLCC")
    prev = rng.randint(0, 990000)
    use = rng.randint(0, 260) if t != "C" else rng.randint(200, 9000)
    arrears = rng.choice([0, 0, 0, rng.randint(1, 30000), -rng.randint(1, 8000)])
    paid = rng.choice([0, 0, rng.randint(1000, 40000)])
    name = f"{rng.choice(FIRST)} {rng.choice(SURNAMES)}" if t != "C" else \
        f"{rng.choice(SURNAMES).upper()} {rng.choice(FIRMS)}"
    rows.append(cust(acct, name, t, prev, prev + use, rng.choice([88, 89, 90, 91, 92, 93]), arrears, paid))
assert len(rows) == LIMIT
with open(path, "w") as fh:
    fh.write("".join(r + "\n" for r in rows))

accts = [r[1:9] for r in rows[1:]]
postings = []
for i in range(LIMIT - 1):
    roll = rng.random()
    if roll < 0.03:
        acct = f"{rng.randint(10000000, 99999999)}"  # almost surely unknown
    elif roll < 0.10:
        acct = accts[rng.randrange(len(accts))]
    else:
        acct = accts[i % len(accts)]
    kind = rng.choice(["PAY"] * 6 + ["ADJ", "FEE", "REF"])
    cents = rng.randint(1, 30000)
    amount = f"{cents / 100:.2f}" if kind != "ADJ" or rng.random() < 0.5 else f"-{cents / 100:.2f}"
    postings.append(f"{acct};{kind};{amount};run {i + 1:03d}")
postings.append(f"{accts[-1]};PAY;1.00;last posting of the run")
assert len(postings) == LIMIT and all(len(p) <= 80 for p in postings)
with open(os.path.join(OUT, "long_run.pay"), "w") as fh:
    fh.write("".join(p + "\n" for p in postings))
print("long_run:", len(rows), "records,", len(postings), "postings")
