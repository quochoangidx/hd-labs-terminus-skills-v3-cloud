"""Authoring step for rev3: account identifiers that are not all digits.

ACCT-NO is PIC X(8) and the run notes restrict only numeric fields to digits, so
a customer may carry any eight printable characters as its account. This case
posts to such accounts successfully, repeats one, misses one by letter case, and
refuses a seven-character one, so a port that only indexes digit-only accounts,
normalises case, or trims spaces writes different bytes. Expected statements are
still produced by the job step itself when the verifier image is built.

Usage: python3 rev3_cases.py <task>/tests/cases
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mkrec import cust, hdr  # noqa: E402

OUT = sys.argv[1]
NAME = "postings_account_identifiers"
rows = [hdr(20250630, "ACCOUNT IDS"),
        cust("ABCDEFGH", "Ada Letters", "D", 0, 0, 90, 0, 0),
        cust("AB-12/7Z", "PUNCTUATED DAIRY", "C", 1000, 4200, 91, 0, 0),
        cust("1234567A", "Trailing Letter", "L", 100, 160, 90, 1500, 0),
        cust("A 1 B 2 ", "Spaced Id", "D", 100, 190, 90, 0, 0),
        cust(" 7654321", "Leading Space", "D", 100, 130, 90, -2500, 0),
        cust("91000001", "Digits Only", "D", 100, 190, 90, 0, 0)]
payments = ["ABCDEFGH;PAY;1.00;x",
            "abcdefgh;PAY;1.00;lower case",
            "AB-12/7Z;ADJ;-3.00;punctuated",
            "1234567A;FEE;5.00;letter at end",
            "A 1 B 2 ;REF;2.50;spaces inside",
            " 7654321;PAY;4.00;leading space",
            "ABCDEFGH;PAY;2.00;second posting",
            "ABCDEFG;PAY;1.00;seven characters",
            "91000001;PAY;3.00;digits only"]
for suffix, lines in ((".dat", rows), (".pay", payments)):
    assert all(len(x) <= 80 and all(" " <= c <= "~" for c in x) for x in lines)
    with open(os.path.join(OUT, NAME + suffix), "w") as fh:
        fh.write("".join(x + "\n" for x in lines))
print(NAME, len(rows), "records,", len(payments), "postings")
