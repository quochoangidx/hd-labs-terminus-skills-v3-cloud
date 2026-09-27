"""Population doublings of one culture (SOP section 3)."""

import math


def doublings(culture):
    return math.log2(culture["harvested"] / culture["seeded"])
