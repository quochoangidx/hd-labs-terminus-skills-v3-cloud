"""Expectation model for tbrain-container-demurrage-detention, written from tariff rules DT-3.

It reads only the job and the rules and never imports the package under /app/src. Where the rules
give no rule for a value (5.1 and 5.4, through the instruction's silence clause), the model keeps
the step the package took before the repair, applied to the figures the rules do define; each such
place is marked "Shipped step".
"""

from datetime import date, timedelta

ONE = timedelta(days=1)
TERMINAL, MERCHANT = "terminal", "merchant"


def _d(text):
    return date.fromisoformat(text)


def is_working_day(day, holidays):
    """2.5: Monday to Friday and not a port holiday."""
    return day.weekday() < 5 and day not in holidays


def stage_list(container, cut_off):
    """2.1-2.4: (name, first day, last day, ended) for each stage the container has."""
    moves = {m["move"]: _d(m["date"]) for m in container["history"]}
    out = []
    gate_out = moves.get("GATE_OUT")
    out.append((TERMINAL, moves["DISCHARGE"], gate_out if gate_out else cut_off, gate_out is not None))
    if gate_out is not None:
        back = moves.get("EMPTY_RETURN")
        out.append((MERCHANT, gate_out, back if back else cut_off, back is not None))
    return out


def last_free_day(name, first, free, holidays, closures):
    """3.1-3.3."""
    if free == 0:
        return first - ONE
    if name == MERCHANT:
        return first + timedelta(days=free - 1)
    day, used = first, 0
    while True:
        if is_working_day(day, holidays) and day not in closures:
            used += 1
            if used == free:
                return day
        day += ONE


def chargeable_dates(name, last, lfd, closures):
    """4.1: the stage's days after its last free day; closure days drop out at the terminal."""
    out = []
    day = lfd + ONE
    while day <= last:
        if not (name == TERMINAL and day in closures):
            out.append(day)
        day += ONE
    return out


def revision_in_force(revisions, day):
    """5.1: the latest revision effective on or before the day, or None before the earliest."""
    found = None
    for rev in revisions:
        if _d(rev["effective"]) <= day:
            found = rev
    return found


def stage_scale(contract, name, size, first_chargeable):
    """5.2."""
    rev = revision_in_force(contract["revisions"], first_chargeable)
    if rev is None:
        # Shipped step: 5.1 gives no rule for the scale when no revision is in force on the first
        # chargeable day; the package takes the last revision on the rate sheet.
        rev = contract["revisions"][-1]
    return rev["scales"][name][size]


def tier_total(count, tiers):
    """5.3: each chargeable day at the rate of the tier that takes it."""
    total, left = 0, count
    for length, rate in tiers:
        take = left if length is None else min(left, length)
        total += take * rate
        left -= take
        if left == 0:
            break
    return total


def discount(amount, percent, all_ended):
    """6.2 with 1.3; an exact half cent goes up (amounts are never below nought)."""
    if all_ended:
        return (amount * percent + 50) // 100
    # Shipped step: 5.4 gives no rule for the discount of a container with a running stage (6.2
    # needs that stage's charge); the package takes percent of the container's amount, truncated.
    return amount * percent // 100


def container_report(container, job, holidays, closures, cut_off):
    contract = job["contracts"][container["contract"]]
    entries = {TERMINAL: None, MERCHANT: None}
    ended_all = True
    for name, first, last, ended in stage_list(container, cut_off):
        free = contract[name + "_free_days"]
        lfd = last_free_day(name, first, free, holidays, closures)
        dates = chargeable_dates(name, last, lfd, closures)
        amount = 0
        if dates:
            amount = tier_total(len(dates), stage_scale(contract, name, container["size"], dates[0]))
        entries[name] = {
            "first_day": first.isoformat(),
            "last_free_day": lfd.isoformat(),
            "days": (last - first).days + 1,
            "chargeable": len(dates),
            "amount": amount,
            "status": "ended" if ended else "running",
        }
        ended_all = ended_all and ended
    amount = sum(e["amount"] for e in entries.values() if e is not None)
    disc = discount(amount, contract["discount_percent"], ended_all)
    return {
        "id": container["id"],
        "terminal": entries[TERMINAL],
        "merchant": entries[MERCHANT],
        "amount": amount,
        "discount": disc,
        "net": amount - disc,
    }


def report(job):
    """The statement tariff rules DT-3 give for the job (section 7)."""
    holidays = {_d(x) for x in job.get("holidays", [])}
    closures = {_d(x) for x in job.get("closures", [])}
    cut_off = _d(job["cut_off"])
    rows = [container_report(c, job, holidays, closures, cut_off) for c in job["containers"]]
    return {"invoice": job["invoice"], "containers": rows, "total": sum(r["net"] for r in rows)}


# ---- trap-input predicates, used by the authoring scorer and generators ----

def carries_running_discount_edge(job):
    """T1 input: a container with a running stage whose discount differs between truncation and
    rounding half up (so keeping today's step shows)."""
    holidays = {_d(x) for x in job.get("holidays", [])}
    closures = {_d(x) for x in job.get("closures", [])}
    cut_off = _d(job["cut_off"])
    for c in job["containers"]:
        row = container_report(c, job, holidays, closures, cut_off)
        stages = [s for s in (row["terminal"], row["merchant"]) if s is not None]
        pct = job["contracts"][c["contract"]]["discount_percent"]
        if any(s["status"] == "running" for s in stages) and (row["amount"] * pct) % 100 >= 50:
            return True
    return False


def carries_pre_sheet_start(job):
    """T2 input: a stage whose first chargeable day falls before its contract's earliest effective date."""
    holidays = {_d(x) for x in job.get("holidays", [])}
    closures = {_d(x) for x in job.get("closures", [])}
    cut_off = _d(job["cut_off"])
    for c in job["containers"]:
        contract = job["contracts"][c["contract"]]
        earliest = _d(contract["revisions"][0]["effective"])
        for name, first, last, _ended in stage_list(c, cut_off):
            lfd = last_free_day(name, first, contract[name + "_free_days"], holidays, closures)
            dates = chargeable_dates(name, last, lfd, closures)
            if dates and dates[0] < earliest:
                return True
    return False


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.dumps(report(json.load(handle))))
