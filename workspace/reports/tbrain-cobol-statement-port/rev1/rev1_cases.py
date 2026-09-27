"""Authoring step for rev1: extend the verifier's input extracts in tests/cases.

Run after make_cases.py's output is in place (the returned fixtures). Adds the
witnesses the quality panel asked for and a seeded set of generated extract pairs
drawn from the whole input contract in RUNBOOK.md. Expected statements are still
produced by the job step itself when the verifier image is built.

Usage: python3 rev1_cases.py <task>/tests/cases
"""

import os
import random
import string
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mkrec import cust, hdr  # noqa: E402

OUT = sys.argv[1]
PRINTABLE = string.printable[:95]  # space .. ~, no tabs or line ends


def write(name, rows, payments):
    for suffix, lines in ((".dat", rows), (".pay", payments)):
        for line in lines:
            assert len(line) <= 80 and all(c in PRINTABLE for c in line), (name, line)
        with open(os.path.join(OUT, name + suffix), "w") as fh:
            fh.write("".join(line + "\n" for line in lines))


def append(name, suffix, lines):
    for line in lines:
        assert len(line) <= 80 and all(c in PRINTABLE for c in line), (name, line)
    with open(os.path.join(OUT, name + suffix), "a") as fh:
        fh.write("".join(line + "\n" for line in lines))


def rewrite(name, suffix, edit):
    path = os.path.join(OUT, name + suffix)
    with open(path) as fh:
        lines = fh.read().split("\n")[:-1]
    lines = edit(lines)
    for line in lines:
        assert len(line) <= 80 and all(c in PRINTABLE for c in line), (name, line)
    with open(path, "w") as fh:
        fh.write("".join(line + "\n" for line in lines))


# --- panel findings ---------------------------------------------------------------

# 1: records whose type is neither H nor C are passed over, wherever they sit
write("other_record_types", [
    hdr(20250630, "OTHER RECORD TYPES"),
    cust("93000001", "Ada Byrne", "D", 100, 190, 90, 0, 0),
    "X" + cust("93000002", "Changed Type Byte", "D", 100, 190, 90, 0, 0)[1:],
    "c" + cust("93000003", "Lower Case Type", "C", 100, 4000, 90, 0, 0)[1:],
    " " + cust("93000004", "Blank Type", "L", 100, 160, 90, 0, 0)[1:],
    cust("93000005", "Bram Novak", "L", 100, 160, 90, 1500, 0),
    "h" + hdr(20250701, "LOWER CASE HEADER")[1:],
    "D" + cust("93000006", "Tariff Letter As Type", "D", 100, 190, 90, 0, 0)[1:],
    "9" + cust("93000007", "Digit Type", "D", 100, 190, 90, 0, 0)[1:],
    "TRAILER 000004 RECORDS",
    "*",
    cust("93000008", "CORRIGAN BREWERY", "C", 1000, 4200, 91, 0, 0),
], [
    "93000001;PAY;10.00;billed", "93000002;PAY;10.00;skipped record", "93000003;ADJ;1.00;skipped record",
    "93000005;FEE;3.00;billed", "93000008;REF;2.00;billed", "93000007;PAY;1.00;skipped record",
])

# 3: a header that stops at STMT-DATE, and one that stops part way into the region
write("short_header", [
    "H20250630",
    cust("94000001", "Ada Byrne", "D", 100, 190, 90, 0, 0).rstrip(" "),
    cust("94000002", "CORRIGAN BREWERY", "C", 1000, 4200, 91, 0, 0)[:64],
], [])
write("header_date_and_part_region", [
    "H20251231NO",
    cust("94000011", "Dina Haddad", "D", 100, 100, 90, -2500, 0)[:64],
], ["94000011;PAY;1.00;x"])

# 4: commercial usage well past 500,000 units, current charges still under 1,000,000.00
append("large_commercial_accounts", ".dat", [
    cust("95000001", "HALF MILLION AND ONE", "C", 0, 500001, 90, 0, 0),
    cust("95000002", "ROLLOVER PAST HALF", "C", 600000, 100001, 90, 0, 0),
    cust("95000003", "COLD STORE NORTH", "C", 12345, 562345, 120, 350000, 0),
    cust("95000004", "SHORT PERIOD PLANT", "C", 0, 555555, 30, 0, 9999999),
    cust("95000005", "LARGEST QUARTER", "C", 400000, 972000, 91, -9999999, 0),
])

# 5: empty readings lines, between accounts and before the first one
rewrite("short_lines", ".dat", lambda lines: lines[:1] + [""] + lines[1:4] + ["", ""] + lines[4:] + [""])
write("blank_line_first", ["", hdr(20250630, "LATE AFTER BLANK"),
                           cust("96000001", "Ada Byrne", "D", 100, 190, 90, 0, 0)], ["96000001;PAY;1.00;x"])

# 2: a sign followed by a leading decimal point, on every posting kind
append("postings_amount_forms", ".pay", [
    "91000001;PAY;-.5;signed leading point", "91000001;PAY;+.25;plus leading point",
    "91000001;PAY;- .75;spaced sign point", "91000003;ADJ;-.005;adj half cent", "91000003;ADJ;+ .125;adj",
    "91000002;FEE;-.5;fee split", "91000002;FEE;+.07;fee plus", "91000004;REF;-.125;ref neg",
    "91000004;REF;+.999;ref plus", "91000001;PAY;.5-;trailing minus point", "91000001;PAY;.25 CR;point cr",
    "91000001;PAY;.75 DB;point db", "91000001;PAY;-.;sign point only", "91000001;PAY;+.x;sign point letter",
    "91000001;PAY;.;point only", "91000001;PAY;-.5 CR;sign both ends", "91000001;PAY;  -  .5  ;spaced",
])

# 6: payments lines at and just under the 80-byte limit
append("postings_memos", ".pay", [
    "91000001;PAY;1.00;" + "M" * 62,
    "91000001;PAY;1.00;" + ("memo number 30 chars here ... #" + "1234567890" * 4)[:62],
    "91000003;FEE;12.34;" + "long memo with #9 and more text past the thirtieth char 12345"[:61],
    "91000002;ADJ;-3.5;" + ("x" * 29) + "#" + ("7" * 32),
    "91000004;REF;0000000000012.345;" + "y" * 48,
    "91000001;PAY;1.00;" + "z" * 61,
])
for line in open(os.path.join(OUT, "postings_memos.pay")).read().split("\n")[-7:-1]:
    assert len(line) >= 79, (len(line), line)

# --- generated extract pairs --------------------------------------------------------
# Drawn from the input contract in RUNBOOK.md: record types other than H and C, empty
# and short lines, every tariff and rejection, rollover, usage up to the per-account
# charge limit, signed arrears, names of any printable text, and payments lines up to
# 80 bytes with every field count, account shape, kind and amount grammar.
rng = random.Random(20250925)
USAGE_CAP = {"D": 380000, "L": 380000, "C": 570000}


def printable(n, pool=PRINTABLE):
    return "".join(rng.choice(pool) for _ in range(n))


def name():
    kind = rng.random()
    if kind < 0.4:
        return rng.choice(["Ada", "lars", "  nadia", "PETR", "Siobhan  O'Neill", "hiro", "Ines"]) + " " + \
            rng.choice(["Byrne", "novak", "HADDAD", "de la  cruz", "Mbatha-Reyes & Co.", ""])
    if kind < 0.6:
        return ""
    return printable(rng.randint(1, 24))


def usage_for(tariff):
    r = rng.random()
    cap = USAGE_CAP.get(tariff, 400000)
    if r < 0.6:
        return rng.randint(0, 400)
    if r < 0.85:
        return rng.randint(400, 20000)
    return rng.randint(20000, cap)


def customer(acct):
    tariff = rng.choice("DDDCCCLLL") if rng.random() < 0.9 else rng.choice("XdcZ 1*")
    days = rng.randint(1, 120) if rng.random() < 0.88 else rng.choice([0, 121, 365, 999])
    use = usage_for(tariff)
    prev = rng.randint(0, 999999)
    curr = (prev + use) % 1000000
    arrears = rng.choice([0, 0, rng.randint(1, 9999999), -rng.randint(1, 9999999), rng.randint(1, 999)])
    paid = rng.choice([0, 0, rng.randint(0, 9999999), rng.randint(0, 999)])
    rec = cust(acct, name(), tariff, prev, curr, days, arrears, paid, negative_zero=arrears == 0 and rng.random() < 0.1)
    tail = rng.random()
    if tail < 0.25:
        rec = rec[:rng.randint(64, 79)]
    elif tail < 0.35:
        rec = rec[:64] + printable(16)
    elif tail < 0.6:
        rec = rec.rstrip(" ")
    return rec


def header():
    date = f"{rng.randint(19000101, 20991231):08d}"
    region = printable(rng.randint(0, 20)) if rng.random() < 0.5 else rng.choice(["NORTH", "EAST RIDING", ""])
    rec = "H" + date + region
    if rng.random() < 0.3:
        rec = rec.ljust(80)
    return rec


def other_record(acct):
    r = rng.random()
    if r < 0.35:
        return ""
    if r < 0.7:
        return rng.choice("XhcDT9* ") + customer(acct)[1:]
    first = rng.choice(PRINTABLE.replace("C", "").replace("H", ""))
    return (first + printable(rng.randint(0, 79))).rstrip(" ") or "."


def amount_text(valid):
    whole = str(rng.choice([0, 1, 5, 12, 99, 250, 1000, 12345, 99998, rng.randint(0, 99998)]))
    frac = "".join(rng.choice(string.digits) for _ in range(rng.choice([0, 1, 2, 2, 3, 4, 7])))
    form = rng.random()
    if form < 0.25:
        body = whole + "." + frac
    elif form < 0.4:
        body = "." + (frac or "5")
    elif form < 0.5:
        body = whole + "."
    else:
        body = whole + ("." + frac if frac else "")
    sp = lambda: " " * rng.choice([0, 0, 0, 1, 2])  # noqa: E731
    if valid:
        if rng.random() < 0.5:
            text = sp() + rng.choice(["", "", "+", "-"]) + sp() + body + sp()
        else:
            text = sp() + body + sp() + rng.choice(["", "+", "-", "CR", "DB"]) + sp()
    else:
        text = rng.choice([
            body + "x", "$" + body, body.replace(".", ",") + ",0", "--" + body, body + " cr", body + " db",
            "+" + body + "-", "1e" + str(rng.randint(1, 5)), body + ".5.", " ", "", "+", "CR", body[:1] + " " + body,
            "12" + " " + "5", "- -" + body])
    return text[:16]


def payment_line(accounts):
    r = rng.random()
    acct = rng.choice(accounts) if accounts and r < 0.75 else rng.choice([
        f"{rng.randint(10000000, 99999999)}", "1234567", "123456789", " 1234567", "abcdefgh", ""])
    kind = rng.choice(["PAY", "PAY", "ADJ", "FEE", "REF"]) if rng.random() < 0.85 else rng.choice(
        ["pay", "PAYMENT", "RE", "XYZ", "", "FEES"])
    amt = amount_text(rng.random() < 0.85)
    memo = printable(rng.randint(0, 70)) if rng.random() < 0.7 else rng.choice(
        ["", "counter", "card #4929123412341234", "cheque 889 #2 ref 77", "a;b;c;d"])
    fields = [acct, kind, amt, memo]
    shape = rng.random()
    if shape < 0.1:
        fields = fields[:rng.randint(0, 3)]
    elif shape < 0.2:
        fields = fields + [printable(rng.randint(0, 10))]
    line = ";".join(fields)
    if rng.random() < 0.1:
        line = printable(rng.randint(0, 80))
    return line[:80]


def generated(number):
    accounts = [f"{rng.randint(10000000, 99999999)}" for _ in range(rng.randint(1, 45))]
    if rng.random() < 0.3 and len(accounts) > 2:
        accounts[1] = accounts[0]  # a repeated account
    rows = []
    start = rng.random()
    if start < 0.75:
        rows.append(header())
    elif start < 0.85:
        rows.append("")
        rows.append(header())
    for acct in accounts:
        if rng.random() < 0.15:
            rows.append(other_record(acct))
        rows.append(customer(acct))
    if rng.random() < 0.15:
        rows.insert(rng.randint(0, len(rows)), header())
    payments = [payment_line(accounts) for _ in range(rng.randint(0, 40))]
    write(f"generated_{number:02d}", rows, payments)


for number in range(1, 25):
    generated(number)
print("cases:", len(os.listdir(OUT)) // 2)
