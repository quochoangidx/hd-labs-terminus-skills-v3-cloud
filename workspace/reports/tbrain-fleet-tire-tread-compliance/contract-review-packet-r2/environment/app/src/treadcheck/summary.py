"""Assemble one summary entry per tire."""

from . import gauges, retread, status, wear


def summarise_tire(job, tire, table):
    """The summary entry for one tire."""
    depths = gauges.reading_depths(tire, table)
    latest = depths[-1]
    worn, distance = wear.tread_worn(tire, depths)
    return {
        "tire": tire["tire"],
        "position": tire["position"],
        "latest": latest,
        "worn": worn,
        "distance": distance,
        "rate": wear.wear_rate(worn, distance),
        "status": status.status(tire["position"], latest),
        "retread": retread.casing_eligible(tire, job["report_date"]),
    }


def build_summary(job):
    """The summary of a job, as the object the driver prints."""
    table = gauges.offsets(job)
    entries = []
    for tire in job["tires"]:
        entries.append(summarise_tire(job, tire, table))
    return {"tires": entries}
