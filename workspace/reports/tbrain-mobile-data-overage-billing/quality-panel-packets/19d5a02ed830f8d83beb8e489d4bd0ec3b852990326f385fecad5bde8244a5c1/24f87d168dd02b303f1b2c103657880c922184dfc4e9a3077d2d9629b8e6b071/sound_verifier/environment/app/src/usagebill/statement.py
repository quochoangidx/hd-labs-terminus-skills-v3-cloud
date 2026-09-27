"""The usage statement for one account file."""

from .charges import charge, overage
from .usage import allowance, used


def line(entry):
    megabytes = used(entry)
    included = allowance(entry)
    over = overage(megabytes, included)
    return {"id": entry["id"], "used": megabytes, "allowance": included, "over": over, "charge": charge(entry, over)}


def statement(usage):
    lines = [line(x) for x in usage["lines"]]
    return {"account": usage["account"], "lines": lines, "total": sum(x["charge"] for x in lines)}
