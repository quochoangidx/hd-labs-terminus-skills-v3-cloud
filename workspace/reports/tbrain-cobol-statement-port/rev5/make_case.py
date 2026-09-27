"""rev5 authoring step: write tests/cases/long_run_no_header.{dat,pay}.

A full-capacity readings extract with no header: the 499 customer records of
long_run.dat followed by one more, so all 500 records are C records, and a
500-line payments export with one posting to each account, the last account included.
Usage: python3 make_case.py <tests/cases dir>
"""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mkrec import cust  # noqa: E402

cases = sys.argv[1]
rng = random.Random(20250926)
with open(os.path.join(cases, "long_run.dat")) as fh:
    rows = [line.rstrip("\n") for line in fh if line.startswith("C")]
assert len(rows) == 499
accounts = {r[1:9] for r in rows}
last = "40050000"
assert last not in accounts
rows.append(cust(last, "Last Of The Run", "D", 4100, 4288, 90, 1250, 0))
kinds = ["PAY"] * 7 + ["ADJ", "FEE", "REF"]
postings = []
for n, r in enumerate(rows, start=1):
    kind = rng.choice(kinds)
    amount = f"{rng.randint(1, 45000) / 100:.2f}"
    if kind == "ADJ" and rng.random() < 0.5:
        amount = "-" + amount
    postings.append(f"{r[1:9]};{kind};{amount};run {n:03d}")
with open(os.path.join(cases, "long_run_no_header.dat"), "w") as fh:
    fh.write("".join(r + "\n" for r in rows))
with open(os.path.join(cases, "long_run_no_header.pay"), "w") as fh:
    fh.write("".join(p + "\n" for p in postings))
print(len(rows), len(postings))
