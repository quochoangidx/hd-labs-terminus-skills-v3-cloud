"""Oracle variants for authoring checks (never shipped).

Each variant is the Oracle tree with one edit: a departure reverted (D*), or a trap's natural
over-repair (T*nat*). `build(name, dest)` writes the variant's app tree under dest and returns
the app dir.
"""

from pathlib import Path

import trees

RESULTS = "src/platecount/results.py"
PLATES = "src/platecount/plates.py"
REPORT = "src/platecount/report.py"

LOOP = '''            for later in dilutions[i + 1:]:
                if later.step == dilution.step + 1 and any(is_countable(r) for r in later.plates):
                    counted.append(later)
'''
EDITS = {
    # departures reverted one at a time
    "D1": [(PLATES, "COUNTABLE_LOW = 20\nCOUNTABLE_HIGH = 300", "COUNTABLE_LOW = 25\nCOUNTABLE_HIGH = 250")],
    "D2": [(RESULTS, LOOP, "")],
    "D3": [(PLATES, "return dilution.volume * dilution_at(dilution.step)", "return dilution_at(dilution.step)")],
    "D4": [(REPORT, "if scaled - digits >= Fraction(1, 2):", "if scaled - digits > Fraction(1, 2) or (scaled - digits == Fraction(1, 2) and digits % 2):")],
    "D5": [(RESULTS, "return BELOW, 1 / plated_amount(dilutions[0])", "return BELOW, 1 / plated_amount(dilutions[-1])")],
    "D6": [(RESULTS, "return ABOVE, COUNTABLE_HIGH / plated_amount(crowded[-1])", "return ABOVE, COUNTABLE_HIGH / plated_amount(crowded[0])")],
    "D7": [(RESULTS, """            return ESTIMATE, Fraction(sum(dilution.plates)) / (len(dilution.plates) * plated_amount(dilution))""",
            """            return ESTIMATE, Fraction(sum(sum(d.plates) for d in dilutions)) / sum(len(d.plates) * plated_amount(d) for d in dilutions)""")],
    "D8": [(PLATES, "return reading is None or reading > COUNTABLE_HIGH", "return colonies(reading) > COUNTABLE_HIGH")],
    # T1 natural over-repairs: pool the next listed dilution / the next one holding a countable plate
    "T1nat_listnext": [(RESULTS, LOOP, '''            if i + 1 < len(dilutions) and any(is_countable(r) for r in dilutions[i + 1].plates):
                counted.append(dilutions[i + 1])
''')],
    "T1nat_nextcountable": [(RESULTS, LOOP, '''            for later in dilutions[i + 1:]:
                if any(is_countable(r) for r in later.plates):
                    counted.append(later)
                    break
''')],
    # T2 natural over-repair: a count takes only the countable plates of its counted dilutions
    "T2nat_countable_only": [(PLATES, "    return not is_crowded(reading)", "    return is_countable(reading)")],
}


def build(name, dest):
    pkg = trees.oracle_tree(dest)
    app = pkg.parent.parent
    for rel, old, new in EDITS.get(name, []):
        p = app / rel
        s = p.read_text()
        assert s.count(old) == 1, (name, rel, old[:60])
        p.write_text(s.replace(old, new))
    return app


def shipped(dest):
    import shutil
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(trees.TASK / "environment" / "app", dest / "app")
    return dest / "app"
