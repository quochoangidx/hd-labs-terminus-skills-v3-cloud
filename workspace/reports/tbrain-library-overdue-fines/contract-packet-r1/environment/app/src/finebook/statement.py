"""The fines statement for one return file."""

from .dates import due, late_days
from .fines import fine


def line(loan):
    due_day = due(loan)
    late = late_days(loan, due_day)
    return {"id": loan["id"], "due": due_day, "late": late, "fine": fine(loan, late)}


def statement(loans):
    lines = [line(x) for x in loans["loans"]]
    return {"branch": loans["branch"], "loans": lines, "total": sum(x["fine"] for x in lines)}
