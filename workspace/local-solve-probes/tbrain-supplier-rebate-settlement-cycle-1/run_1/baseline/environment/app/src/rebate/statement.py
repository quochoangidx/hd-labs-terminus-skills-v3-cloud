"""One settlement statement per supplier account."""

from .chargeback import chargebacks
from .growth import growth_bonus
from .ledger import quarter_purchases
from .protection import protection_credit
from .returns import returns_credit
from .settle import settle
from .tiers import load_tiers, tier_rate, volume_rebate


def account_statement(account, tiers):
    quarter = account["quarter"]
    purchases = quarter_purchases(account["purchases"], quarter)
    returned = returns_credit(account["returns"], quarter)
    net = purchases - returned
    bp = tier_rate(purchases, tiers)
    rebate = volume_rebate(net, bp)
    growth = growth_bonus(net, account["prior"])
    protection = protection_credit(account["notices"], quarter)
    charged = chargebacks(account["sales"], quarter)
    total = rebate + growth + protection + charged
    paid, carried = settle(total)
    return {
        "account": account["account"],
        "purchases": purchases,
        "returns": returned,
        "net": net,
        "tier_bp": bp,
        "rebate": rebate,
        "growth": growth,
        "protection": protection,
        "chargebacks": charged,
        "total": total,
        "paid": paid,
        "carried": carried,
    }


def build_statements(job):
    """The settlement statements for a job, in the order of its accounts."""
    tiers = load_tiers(job["tiers"])
    return {"settlements": [account_statement(account, tiers) for account in job["accounts"]]}
