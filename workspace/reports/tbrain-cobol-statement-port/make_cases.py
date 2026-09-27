"""Authoring step: write the verifier's input extracts (tests/cases/*.dat).

Expected statement files are not written here: the verifier image builds the
legacy program with GnuCOBOL and runs it on these extracts.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mkrec import cust, hdr  # noqa: E402

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
rng = random.Random(20250924)
SURNAMES = ["Okafor", "Lindgren", "Haddad", "Novak", "Fitzgerald", "Tanaka", "Moreau", "Sokolova",
            "Adeyemi", "Carvalho", "Mbatha", "Quinlan", "Reyes", "Horvath", "Byrne", "Nakamura"]
FIRST = ["Amara", "Lars", "Nadia", "Petr", "Siobhan", "Hiro", "Claude", "Irina", "Tunde", "Ines"]
FIRMS = ["BAKERY", "COLD STORE", "LAUNDRY", "BREWERY", "SCHOOL", "LEISURE CENTRE", "DAIRY", "HOTEL"]


def acct():
    return f"{rng.randint(10000000, 99999999)}"


def person():
    return f"{rng.choice(FIRST)} {rng.choice(SURNAMES)}"


def ordinary(n):
    rows = []
    for _ in range(n):
        t = rng.choice("DDDDDLLCC")
        prev = rng.randint(0, 990000)
        use = rng.randint(0, 260) if t != "C" else rng.randint(200, 9000)
        days = rng.choice([88, 89, 90, 91, 92, 93])
        arrears = rng.choice([0, 0, 0, rng.randint(1, 30000), -rng.randint(1, 8000)])
        paid = rng.choice([0, 0, rng.randint(1000, 40000)])
        name = person() if t != "C" else f"{rng.choice(SURNAMES).upper()} {rng.choice(FIRMS)}"
        rows.append(cust(acct(), name, t, prev, prev + use, days, arrears, paid))
    return rows


PAYMENTS = {}


def write(name, rows, payments=None):
    with open(os.path.join(OUT, name + ".dat"), "w") as fh:
        fh.write("".join(r + "\n" for r in rows))
    if payments is None:
        accts = [r[1:9] for r in rows if r.startswith("C")]
        payments = [f"{a};PAY;{rng.randint(1, 30000) / 100:.2f};counter" for a in accts[:4]]
    with open(os.path.join(OUT, name + ".pay"), "w") as fh:
        fh.write("".join(p + "\n" for p in payments))


write("district_run", [hdr(20250630, "ESTUARY & HILLS")] + ordinary(40))

write("rejected_records", [hdr(20250630, "WEST")] + [
    cust("40000001", "Lower Case Tariff", "d", 100, 180, 90, 0, 0),
    cust("40000002", "Unknown Tariff", "X", 100, 180, 90, 0, 0),
    cust("40000003", "Blank Tariff", " ", 100, 180, 90, 0, 0),
    cust("40000004", "No Days", "D", 100, 180, 0, 0, 0),
    cust("40000005", "Both Wrong", "Z", 100, 180, 0, 0, 0),
    cust("40000006", "Exactly Four Months", "D", 100, 180, 120, 0, 0),
    cust("40000007", "Just Over", "C", 100, 180, 121, 0, 0),
    cust("40000008", "Year Long", "L", 100, 180, 365, 0, 0),
    cust("40000009", "One Day", "C", 100, 101, 1, 0, 0),
    cust("40000010", "Relief Zero Days Wrong", "L", 100, 180, 999, 0, 0),
])

write("meter_rollover", [hdr(20250630, "SOUTH")] + [
    cust("50000001", "Rollover Small", "D", 999950, 120, 92, 0, 0),
    cust("50000002", "Rollover One Unit", "D", 999999, 0, 90, 0, 0),
    cust("50000003", "Nearly Full Turn", "C", 1, 400001, 91, 0, 0),
    cust("50000004", "Rollover Relief", "L", 999800, 15, 90, 2500, 1000),
    cust("50000005", "Equal Readings", "D", 424242, 424242, 90, 0, 0),
    cust("50000006", "Rollover Commercial", "C", 998000, 44000, 90, 0, 0),
])

credit = [hdr(20250630, "CENTRAL")]
for arrears, paid in [(-1, 0), (-39, 0), (-4210, 0), (-120000, 0), (0, 5000000), (-1000000, 9999999),
                      (-9999999, 9999999), (-9999999, 0), (-5000000, 5400000), (-2, 1), (-200, 1)]:
    credit.append(cust(acct(), person(), rng.choice("DLC"), 5000, 5000 + rng.randint(0, 40), 90, arrears, paid))
write("credit_balances", credit)

large = [hdr(20250630, "INDUSTRIAL ESTATE")]
for use in [60300, 60000, 61000, 63500, 120000, 350000, 404000, 440000, 500000, 70300, 58000]:
    prev = rng.randint(0, 300000)
    large.append(cust(acct(), f"{rng.choice(SURNAMES).upper()} {rng.choice(FIRMS)}", "C", prev,
                      (prev + use) % 1000000, rng.choice([90, 91, 60, 120]), rng.choice([0, 9999999, 350000]),
                      rng.choice([0, 0, 9999999])))
write("large_commercial_accounts", large)

names = ["  smith", " x", "", "   ", "jane  o'hara", "A  B", "abcdefghijklmnopqrstuvwx", "ABCDEFGHIJKLMNOPQRSTUVW ",
         "de la cruz  junior", "O'BRIEN-SMYTHE & CO. (2)", "q", "trailing space ", "mIxEd CaSe NaMe",
         "x                      y"]
write("names_of_every_shape", [hdr(20250630, "NAMES")] + [
    cust(f"6000{i:04d}", nm, "D", 1000, 1080, 90, 0, 0) for i, nm in enumerate(names)])

rounding = [hdr(20250630, "ROUNDING")]
for arrears in [1, 3, 33, 100, 300, 500, 700, 1100, 2300, 99999, 12345, 101]:
    rounding.append(cust(acct(), person(), "D", 0, rng.randint(1, 60), 90, arrears, 0))
for days in [1, 2, 4, 5, 7, 8, 11, 13, 14, 16, 17, 29, 31, 43, 59, 61, 89, 118, 119]:
    rounding.append(cust(acct(), person(), rng.choice("DLC"), 700, 700 + rng.randint(0, 400), days, 0, 0))
for use in [1, 3, 7, 13, 17, 23, 29, 31, 47, 53, 67, 71, 101, 137]:
    rounding.append(cust(acct(), person(), "L", 100, 100 + use, 90, 0, 0))
write("rounding_boundaries", rounding)

bands = [hdr(20250630, "BANDS")]
for t, days, use in [("D", 90, 30), ("D", 90, 31), ("D", 90, 90), ("D", 90, 91), ("D", 30, 10), ("D", 30, 11),
                     ("C", 90, 150), ("C", 90, 151), ("C", 90, 600), ("C", 90, 601), ("C", 60, 400),
                     ("L", 45, 15), ("L", 45, 45), ("L", 45, 46), ("D", 29, 10), ("D", 31, 10), ("C", 91, 152)]:
    bands.append(cust(acct(), person(), t, 2000, 2000 + use, days, 0, 0))
write("band_boundaries", bands)

write("zero_amounts", [hdr(20250630, "ZEROES")] + [
    cust("70000001", "No Use No Arrears", "D", 500, 500, 90, 0, 0),
    cust("70000002", "Paid Exactly", "C", 500, 500, 30, 0, 3106),
    cust("70000003", "Tiny", "D", 0, 0, 1, 0, 0),
    cust("70000004", "Relief No Use", "L", 9, 9, 90, 0, 0),
    cust("70000005", "Credit Of One Cent", "D", 0, 0, 1, 0, 34),
    cust("70000006", "Arrears Paid Off", "D", 10, 12, 90, 5000, 5000),
    cust("70000007", "Minus Nought Arrears", "D", 10, 40, 90, 0, 0, negative_zero=True),
    cust("70000008", "Minus Nought Credit", "C", 10, 10, 30, 0, 3106, negative_zero=True),
])

short = [hdr(20250630, "SHORT LINES").rstrip(" ")]
for row in ordinary(8):
    short.append(row.rstrip(" "))
short.append(cust("80000001", "Name With Trailing Blanks  ", "D", 10, 20, 90, 0, 0)[:64])
write("short_lines", short)

write("header_missing", ordinary(5))
write("header_out_of_place", ordinary(3) + [hdr(20250630, "LATE HEADER")] + ordinary(3))
write("two_headers", [hdr(20250630, "FIRST"), hdr(20250701, "SECOND")] + ordinary(4))
write("header_only", [hdr(20251231, "EMPTY QUARTER")])
write("empty_file", [])
write("date_and_region", [hdr(19991231, "a lower case region!"), hdr(20000101, "X")] + ordinary(2))
write("long_run", [hdr(20250930, "ALL DISTRICTS")] + ordinary(300))
# --- payments side ---------------------------------------------------------------
base = [hdr(20250630, "POSTINGS")] + [
    cust("91000001", "Ada Byrne", "D", 100, 190, 90, 0, 0),
    cust("91000002", "Bram Novak", "L", 100, 160, 90, 1500, 0),
    cust("91000003", "CORRIGAN BREWERY", "C", 1000, 4200, 91, 0, 0),
    cust("91000004", "Dina Haddad", "D", 100, 100, 90, -2500, 0),
    cust("91000002", "Duplicate Of Bram", "D", 100, 400, 90, 0, 0),
    cust("91000005", "Rejected Tariff", "X", 100, 190, 90, 0, 0),
]

write("postings_ordinary", base, [
    "91000001;PAY;120.00;counter cash", "91000003;PAY;2500.00;bank transfer", "91000004;ADJ;-15.50;goodwill",
    "91000002;FEE;25.00;late fee", "91000003;REF;40.00;overpayment", "91000001;PAY;0.01;rounding"])

write("postings_with_fewer_fields", base, [
    "91000001;PAY;10.00;first memo #12345", "91000003;PAY;20.00", "91000004;ADJ;3.00;",
    "91000002;FEE;9.99", "99999999;PAY;1.00;rejected memo 777 #888", "91000001;REF;5.00",
    "91000003;PAY", "91000003", "", "91000001;ADJ;1.00;last"])

write("postings_rounding_modes", base, [
    "91000001;PAY;12.345;pay half up", "91000001;PAY;12.335;pay half even", "91000001;PAY;-2.675;pay neg",
    "91000003;ADJ;12.345;adj", "91000003;ADJ;-12.345;adj neg", "91000003;ADJ;-0.004;adj tiny",
    "91000002;FEE;10.009;fee truncates", "91000002;FEE;-10.01;fee negative", "91000002;FEE;0.02;fee small",
    "91000004;REF;7.125;ref", "91000004;REF;-7.121;ref neg", "91000004;REF;-0.001;ref tiny neg",
    "91000001;ADJ;-0.50;half dollar", "91000001;PAY;-1.00;negative payment",
    "91000001;PAY;12.3450001;just over half", "91000001;PAY;0.0050000001;tiny over half",
    "91000001;PAY;-2.6750000001;negative over half", "91000001;PAY;7.1249999999;just under half",
    "91000001;PAY;-0;minus nought", "91000001;PAY;-0.004;rounds to nought",
    "91000002;FEE;20.00;split rounds up", "91000002;FEE;-20.00;split negative", "91000002;FEE;0.05;split tiny",
    "91000002;FEE;10.01;split", "91000002;FEE;100.00;split hundred", "91000002;FEE;99999.99;split largest",
    "91000002;FEE;0.04;split four cents"])

write("postings_amount_forms", base, [
    "91000001;PAY;5-;trailing minus", "91000001;PAY;5 CR;credit", "91000001;PAY;7.5 DB;debit",
    "91000001;ADJ;- 3;spaced sign", "91000001;ADJ;+ 7.25;plus", "91000001;ADJ;.5;point five",
    "91000001;ADJ;5.;five point", "91000001;ADJ;0000000000012.345;long amount", "91000001;ADJ; 3.999 ;spaces",
    "91000001;PAY;1,000.00;comma", "91000001;PAY;$5;dollar", "91000001;PAY;12a;letter", "91000001;PAY;;empty",
    "91000001;PAY;1.2.3;two points", "91000001;PAY;12 .5;inner space", "91000001;PAY;-5-;two signs",
    "91000001;PAY;5 cr;lower cr", "91000001;PAY;   ;blank"])

write("postings_kinds_and_accounts", base, [
    "91000003;PAYMENT;10.00;long kind", "91000003;pay;10.00;lower kind", "91000003;RE;10.00;short kind",
    "91000003;XYZ;10.00;unknown kind", "91000002;PAY;30.00;duplicate account", "91000005;PAY;30.00;rejected acct",
    "9100000;PAY;1.00;seven digits", "910000031;PAY;1.00;nine digits", "91000003 ;PAY;1.00;trailing space",
    " 9100003;PAY;1.00;leading space", "91000006;PAY;1.00;unknown", "91000003;FEE;12.345;fee kind",
    "bad line without separators", ";;;", "91000001;ADJ;abc;bad amount before kind check"])

write("postings_memos", base, [
    "91000001;PAY;1.00;no hash 12345", "91000001;PAY;1.00;card #4929123412341234",
    "91000001;PAY;1.00;##99", "91000001;PAY;1.00;#", "91000001;PAY;1.00;cheque 889 #2 ref 77",
    "91000001;PAY;1.00;a;b;c", "91000001;PAY;1.00;" + "x" * 40, "91000001;PAY;1.00;12#34#56",
    "91000001;PAY;1.00;memo with trailing spaces   ", "91000001;PAY;1.00;extra;fields;here;and;more"])

write("postings_empty", base, [])
print("written", len(os.listdir(OUT)))
