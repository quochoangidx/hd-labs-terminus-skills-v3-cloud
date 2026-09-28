"""One commission statement per rep."""

from .bonus import bonus
from .bookings import bookings, quarter_orders
from .clawback import clawback
from .commission import commission
from .payout import payout


def rep_statement(rep):
    quarter = rep["quarter"]
    booked = bookings(rep["orders"], quarter)
    earned = commission(booked, rep["quota"])
    bonus_cents = bonus(quarter_orders(rep["orders"], quarter))
    taken = clawback(rep["credits"], quarter)
    total = earned + bonus_cents + rep["carried"] - taken
    recovered, owed, paid, carried = payout(total, rep["draw"], rep["owed"])
    return {
        "rep": rep["rep"],
        "bookings": booked,
        "commission": earned,
        "bonus": bonus_cents,
        "clawback": taken,
        "total": total,
        "recovered": recovered,
        "owed": owed,
        "paid": paid,
        "carried": carried,
    }


def build_statements(job):
    """The commission statements for a job, in the order of its reps."""
    return {"statements": [rep_statement(rep) for rep in job["reps"]]}
