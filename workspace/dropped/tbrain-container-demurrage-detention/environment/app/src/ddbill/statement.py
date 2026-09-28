"""The billing statement (tariff rules sections 6 and 7)."""

from .dates import Calendar, parse, show
from .freetime import chargeable_days, last_free_day
from .rates import scale_for, tier_charge
from .stays import MERCHANT, TERMINAL, stage_days, stages

FREE_DAYS_KEY = {TERMINAL: "terminal_free_days", MERCHANT: "merchant_free_days"}


def stage_entry(stage, container, contract, calendar):
    """One stage's figures for the statement."""
    free_days = contract[FREE_DAYS_KEY[stage["name"]]]
    count = chargeable_days(stage, free_days, calendar)
    scale = scale_for(contract, stage["name"], container["size"])
    return {
        "first_day": show(stage["first"]),
        "last_free_day": show(last_free_day(stage, free_days, calendar)),
        "days": stage_days(stage),
        "chargeable": count,
        "amount": tier_charge(count, scale),
        "status": "ended" if stage["ended"] else "running",
    }


def discount_on(amount, percent):
    """The contract discount on a container's amount, in cents."""
    return amount * percent // 100


def container_entry(container, job, calendar, cut_off):
    """One container's statement entry."""
    contract = job["contracts"][container["contract"]]
    entries = {TERMINAL: None, MERCHANT: None}
    for stage in stages(container, cut_off):
        entries[stage["name"]] = stage_entry(stage, container, contract, calendar)
    amount = sum(entry["amount"] for entry in entries.values() if entry is not None)
    discount = discount_on(amount, contract["discount_percent"])
    return {
        "id": container["id"],
        "terminal": entries[TERMINAL],
        "merchant": entries[MERCHANT],
        "amount": amount,
        "discount": discount,
        "net": amount - discount,
    }


def build_statement(job):
    """The statement for one job, as a JSON-ready dict."""
    calendar = Calendar(job)
    cut_off = parse(job["cut_off"])
    containers = [container_entry(c, job, calendar, cut_off) for c in job["containers"]]
    return {
        "invoice": job["invoice"],
        "containers": containers,
        "total": sum(entry["net"] for entry in containers),
    }
