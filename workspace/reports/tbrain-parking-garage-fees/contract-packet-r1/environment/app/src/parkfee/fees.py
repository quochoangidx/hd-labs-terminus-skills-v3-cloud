"""Hours, fee and amount due."""

HOURLY_RATE = {"CAR": 300, "VAN": 300, "MOTO": 150}
VALIDATION_CREDIT = 200


def hours(session):
    """Every started hour of the stay."""
    return -(-(session["exit"] - session["entry"]) // 60)


def amounts(session):
    """The parking fee and the amount due for one session."""
    fee = hours(session) * HOURLY_RATE[session["vehicle"]]
    due = fee - VALIDATION_CREDIT if session["validated"] else fee
    return fee, due
