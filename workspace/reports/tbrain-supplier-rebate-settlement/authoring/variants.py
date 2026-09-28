"""Build scorer-validation variants of the package under authoring/variants/<name>/src (authoring only)."""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHIPPED = HERE / "oracle" / "a" / "src"
ORACLE = HERE / "oracle" / "b" / "src"


def edit(root, f, a, b):
    p = root / "rebate" / f
    t = p.read_text()
    assert a in t, (f, a)
    p.write_text(t.replace(a, b, 1))


# name -> (base, [(file, old, new), ...])
INPLACE = {
    "shipped-oracle-but-TA": [("rates.py", '"settlement_minimum": "minimum_settlement"', '"settlement_minimum": "small_credit"'),
                              ("rates.py", '"small_credit": 5000,', '"small_credit": 25000,')],
    "shipped-oracle-but-TB": [("rates.py", '"return_charge": "return_handling"', '"return_charge": "unit_handling"'),
                              ("rates.py", '"unit_handling": 25,', '"unit_handling": 40,')],
}

VARIANTS = {
    "oracle": ("oracle", []),
    "shipped": ("shipped", []),
    # natural fixes of each trap's driving departure (the rest of the Oracle kept)
    "TA-inplace-shared-constant": ("shipped-oracle-but-TA", []),
    "TB-inplace-shared-constant": ("shipped-oracle-but-TB", []),
    "TC-shift-every-line": ("oracle", [
        ("ledger.py", "        if units >= CARTON_UNITS:\n            day += TRANSIT\n", "        day += TRANSIT\n")]),
    # exclusion readings and guard removal (other over-repairs)
    "TA-no-credit-for-tidy-ups": ("oracle", [
        ("protection.py", "        credit = (old_cents - new_cents) * on_hand\n",
         "        if old_cents - new_cents < 250:\n            continue\n        credit = (old_cents - new_cents) * on_hand\n")]),
    "TA-guard-removed": ("oracle", [
        ("protection.py", '        if credit < figure("notice_cutoff"):\n            credit = 0\n', "")]),
    "TB-no-chargeback-for-price-match": ("oracle", [
        ("chargeback.py", 'if below < figure("claim_cutoff"):', "if below < 100:")]),
    "TC-drop-loose-lines": ("oracle", [
        ("ledger.py", "        if units >= CARTON_UNITS:\n            day += TRANSIT\n",
         "        if units < CARTON_UNITS:\n            continue\n        day += TRANSIT\n")]),
    # each departure reverted on its own
    "D1-reverted": ("oracle", [("ledger.py", "        if units >= CARTON_UNITS:\n            day += TRANSIT\n", "")]),
    "D2-reverted": ("oracle", [("statement.py", "tier_rate(net, tiers)", "tier_rate(purchases, tiers)")]),
    "D3-reverted": ("oracle", [("tiers.py", "if amount >= threshold:", "if amount > threshold:")]),
    "D4-reverted": ("oracle", [("rates.py", '"return_handling": 40', '"return_handling": 25')]),
    "D5-reverted": ("oracle", [("growth.py", "(net - prior) * GROWTH_SHARE_BP", "net * GROWTH_SHARE_BP")]),
    "D6-reverted": ("oracle", [("rates.py", '"minimum_settlement": 25000', '"minimum_settlement": 5000')]),
    "D7-reverted": ("oracle", [("tiers.py", "    return half_up(net * bp, 10000)\n", "    return net * bp // 10000\n")]),
}


def build():
    out = {}
    for name, (base, edits) in VARIANTS.items():
        dest = HERE / "variants" / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(SHIPPED if base == "shipped" else ORACLE, dest / "src")
        edits = INPLACE.get(base, []) + edits
        for f, a, b in edits:
            edit(dest / "src", f, a, b)
        out[name] = dest
    return out


if __name__ == "__main__":
    for k, v in build().items():
        print(k, v)
