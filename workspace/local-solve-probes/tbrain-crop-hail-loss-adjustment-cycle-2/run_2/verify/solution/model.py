"""Expectation model for the crop-hail claim statements (never imports the package).

Written from /app/docs/loss-adjustment-procedure.md (edition 7). The two figures the
procedure does not reach mirror the step the shipped package takes for them, and say so:

- the stand-loss figure of a sample plot that is not hail-thinned (2.1, 3.1, 3.2): the
  shipped step takes the dead and broken plants as a share of the stand and drops a figure
  below 5.0 per cent to nought;
- the replant line of a field that is not a replanted field (2.2, 6.1, 6.2): the shipped
  step prices the acres at 3,000 cents an acre and drops a line below 2,500 cents to nought.

statements(job) returns the whole statement object the driver must print; within_limits(job)
returns the list of section 1 limits a job breaks (empty when it keeps them all).
"""

STAGE_SHARE = {"V6": 5, "V10": 15, "V14": 35, "VT": 100, "R2": 75, "R4": 40, "R5": 15}
OPTIONS = ("full", "straight", "vanishing")

MINIMUM_LOSS = 80  # 5.1, tenths of a per cent
STRAIGHT = 100  # 5.2
VANISH_FROM = 200  # 5.2
REPLANT_PER_ACRE = 3000  # 6.1, cents
MINIMUM_CLAIM = 10000  # 7.2, cents

# Shipped steps (not reached by the procedure).
SHIPPED_PLOT_TRACE = 50  # tenths of a per cent
SHIPPED_REPLANT_TRACE = 2500  # cents


def rounded(num, den):
    """num / den to the nearest unit, an exact half up (1.1); num >= 0, den > 0."""
    return (2 * num + den) // (2 * den)


def hail_thinned(stand, dead):
    """2.1: one plant in ten of the stand, or more, dead or broken."""
    return 10 * dead >= stand


def plot_stand_figure(stand, dead):
    share = rounded(1000 * dead, stand)
    if hail_thinned(stand, dead):
        return share  # 3.1
    # Shipped step: a plot the procedure does not reach keeps today's figure,
    # the share with trace figures below 5.0 per cent dropped.
    return share if share >= SHIPPED_PLOT_TRACE else 0


def replant_line(replanted_tenths):
    line = replanted_tenths * REPLANT_PER_ACRE // 10  # exact: tenths x 300
    if replanted_tenths >= 100:
        return line  # 2.2, 6.1
    # Shipped step: a replanting of less than 10.0 acres keeps today's line,
    # priced the same way and dropped below 2,500 cents.
    return line if line >= SHIPPED_REPLANT_TRACE else 0


def field(entry):
    plots = entry["plots"]
    n = len(plots)
    stand_loss = rounded(sum(plot_stand_figure(s, d) for s, d, _ in plots), n)  # 3.3
    defoliation = rounded(sum(leaf for _, _, leaf in plots), n)  # 3.2, 3.3
    leaf_loss = rounded(defoliation * STAGE_SHARE[entry["stage"]], 100)  # 4.1, 4.3
    loss = stand_loss + rounded(leaf_loss * (1000 - stand_loss), 1000)  # 4.2
    if loss < MINIMUM_LOSS:  # 5.1
        payable = 0
    elif entry["deductible"] == "full":
        payable = loss
    elif entry["deductible"] == "straight":
        payable = max(0, loss - STRAIGHT)
    else:
        payable = min(loss, max(0, 2 * (loss - VANISH_FROM)))
    # 2.3, 5.3: liability = per_acre dollars x 100 cents x acres/10 (whole cents);
    # payable/1000 of it, rounded once to the cent.
    indemnity = rounded(payable * entry["per_acre"] * entry["acres"], 100)
    replant = replant_line(entry["replanted"])
    return {
        "field": entry["field"],
        "stand_loss": stand_loss,
        "defoliation": defoliation,
        "leaf_loss": leaf_loss,
        "loss": loss,
        "payable": payable,
        "indemnity": indemnity,
        "replant": replant,
        "payment": indemnity + replant,
    }


def claim(entry):
    fields = [field(f) for f in entry["fields"]]
    total = sum(f["payment"] for f in fields)  # 7.1
    return {"claim": entry["claim"], "fields": fields, "total": total,
            "paid": total if total >= MINIMUM_CLAIM else 0}  # 7.2


def statements(job):
    return {"claims": [claim(c) for c in job["claims"]]}


def _int(v, lo, hi):
    return type(v) is int and lo <= v <= hi


def within_limits(job):
    """Section 1 limits the job breaks, as short strings (empty list when none)."""
    bad = []
    claims = job.get("claims") if isinstance(job, dict) else None
    if not isinstance(claims, list) or not 1 <= len(claims) <= 50:
        return ["claims 1..50"]
    numbers = [c.get("claim") for c in claims]
    if len(set(numbers)) != len(numbers):
        bad.append("claim numbers unique")
    for c in claims:
        if not (isinstance(c["claim"], str) and 1 <= len(c["claim"]) <= 16):
            bad.append("claim number 1..16 characters")
        fields = c.get("fields")
        if not isinstance(fields, list) or not 1 <= len(fields) <= 30:
            bad.append("fields 1..30")
            continue
        codes = [f.get("field") for f in fields]
        if len(set(codes)) != len(codes):
            bad.append("field codes unique in a claim")
        for f in fields:
            if not (isinstance(f["field"], str) and 1 <= len(f["field"]) <= 16):
                bad.append("field code 1..16 characters")
            if not _int(f["acres"], 10, 50000):
                bad.append("acres 1.0..5000.0")
            if not _int(f["per_acre"], 10, 2000):
                bad.append("per_acre 10..2000 dollars")
            if f["deductible"] not in OPTIONS:
                bad.append("deductible option")
            if f["stage"] not in STAGE_SHARE:
                bad.append("stage on the chart")
            if not (_int(f["replanted"], 0, 50000) and f["replanted"] <= f["acres"]):
                bad.append("replanted 0..acres")
            plots = f["plots"]
            if not isinstance(plots, list) or not 1 <= len(plots) <= 40:
                bad.append("plots 1..40")
                continue
            for p in plots:
                if not (isinstance(p, list) and len(p) == 3):
                    bad.append("plot shape")
                    continue
                stand, dead, leaf = p
                if not _int(stand, 20, 200):
                    bad.append("stand 20..200")
                elif not _int(dead, 0, stand):
                    bad.append("dead 0..stand")
                if not _int(leaf, 0, 1000):
                    bad.append("leaf 0..1000")
    return bad
