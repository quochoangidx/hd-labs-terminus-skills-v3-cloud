"""Build one-edit variants of the Oracle package (authoring only): each departure reverted, and each
natural over-repair of a trap. python3 variants.py  ->  variants/<name>/app/src/coopsum"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE = HERE / "oracle" / "app"
OUT = HERE / "variants"

EDITS = {
    "D1_max_on_form_day": [("crediting.py", "maxima[day - shift] = high", "maxima[day] = high")],
    "D2_precip_on_form_day": [("crediting.py", "credited = day if unread else day - shift", "credited = day")],
    "D3_dd_from_unrounded_mean": [("temperature.py", """        rounded = half_up(maxima[day] + minima[day], 20)
        heating += max(0, BASE - rounded)
        cooling += max(0, rounded - BASE)
    return heating, cooling""", """        twice = maxima[day] + minima[day]
        heating += max(0, 1300 - twice)
        cooling += max(0, twice - 1300)
    return half_up(heating, 20), half_up(cooling, 20)""")],
    "D4_mean_of_daily_means": [("temperature.py", """    if complete(maxima, minima, days):
        return half_up(mean_of(maxima) + mean_of(minima), 2)
""", "")],
    "D5_strict_temperature_thresholds": [("temperature.py", "value >= 900", "value > 900"),
                                         ("temperature.py", "value <= 320)\n    freezing", "value < 320)\n    freezing"),
                                         ("temperature.py", "if value <= 320)\n    zero", "if value < 320)\n    zero"),
                                         ("temperature.py", "if value <= 0)", "if value < 0)")],
    "D6_first_day_on_ties": [("temperature.py", "value >= by_day[chosen]", "value > by_day[chosen]"),
                             ("temperature.py", "value <= by_day[chosen]", "value < by_day[chosen]"),
                             ("precipitation.py", "totals[day] >= totals[chosen]", "totals[day] > totals[chosen]")],
    "D7_trace_as_hundredth": [("entries.py", "    if text == TRACE:\n        return 0", "    if text == TRACE:\n        return 1")],
    "D8_strict_precip_thresholds": [("precipitation.py", "totals[day] >= TENTH", "totals[day] > TENTH"),
                                    ("precipitation.py", "totals[day] >= INCH", "totals[day] > INCH")],
    "T1_natural_shift_every_amount": [("crediting.py", "credited = day if unread else day - shift",
                                       "credited = day - shift")],
    "T2_natural_null_when_incomplete": [("temperature.py", """        return half_up(mean_of(maxima) + mean_of(minima), 2)
    both =""", """        return half_up(mean_of(maxima) + mean_of(minima), 2)
    return None
    both =""")],
    "T2_natural_new_formula_everywhere": [("temperature.py", """    if complete(maxima, minima, days):
        return half_up(mean_of(maxima) + mean_of(minima), 2)
""", """    if maxima and minima:
        return half_up(mean_of(maxima) + mean_of(minima), 2)
    return None
""")],
}


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    for name, edits in EDITS.items():
        dest = OUT / name / "app"
        shutil.copytree(ORACLE, dest)
        for fname, old, new in edits:
            p = dest / "src" / "coopsum" / fname
            s = p.read_text()
            if s.count(old) != 1:
                sys.exit(f"{name}: {fname}: anchor count {s.count(old)}: {old!r}")
            p.write_text(s.replace(old, new))
    return sorted(EDITS)


if __name__ == "__main__":
    print("\n".join(build()))
