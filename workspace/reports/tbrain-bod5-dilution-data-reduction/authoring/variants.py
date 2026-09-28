"""Build one-edit variants of the Oracle under authoring/variants/<name>/app (revert one departure, or a trap's natural fix)."""
import shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent
V = {
 "revert_D1": ("bottles.py", "MIN_DEPLETION = 2.5", "MIN_DEPLETION = 2.0"),
 "revert_D2": ("bottles.py", "MIN_FINAL_DO = 1.2", "MIN_FINAL_DO = 1.0"),
 "revert_D3": ("seed.py", "    reference = [c for c in controls if is_usable(c)] or list(controls)\n    rates = [depletion(c) / c[\"seed_ml\"] for c in reference]\n    return sum(rates) / len(rates)",
               "    return sum(depletion(c) for c in controls) / sum(c[\"seed_ml\"] for c in controls)"),
 "revert_D4": ("bottles.py", "    return (depletion(bottle) - seed_correction(bottle, seed_factor)) / sample_fraction(bottle)",
               "    return depletion(bottle) / sample_fraction(bottle) - seed_correction(bottle, seed_factor)"),
 "revert_D5": ("samples.py", "limiting = max(", "limiting = min("),
 "revert_D6": ("qc.py", "    return max(depletion(b) for b in blanks)", "    return sum(depletion(b) for b in blanks) / len(blanks)"),
 "revert_D7": ("qc.py", 'if rel_mine == "=" and rel_theirs == "=":', "if False:"),
 "revert_D8": ("report.py", "    return round(value, 2 - math.floor(math.log10(abs(value)))) if value else 0.0", "    return round(value, 1)"),
 # natural fixes of each trap (everything else the Oracle)
 # T1 natural misses: keep today's pooled figure when no control is usable (keep-today reading), or 0.0
 "natural_T1_keep_pooled": ("seed.py", "    reference = [c for c in controls if is_usable(c)] or list(controls)\n    rates = [depletion(c) / c[\"seed_ml\"] for c in reference]\n    return sum(rates) / len(rates)",
                            "    rates = [depletion(c) / c[\"seed_ml\"] for c in controls if is_usable(c)]\n    if rates:\n        return sum(rates) / len(rates)\n    return sum(depletion(c) for c in controls) / sum(c[\"seed_ml\"] for c in controls)"),
 "natural_T1_zero": ("seed.py", "    reference = [c for c in controls if is_usable(c)] or list(controls)\n    rates = [depletion(c) / c[\"seed_ml\"] for c in reference]\n    return sum(rates) / len(rates)",
                     "    rates = [depletion(c) / c[\"seed_ml\"] for c in controls if is_usable(c)]\n    return sum(rates) / len(rates) if rates else 0.0"),
 "natural_T2_mean_always": ("qc.py", 'if rel_mine == "=" and rel_theirs == "=":', "if True:"),
}
def build():
    root = HERE / "variants"
    shutil.rmtree(root, ignore_errors=True)
    for name, (f, a, b) in V.items():
        dst = root / name / "app"
        shutil.copytree(HERE / "oracle" / "app", dst)
        p = dst / "src" / "bodcalc" / f
        s = p.read_text(); assert a in s, name
        p.write_text(s.replace(a, b, 1))
    return root
if __name__ == "__main__":
    print(build())
