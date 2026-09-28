"""Expected lineage reports worked out from SOP CB-3, independently of the package.

This module never imports or runs `cellbank`. Every figure the SOP sets is written here
from the SOP's own rules. Where the SOP has no rule for a figure (3.1 is written in viable
counts, which 2.3 gives only to valid counts; 6.2 speaks only of a bank in use, 2.5), the
instruction keeps the figure the shipped step works out today, so the model mirrors that
shipped expression and says so at the site.
"""

import math

VALID_FROM = 70.0  # SOP 2.3
NEAR_WITHIN = 3.0  # SOP 5.2


def viable_count(cells, viability):
    """SOP 2.3: cells x viability / 100 for a valid count; no other count has one."""
    if viability >= VALID_FROM:
        return cells * viability / 100
    return None


class Lineage:
    """Resolves every suspension of one log by following source and vial links (4.3)."""

    def __init__(self, log):
        self.lines = {line["name"]: line for line in log["lines"]}
        self.records = log["records"]
        self.by_id = {rec["id"]: rec for rec in self.records}
        self.memo = {}

    def count_viability(self, suspension_id):
        # SOP 2.2: a harvest's count is its culture's; a thawed vial's is the thaw's.
        return self.by_id[suspension_id]["viability"]

    def doublings(self, culture):
        harvest = viable_count(culture["harvested"], culture["viability"])
        seed = viable_count(culture["seeded"], self.count_viability(culture["source"]))
        if harvest is None or seed is None:
            # 3.1 has no rule here (a count that is not valid). Shipped step (growth.doublings):
            # log2(harvested / seeded) on the recorded totals.
            return math.log2(culture["harvested"] / culture["seeded"])
        return math.log2(harvest / seed)  # SOP 3.1, below nought kept (3.2)

    def line_of(self, rec_id):
        rec = self.by_id[rec_id]
        while rec["kind"] != "thaw":
            rec = self.by_id[rec["source"]]
        return rec["line"]

    def figures(self, rec_id):
        """(passage, pdl, age, doublings) of a suspension; doublings is None for a thaw."""
        if rec_id in self.memo:
            return self.memo[rec_id]
        rec = self.by_id[rec_id]
        if rec["kind"] == "thaw":
            if rec["vial"] is None:
                line = self.lines[rec["line"]]
                # SOP 4.2 and 5.1: a supplier vial
                out = (line["seed_passage"], line["seed_pdl"], line["seed_pdl"], None)
            else:
                harvest_id = self.by_id[rec["vial"]]["source"]
                passage, pdl, age, _ = self.figures(harvest_id)
                # SOP 4.2: thawing is not a passage; 5.1: the vial keeps its harvest's age
                out = (passage, pdl, age, None)
        elif rec["kind"] == "culture":
            s_passage, s_pdl, s_age, _ = self.figures(rec["source"])
            gained = self.doublings(rec)
            pdl = s_pdl + gained  # SOP 4.1
            out = (s_passage + 1, pdl, max(s_age, pdl), gained)  # SOP 4.1, 5.1
        else:
            raise ValueError("a freeze is not a suspension")
        self.memo[rec_id] = out
        return out


def flag_for(age, max_pdl):
    # SOP 5.2
    if age > max_pdl:
        return "LIMIT"
    if age > max_pdl - NEAR_WITHIN:
        return "NEAR"
    return ""


def build_report(log):
    tree = Lineage(log)
    cultures = []
    for rec in log["records"]:
        if rec["kind"] != "culture":
            continue
        passage, pdl, age, gained = tree.figures(rec["id"])
        line = tree.line_of(rec["id"])
        cultures.append(
            {
                "id": rec["id"],
                "line": line,
                "passage": passage,
                "doublings": gained,
                "pdl": pdl,
                "flag": flag_for(age, tree.lines[line]["max_pdl"]),
            }
        )

    uses = {}
    for rec in log["records"]:
        if rec["kind"] == "thaw" and rec["vial"] is not None:
            uses[rec["vial"]] = uses.get(rec["vial"], 0) + 1

    order = []
    freezes = {}
    for rec in log["records"]:
        if rec["kind"] == "freeze":
            if rec["bank"] not in freezes:
                order.append(rec["bank"])
                freezes[rec["bank"]] = []
            freezes[rec["bank"]].append(rec)

    banks = []
    for name in order:
        members = freezes[name]
        left = [f["vials"] - uses.get(f["id"], 0) for f in members]  # SOP 6.1
        vial_pdl = [tree.figures(f["source"])[1] for f in members]  # SOP 6.2 vial PDL
        in_stock = [p for p, n in zip(vial_pdl, left) if n > 0]
        if in_stock:
            pdl = max(in_stock)  # SOP 6.2
        else:
            # SOP 6.2 has no rule for a bank not in use (2.5). Shipped step
            # (banks.summarise): the PDL of the bank's latest freeze in the log.
            pdl = vial_pdl[-1]
        banks.append(
            {
                "bank": name,
                "line": tree.line_of(members[0]["source"]),
                "vials_left": sum(left),
                "pdl": pdl,
            }
        )
    return {"cultures": cultures, "banks": banks}
