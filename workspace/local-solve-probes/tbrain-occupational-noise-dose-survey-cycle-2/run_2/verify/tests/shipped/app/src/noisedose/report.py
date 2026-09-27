"""Assembling the survey report."""

from .flags import has_impulse, over_ceiling
from .groups import group_rows
from .shift import shift_dose
from .survey import load_workers
from .twa import status_for, to_tenth, twa_for


def worker_row(worker):
    """The report row of one loaded worker."""
    dose = shift_dose(worker["log"], worker["shift_minutes"])
    twa = twa_for(dose)
    if twa is not None:
        twa = to_tenth(twa)
    ceiling = over_ceiling(worker["log"])
    impulse = has_impulse(worker["peaks"])
    return {
        "id": worker["id"],
        "group": worker["group"],
        "dose": dose,
        "twa": twa,
        "status": "over" if ceiling or impulse else status_for(twa),
        "ceiling": ceiling,
        "impulse": impulse,
    }


def build_report(survey):
    """The exposure report of a decoded survey: workers in survey order, then groups."""
    workers = [worker_row(worker) for worker in load_workers(survey)]
    return {"survey": survey["survey"], "workers": workers, "groups": group_rows(workers)}
