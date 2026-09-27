"""Bank stock and bank PDL (SOP section 6)."""


def summarise(records, frozen, line_of):
    banks = {}
    for rec in records:
        if rec["kind"] != "freeze":
            continue
        bank = banks.get(rec["bank"])
        if bank is None:
            bank = {"bank": rec["bank"], "line": line_of[rec["id"]], "vials_left": 0}
            banks[rec["bank"]] = bank
        bank["vials_left"] += rec["vials"]
        bank["pdl"] = frozen[rec["id"]][0]
    return list(banks.values())
