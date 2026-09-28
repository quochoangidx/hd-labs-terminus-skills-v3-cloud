"""Field payments, claim totals and the claim statements."""

from .leaf import leaf_loss
from .loss import field_loss, payable_loss
from .figures import figure
from .plots import field_averages
from .replant import replant_line
from .rounding import half_up
from .sheet import UNITS, read_claim


def indemnity(payable, per_acre, acres):
    """The payable loss (tenths of a per cent) taken of the liability, in cents.

    The liability is per_acre dollars times acres, given in tenths of an acre.
    """
    return half_up(payable * per_acre * acres, 100)


def field_statement(field):
    """The statement entry for one field."""
    stand, defoliation = field_averages(field.plots)
    leaf = leaf_loss(defoliation, field.stage)
    loss = field_loss(stand, leaf)
    payable = payable_loss(loss, field.deductible)
    paid_loss = indemnity(payable, field.per_acre, field.acres)
    replant = replant_line(field.replanted)
    return {
        "field": field.code,
        "stand_loss": stand,
        "defoliation": defoliation,
        "leaf_loss": leaf,
        "loss": loss,
        "payable": payable,
        "indemnity": paid_loss,
        "replant": replant,
        "payment": paid_loss + replant,
    }


def claim_statement(record):
    """The statement for one claim of a job."""
    number, fields = read_claim(record)
    entries = [field_statement(field) for field in fields]
    total = sum(entry["payment"] for entry in entries)
    paid = total if total >= figure(UNITS["total"], "floor") else 0
    return {"claim": number, "fields": entries, "total": total, "paid": paid}


def build_statements(job):
    """The claim statements for a job, in job order."""
    return {"claims": [claim_statement(record) for record in job["claims"]]}
