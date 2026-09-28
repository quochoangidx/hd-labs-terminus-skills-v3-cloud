"""One-edit variants of the Oracle tree (authoring only): each departure reverted alone, and the natural
over-repairs of each trap. VARIANTS[name] = [(file, old, new), ...] applied to oracle/app/src/cemsqr."""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE = HERE / "oracle" / "app"

D7_OLD = '''        if k >= WINDOW - 1:  # DRP-4 6.1: twenty-nine operating days before it
            window = [hour["conc"] for d in days[k - WINDOW + 1:k + 1]
                      for hour in d["hours"] if hour["valid"]]'''
D7_NEW = '''        import datetime
        num = lambda s: datetime.date.fromisoformat(s).toordinal()
        if num(day["day"]) - num(days[0]["day"]) >= WINDOW - 1:
            window = [hour["conc"] for d in days[:k + 1] if num(day["day"]) - num(d["day"]) < WINDOW
                      for hour in d["hours"] if hour["valid"]]'''
D8_NEW = '''            window = [mean(h["conc"] for h in d["hours"]) for d in days[k - WINDOW + 1:k + 1]]'''
D8_OLD = '''            window = [hour["conc"] for d in days[k - WINDOW + 1:k + 1]
                      for hour in d["hours"] if hour["valid"]]'''

VARIANTS = {
    "D1-all-records-averaged": [("hours.py", 'records = valid_readings(hour)\n        hour["nox"]',
                                 'records = hour["records"]\n        hour["nox"]')],
    "D2-four-ok-quarters": [("hours.py", '    good = len(valid_readings(hour))\n',
                             '    return len(hour["records"]) == 4 and all(r[CODE] == "OK" for r in hour["records"])\n')],
    "D3-ambient-21": [("correction.py", "half_up(nox * Fraction(209 - reference) / (209 - o2))",
                       "half_up(nox * Fraction(210 - reference) / (210 - o2))")],
    "D4-mass-from-corrected": [("report.py", 'mass_rate(hour["nox"], hour["flow"])', 'mass_rate(hour["conc"], hour["flow"])')],
    "D5-whole-hour-mass": [("report.py", ' * Fraction(hour["quarters"], 4)', '')],
    "D6-carry-forward-lost": [("substitute.py", 'if hour["lost"]:', 'if False:')],
    "D7-calendar-window": [("rolling.py", D7_OLD, D7_NEW)],
    "D8-daily-means-all-hours": [("rolling.py", D8_OLD, D8_NEW)],
    "D9-at-limit-exceeds": [("rolling.py", "rolling > limit", "rolling >= limit")],
    "T1-fill-rule-for-every-substitute-hour": [("substitute.py", 'elif not hour["valid"]:', 'elif False:'),
                                               ("substitute.py", 'if hour["lost"]:', 'if not hour["valid"]:')],
    "T1-carry-last-valid-hour-only": [("substitute.py", '        last = (hour["conc"], hour["rate"])\n    return',
                                       '        if hour["valid"]:\n            last = (hour["conc"], hour["rate"])\n    return')],
    "T2-ambient-209-for-every-hour": [("correction.py", "AMBIENT_O2 = 210", "AMBIENT_O2 = 209"),
                                       ("correction.py", "if o2 < 190:", "if False:")],
    "T2-cap-moved-to-190": [("correction.py", "O2_CAP = 200", "O2_CAP = 190")],
    "T2-firing-formula-for-every-hour": [("correction.py", "if o2 < 190:", "if True:")],
}


def build(name, dest):
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(ORACLE, dest / "app")
    for f, old, new in VARIANTS[name]:
        p = dest / "app" / "src" / "cemsqr" / f
        s = p.read_text()
        assert s.count(old) == 1, (name, f, old)
        p.write_text(s.replace(old, new))
    return dest / "app"
