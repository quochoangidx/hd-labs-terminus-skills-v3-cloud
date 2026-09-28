"""Hours, fee and amount due."""

HOURLY_RATE = {"CAR": 300, "VAN": 450, "MOTO": 150}
VALIDATION_CREDIT = 200
GRACE_MINUTES = 15
DAILY_MAXIMUM = 2400
CAPPED = ("CAR", "VAN")
GRACED = ("CAR", "VAN")


def hours(session):
    """Every started hour of the stay."""
    return -(-(session["exit"] - session["entry"]) // 60)


def parking_fee(session):
    stay = session["exit"] - session["entry"]
    if stay <= GRACE_MINUTES and session["vehicle"] in GRACED:
        return 0
    fee = hours(session) * HOURLY_RATE[session["vehicle"]]
    if session["vehicle"] in CAPPED:
        fee = min(fee, DAILY_MAXIMUM * -(-stay // 1440))
    return fee


def amounts(session):
    """The parking fee and the amount due for one session."""
    fee = parking_fee(session)
    due = fee - VALIDATION_CREDIT if session["validated"] else fee
    return fee, due
