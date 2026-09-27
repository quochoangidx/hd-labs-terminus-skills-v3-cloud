"""Independent model of policy LF-5 (/app/docs/overdue-fines-policy.md).

Worked out from the policy alone; it never imports the package under repair. Where the policy gives no rule for
a figure, the model mirrors the shipped package's step for it and says so ("Shipped step").
"""

PERIOD = {"BOOK": 21, "DVD": 7}  # 2.1


def sunday(day):
    return day % 7 == 6  # 1.1


def due(loan):
    # Shipped step (no loan period is given for a journal): dates.due() adds 14 days.
    return loan["borrowed"] + PERIOD.get(loan["kind"], 14)


def line(loan):
    due_day = due(loan)
    if loan["returned"] > due_day:  # 2.2, 3.1: late
        late = sum(1 for d in range(due_day + 1, loan["returned"] + 1) if not sunday(d))
        fine = min(late * loan["daily_fine"], loan["replacement"])
    else:
        # Shipped step (no late days or fine are given for a loan that is not late): dates.late_days() gives the
        # return day less the due day and fines.fine() that many days at the daily fine, nought or a credit.
        late = loan["returned"] - due_day
        fine = late * loan["daily_fine"]
    return {"id": loan["id"], "due": due_day, "late": late, "fine": fine}


def statement(loans):
    lines = [line(x) for x in loans["loans"]]
    return {"branch": loans["branch"], "loans": lines, "total": sum(x["fine"] for x in lines)}


def silent(loan):
    """The figures the policy leaves to today's code that this loan carries (used by seal.py)."""
    out = set()
    if loan["kind"] not in PERIOD:
        out.add("journal")
    if loan["returned"] <= due(loan):
        out.add("idle")
    return out
