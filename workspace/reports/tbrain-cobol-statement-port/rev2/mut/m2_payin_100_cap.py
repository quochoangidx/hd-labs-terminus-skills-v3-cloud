"""Python port of the WBILL quarterly water statement run.

Usage: python3 wbill.py READINGS PAYMENTS OUTPUT

Reproduces the statement file the COBOL program writes: fixed-point decimal
arithmetic with COBOL ROUNDED (half away from zero) and truncation, numeric
edited pictures, STRING ... DELIMITED BY semantics, and GnuCOBOL line
sequential output (trailing spaces removed, one newline per record).
"""

import sys
import re
from decimal import ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

TARIFFS = [
    # code, limit1, limit2, rate1, rate2, rate3, standing
    ("D", 10, 30, "1.2050", "1.8575", "2.4410", "0.3125"),
    ("C", 50, 200, "1.1500", "1.4025", "1.6550", "0.9860"),
    ("L", 10, 30, "1.2050", "1.8575", "2.4410", "0.3125"),
]

CENT = Decimal("0.01")
TENTH = Decimal("0.1")


def rounded(value, quantum):
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def truncated(value, quantum):
    return value.quantize(quantum, rounding=ROUND_DOWN)


def edit(value, pic, blank_when_zero=False):
    """Move a numeric value into a numeric-edited picture (no repeat counts)."""
    value = Decimal(value)
    if blank_when_zero and value == 0:
        return " " * len(pic)
    negative = value < 0
    suffix = ""
    if pic.endswith("CR"):
        suffix, pic = ("CR" if negative else "  "), pic[:-2]
    elif pic.endswith("-") and pic[0] != "-":
        suffix, pic = ("-" if negative else " "), pic[:-1]
    prefix = ""
    if pic[0] in "+-" and pic.count(pic[0]) == 1:
        prefix = ("-" if negative else ("+" if pic[0] == "+" else " "))
        pic = pic[1:]
    floating = pic[0] if pic[0] in "$+-" and pic.count(pic[0]) > 1 else None
    int_part, _, dec_part = pic.partition(".")

    def positions(part, first_is_symbol):
        count, seen = 0, False
        for ch in part:
            if ch in "9Z*":
                count += 1
            elif floating and ch == floating:
                if first_is_symbol and not seen:
                    seen = True
                else:
                    count += 1
        return count

    n_int = positions(int_part, True)
    n_dec = positions(dec_part, False)
    magnitude = truncated(abs(value), Decimal(1).scaleb(-n_dec))
    digits = f"{magnitude:.{n_dec}f}".replace(".", "")
    int_digits = digits[: len(digits) - n_dec] if n_dec else digits
    # The legacy runtime lines the value up with the currency position counted as a
    # digit position too; when a non-zero digit lands there, the sign prints in that
    # position and no zero after it is suppressed.
    padded = int_digits.rjust(n_int + 1, "0")
    overflow = bool(floating) and padded[-(n_int + 1)] != "0"
    int_digits = int_digits[-n_int:].rjust(n_int, "0") if n_int else ""
    dec_digits = digits[len(digits) - n_dec:] if n_dec else ""
    stream = iter(int_digits + dec_digits)

    out = []
    suppressing = not overflow
    fill = "*" if "*" in pic else " "
    last_suppressed = None
    seen_symbol = False
    for ch in pic:
        if ch == ".":
            suppressing = False
            out.append(".")
        elif ch == ",":
            if suppressing:
                out.append(fill)
                if floating:
                    last_suppressed = len(out) - 1
            else:
                out.append(",")
        elif ch in "Z*":
            d = next(stream)
            if suppressing and d == "0":
                out.append(fill)
            else:
                suppressing = False
                out.append(d)
        elif floating and ch == floating:
            if not seen_symbol:
                seen_symbol = True
                out.append(" ")
                last_suppressed = len(out) - 1
                continue
            d = next(stream)
            if suppressing and d == "0":
                out.append(" ")
                last_suppressed = len(out) - 1
            else:
                suppressing = False
                out.append(d)
        elif ch == "9":
            suppressing = False
            out.append(next(stream))
        elif ch == "/":
            out.append("/")
        else:
            out.append(ch)
    if floating:
        symbol = {"$": "$", "+": "-" if negative else "+", "-": "-" if negative else " "}[floating]
        out[last_suppressed] = symbol
    return prefix + "".join(out) + suffix


def string_delimited(text, delimiter):
    index = text.find(delimiter)
    return text if index < 0 else text[:index]


class Totals:
    def __init__(self):
        self.table = []
        self.billed = self.rejected = self.credits = 0
        self.units = 0
        self.current = Decimal(0)
        self.due = Decimal(0)
        self.net = Decimal(0)


def signed_field(text):
    sign, body = text[0], text[1:]
    value = Decimal(int(body)) / 100
    return -value if sign == "-" else value


def one_account(rec, out, totals):
    acct, name, tariff = rec[1:9], rec[9:33], rec[33]
    prev, curr, days = int(rec[34:40]), int(rec[40:46]), int(rec[46:49])
    arrears = signed_field(rec[49:57])
    paid = Decimal(int(rec[57:64])) / 100
    row = next((t for t in TARIFFS if t[0] == tariff), None)
    reason = ""
    if row is None:
        reason = "UNKNOWN TARIFF"
    elif days == 0:
        reason = "NO BILLING DAYS"
    elif days > 120:
        reason = "PERIOD TOO LONG"
    if reason:
        totals.rejected += 1
        out.append(("REJECT " + acct + " " + reason.ljust(20))[:72])
        out.append("")
        return
    _, limit1, limit2, rate1, rate2, rate3, standing = row
    units = curr - prev if curr >= prev else curr + 1000000 - prev
    lim1 = rounded(Decimal(limit1 * days) / 30, TENTH)
    lim2 = rounded(Decimal(limit2 * days) / 30, TENTH)
    b1 = b2 = b3 = Decimal(0)
    if units > lim1:
        b1 = lim1
        if units > lim2:
            b2 = lim2 - lim1
            b3 = units - lim2
        else:
            b2 = units - lim1
    else:
        b1 = Decimal(units)
    c1 = rounded(b1 * Decimal(rate1), CENT)
    c2 = rounded(b2 * Decimal(rate2), CENT)
    c3 = rounded(b3 * Decimal(rate3), CENT)
    usage = c1 + c2 + c3
    stand = rounded(days * Decimal(standing), CENT)
    discount = Decimal(0)
    if tariff == "L":
        discount = truncated(usage * Decimal("0.15"), CENT)
        usage -= discount
    net = usage + stand
    vat = rounded(net * Decimal("0.05"), CENT)
    current = net + vat
    interest = rounded(arrears * Decimal("0.015"), CENT) if arrears > 0 else Decimal(0)
    balance = current + arrears + interest - paid
    due = balance if balance > 0 else Decimal(0)
    carry = Decimal(0)
    if balance < 0:
        carry = rounded(balance * Decimal("0.975"), CENT)
        totals.credits += 1
    totals.billed += 1
    totals.table.append([acct, balance])
    totals.units += units
    totals.current += current
    totals.due += due
    totals.net += balance

    shown = string_delimited(name.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz",
                                                          "ABCDEFGHIJKLMNOPQRSTUVWXYZ")), "  ")
    if shown.strip() == "":
        shown = "(NO NAME ON FILE)"
    out.append("ACCOUNT ****" + acct[4:8] + "  " + shown.ljust(24)[:24] + " TARIFF " + tariff)
    out.append("READINGS " + edit(prev, "ZZZZZ9") + " TO " + edit(curr, "ZZZZZ9") + "  USAGE "
               + edit(units, "Z,ZZZ,ZZ9") + " OVER " + edit(days, "ZZ9") + " DAYS")
    out.append("BANDS " + edit(b1, "ZZ,ZZ9.9") + " " + edit(b2, "ZZ,ZZ9.9") + " " + edit(b3, "Z,ZZZ,ZZ9.9"))
    out.append("USAGE CHARGE " + edit(usage, "$$,$$$,$$9.99") + "  STANDING" + edit(stand, "$$$,$$9.99"))
    out.append("DISCOUNT " + edit(discount, "ZZ,ZZ9.99", True) + "  VAT" + edit(vat, "ZZZ,ZZ9.99")
               + "  CURRENT" + edit(current, "$$$,$$9.99"))
    out.append("ARREARS " + edit(arrears, "++,+++,++9.99") + "  INTEREST"
               + edit(interest, "ZZ,ZZ9.99", True) + "  PAID" + edit(paid, "ZZ,ZZ9.99"))
    out.append("BALANCE " + edit(balance, "Z,ZZZ,ZZ9.99CR") + "  AMOUNT DUE" + edit(due, "***,**9.99"))
    if balance < 0:
        out.append("CREDIT C/F " + edit(carry, "$$$,$$9.99-"))
    out.append("")


NUMVAL = re.compile(
    r"^ *(?:([+-]) *)?(\d+\.?\d*|\.\d+) *$|^ *(\d+\.?\d*|\.\d+) *(\+|-|CR|DB)? *$")


def numval(text):
    """FUNCTION NUMVAL, or None where FUNCTION TEST-NUMVAL reports an error."""
    m = NUMVAL.match(text)
    if not m:
        return None
    if m.group(2) is not None:
        value = Decimal(m.group(2) if not m.group(2).endswith(".") else m.group(2)[:-1] or "0")
        return -value if m.group(1) == "-" else value
    body = m.group(3)
    value = Decimal(body[:-1] or "0") if body.endswith(".") else Decimal(body)
    return -value if m.group(4) in ("-", "CR", "DB") else value


def unstring(line, fields):
    """UNSTRING line DELIMITED BY ";" INTO the receiving fields.

    ``fields`` holds (current value, width) pairs and is updated in place only for
    the fields that receive data, as the verb does. Returns (tally, first count)."""
    pointer, tally, first_count = 0, 0, 0
    for index, (_, width) in enumerate(fields):
        if pointer >= len(line):
            break
        end = line.find(";", pointer)
        piece = line[pointer:] if end < 0 else line[pointer:end]
        fields[index] = (piece[:width].ljust(width), width)
        if index == 0:
            first_count = len(piece)
        tally += 1
        pointer = len(line) if end < 0 else end + 1
    return tally, first_count


def post_payments(path, out, totals):
    out.append("")
    out.append("PAYMENTS AND ADJUSTMENTS")
    fields = [(" " * 8, 8), (" " * 3, 3), (" " * 16, 16), (" " * 30, 30)]
    line_no = applied = rejected = 0
    paid = other = Decimal(0)
    with open(path, "r", encoding="latin-1", newline="\n") as fh:
        lines = [line.rstrip("\n").ljust(80)[:80] for line in fh][:100]
    for line in lines:
        line_no += 1
        tally, acct_len = unstring(line, fields)
        acct, kind, amt_txt, memo = (f[0] for f in fields)
        reason = ""
        amount = numval(amt_txt)
        if tally < 3:
            reason = "TOO FEW FIELDS"
        elif acct_len != 8:
            reason = "BAD ACCOUNT"
        elif amount is None:
            reason = "BAD AMOUNT"
        elif kind not in ("PAY", "ADJ", "FEE", "REF"):
            reason = "BAD KIND"
        entry = None
        if not reason:
            entry = next((e for e in totals.table if e[0] == acct), None)
            if entry is None:
                reason = "NO SUCH ACCOUNT"
        if reason:
            rejected += 1
            out.append("LINE " + edit(line_no % 1000, "ZZ9") + " REJECTED " + reason.ljust(20))
            continue
        part = rem = None
        if kind == "PAY":
            amt = amount.quantize(CENT, rounding=ROUND_HALF_EVEN)
            entry[1] -= amt
            paid += amt
        elif kind == "ADJ":
            amt = amount.quantize(CENT, rounding=ROUND_HALF_UP)
            entry[1] += amt
            other += amt
        elif kind == "FEE":
            amt = amount.quantize(CENT, rounding=ROUND_DOWN)
            entry[1] += amt
            other += amt
            # DIVIDE ... ROUNDED REMAINDER: the part is rounded, but the remainder
            # is worked out from the truncated quotient.
            part = (amt / 3).quantize(CENT, rounding=ROUND_HALF_UP)
            rem = amt - (amt / 3).quantize(CENT, rounding=ROUND_DOWN) * 3
        else:
            amt = amount.quantize(CENT, rounding=ROUND_FLOOR)
            entry[1] += amt
            other += amt
        whole = amt.to_integral_value(rounding=ROUND_FLOOR)
        hash_at = memo.find("#")
        if hash_at >= 0:
            head, tail = memo[: hash_at + 1], memo[hash_at + 1:]
            memo = head + tail.translate(str.maketrans("0123456789", "XXXXXXXXXX"))
            fields[3] = (memo, 30)
        applied += 1
        out.append(kind + " " + acct + " " + edit(amt, "----,--9.99") + " WHOLE " + edit(whole, "-----9")
                   + " BAL " + edit(entry[1], "Z,ZZZ,ZZ9.99CR") + " " + memo)
        if kind == "FEE":
            out.append("    FEE SPLIT 3X" + edit(part, "---,--9.99") + " REMAINDER " + edit(rem, "-9.99"))
    out.append("POSTED  " + edit(applied, "ZZ9") + "  REJECTED " + edit(rejected, "ZZ9") + "  PAID  "
               + edit(paid, "$$,$$$,$$9.99-") + "  OTHER " + edit(other, "$$,$$$,$$9.99-"))


def main(argv):
    with open(argv[1], "r", encoding="latin-1", newline="\n") as fh:
        lines = [line.rstrip("\n").ljust(80)[:80] for line in fh]
    out = []
    totals = Totals()
    pos = 0
    if lines and lines[0][0] == "H":
        rec = lines[0]
        date = rec[1:9]
        out.append("STATEMENTS FOR " + rec[9:29] + " DATED " + date[6:8] + "/" + date[4:6] + "/" + date[0:4])
        out.append("")
        pos = 1
    for rec in lines[pos:]:
        if rec[0] == "C":
            one_account(rec, out, totals)
    out.append("ACCOUNTS BILLED " + edit(totals.billed, "ZZ9") + "  REJECTED " + edit(totals.rejected, "ZZ9")
               + "  CREDITS " + edit(totals.credits, "ZZ9"))
    out.append("TOTAL UNITS " + edit(totals.units, "ZZZ,ZZZ,ZZ9") + "  TOTAL CURRENT "
               + edit(totals.current, "$$$,$$$,$$9.99"))
    average = rounded(totals.current / totals.billed, CENT) if totals.billed else Decimal(0)
    out.append("TOTAL DUE " + edit(totals.due, "$$$,$$$,$$9.99") + "  AVERAGE BILL "
               + edit(average, "$$,$$$,$$9.99"))
    out.append("NET POSITION " + edit(totals.net, "---,---,--9.99"))
    post_payments(argv[2], out, totals)
    with open(argv[3], "w", encoding="latin-1", newline="\n") as fh:
        for line in out:
            fh.write(line[:72].rstrip(" ") + "\n")


if __name__ == "__main__":
    main(sys.argv)
