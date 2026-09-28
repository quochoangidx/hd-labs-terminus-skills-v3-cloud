"""Expectation model for the temporary disability statements, derived from manual TD-7.

Written from /app/docs/td-benefits-manual.md alone; it never imports or calls the
tdbenefit package. Exact arithmetic throughout (integers and Fraction). Where the
manual gives no rule for a figure, the model mirrors the shipped package's step and
says so in a "Shipped step" comment; every other step follows the manual.

    python3 model.py JOB.json     prints the expected statements for a job file
"""

import json
import sys
from datetime import date, timedelta
from fractions import Fraction

FRIDAY = 4  # date.weekday() of a Friday (1.4: every wage line is paid on one)
BASE_WEEKS = 13  # 2.3
WEEKS_PAY = 2_000  # 2.2: a week's pay is a wage line of 2,000 cents or more
PARTIAL_WEEK = 1_000  # 2.8: a week of partial disability earned 1,000 cents or more
WAITING = 3  # 2.6
RETRO_FROM = 14  # 4.1
TWO_THIRDS = Fraction(2, 3)  # 3.4, 5.1


def day(text):
    return date.fromisoformat(text)


def sunday_closing(d):
    """1.2: the payroll week holding d runs Monday..Sunday and is known by that Sunday."""
    return d + timedelta(days=6 - d.weekday())


def cents(q):
    """1.1: nearest cent (divisors 13, 3, 5 and 7 never leave an exact half; amounts are nought or more)."""
    q = Fraction(q)
    assert q >= 0
    return int((q + Fraction(1, 2)).__floor__())


def counted_week(paid, amount):
    """The Sunday of the payroll week a wage line counts toward (3.2: exactly one)."""
    d = day(paid)
    if amount >= WEEKS_PAY:
        # 2.2 + 3.1: a week's pay pays the week whose Sunday is five days before its Friday.
        return d - timedelta(days=5)
    # Shipped step: the manual gives no rule for which week a line smaller than a week's
    # pay counts toward; the package counts every line toward the week holding its payday.
    return sunday_closing(d)


def base_period(injury):
    """2.1, 2.3: the thirteen payroll weeks before the week of injury (Sundays)."""
    s = sunday_closing(day(injury))
    return {s - timedelta(days=7 * k) for k in range(1, BASE_WEEKS + 1)}


def average_weekly_wage(claim):
    weeks = base_period(claim["injury"])
    wages = sum(c for p, c in claim["wages"] if counted_week(p, c) in weeks)  # 3.2
    return cents(Fraction(wages, BASE_WEEKS))  # 3.3


def row_in_force(rates, d):
    """2.4: the last row taking effect on or before d (1.3: the first row always does)."""
    chosen = None
    for row in rates:
        if day(row["from"]) <= d:
            chosen = row
    return chosen


def weekly_rate(aww, rates, injury):
    row = row_in_force(rates, day(injury))
    if aww < row["min"]:  # 3.5
        return aww
    rate = cents(TWO_THIRDS * aww)  # 3.4
    return max(row["min"], min(row["max"], rate))


def disability_days(periods):
    """2.5: calendar days covered, both ends included."""
    return sum((day(last) - day(first)).days + 1 for first, last in periods)


def statement(claim, rates):
    aww = average_weekly_wage(claim)
    rate = weekly_rate(aww, rates, claim["injury"])
    days = disability_days(claim["disability"])
    waiting = min(WAITING, days)  # 2.6
    retro = waiting if days >= RETRO_FROM else 0  # 4.1
    paid = days - waiting + retro  # 4.2
    ttd = cents(Fraction(rate * paid, 7))  # 4.3
    tpd = 0
    for _week, earned in claim["earnings"]:
        loss = aww - earned if earned < aww else 0  # 2.7
        if earned >= PARTIAL_WEEK:
            share = TWO_THIRDS  # 2.8, 5.1
        else:
            # Shipped step: the manual gives no share for a week of the partial earnings that
            # is not a week of partial disability; the package pays every such week 60 per
            # cent of its wage loss (5.2 gives it a benefit; the cap is the shared step, kept).
            share = Fraction(3, 5)
        tpd += min(cents(share * loss), rate)  # 5.1, 5.2
    return {
        "claim": claim["claim"],
        "aww": aww,
        "rate": rate,
        "waiting_days": waiting,
        "retro_days": retro,
        "ttd_days": paid,
        "ttd": ttd,
        "tpd_weeks": len(claim["earnings"]),
        "tpd": tpd,
        "total": ttd + tpd,
    }


def statements(job):
    return {"statements": [statement(claim, job["rates"]) for claim in job["claims"]]}


def within_limits(job):
    """An executable form of manual section 1; returns a list of violations (empty when clean)."""
    bad = []
    lo, hi = date(2016, 1, 1), date(2035, 12, 31)

    def in_years(text):
        return lo <= day(text) <= hi

    rates = job["rates"]
    if not 1 <= len(rates) <= 40:
        bad.append("rate rows")
    for k, row in enumerate(rates):
        if not in_years(row["from"]):
            bad.append("row date")
        if not (20_000 <= row["max"] <= 400_000 and 1_000 <= row["min"] < row["max"]):
            bad.append("row figures")
        if k and not day(row["from"]) > day(rates[k - 1]["from"]):
            bad.append("row order")
    claims = job["claims"]
    if not 1 <= len(claims) <= 200:
        bad.append("claims")
    if len({c["claim"] for c in claims}) != len(claims):
        bad.append("claim numbers")
    for c in claims:
        inj = day(c["injury"])
        if not (1 <= len(c["claim"]) <= 24 and in_years(c["injury"]) and inj >= day(rates[0]["from"])):
            bad.append("claim head")
        if len(c["wages"]) > 120:
            bad.append("wage lines")
        for paid, amount in c["wages"]:
            d = day(paid)
            if not (in_years(paid) and inj - timedelta(days=400) <= d <= inj + timedelta(days=30) and 1 <= amount <= 500_000
                    and d.weekday() == FRIDAY):
                bad.append("wage line")
        per = c["disability"]
        if not 1 <= len(per) <= 12:
            bad.append("periods")
        prev = None
        for first, last in per:
            f, end = day(first), day(last)
            if not (in_years(first) and in_years(last) and f <= end < f + timedelta(days=400)):
                bad.append("period")
            if (prev is None and f < inj) or (prev is not None and f <= prev):
                bad.append("period order")
            prev = end
        if len(c["earnings"]) > 104:
            bad.append("partial weeks")
        prevw = None
        for week, earned in c["earnings"]:
            w = day(week)
            if not (in_years(week) and w.weekday() == 6 and 0 <= earned <= 500_000):
                bad.append("partial week")
            if prevw is not None and w <= prevw:
                bad.append("partial order")
            if w - timedelta(days=6) <= prev:
                bad.append("partial before disability end")
            prevw = w
    return bad


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as handle:
        job = json.load(handle)
    json.dump(statements(job), sys.stdout)
    sys.stdout.write("\n")
