"""One benefit statement per claim."""

from .dates import parse_day
from .disability import total_disability
from .partial import partial_disability
from .payroll import average_weekly_wage
from .rates import load_table, weekly_rate

FIELDS = ("claim", "aww", "rate", "waiting_days", "retro_days", "ttd_days", "ttd", "tpd_weeks", "tpd", "total")


def claim_statement(claim, table):
    """The statement for one claim against a loaded rate table."""
    injury = parse_day(claim["injury"])
    aww = average_weekly_wage(claim["wages"], injury)
    rate = weekly_rate(aww, table, injury)
    ttd = total_disability(claim["disability"], rate)
    tpd = partial_disability(claim["earnings"], aww)
    figures = {"claim": claim["claim"], "aww": aww, "rate": rate}
    figures.update(ttd)
    figures.update(tpd)
    figures["total"] = ttd["ttd"] + tpd["tpd"]
    return {key: figures[key] for key in FIELDS}


def build_statements(job):
    """Statements for every claim of a job, in job order."""
    table = load_table(job["rates"])
    return {"statements": [claim_statement(claim, table) for claim in job["claims"]]}
