"""Receipt: departures differ, silent cases match the shipped package, variants per family.

Writes ../receipts/departure-trap-checks.json.
"""

import hashlib
import json
from collections import namedtuple

import check_local
import gen
import pkgload
import variants

Plot = namedtuple("Plot", "stand dead leaf")
m = gen.model


def main():
    shipped = pkgload.load(variants.SHIPPED)
    oracle = pkgload.load(variants.ORACLE)
    sp, op = shipped.plots, oracle.plots
    sr, orp = shipped.replant, oracle.replant
    silent_plots = mismatch_ship = mismatch_oracle_all = 0
    for stand in range(20, 201):
        for dead in range(0, stand + 1):
            p = Plot(stand, dead, 0)
            want = m.plot_stand_figure(stand, dead)
            if op.stand_figure(p) != want:
                mismatch_oracle_all += 1
            if 10 * dead < stand:
                silent_plots += 1
                if sp.stand_figure(p) != want:
                    mismatch_ship += 1
    rep_ship_mis = sum(sr.replant_line(r) != m.replant_line(r) for r in range(0, 100))
    rep_oracle_mis = sum(orp.replant_line(r) != m.replant_line(r) for r in range(0, 50001))
    families = {}
    for name in ["shipped"] + list(variants.VARIANTS):
        families[name] = check_local.score(variants.OUT / name / "app")
    out = {
        "schema": "departure-and-trap-checks",
        "model_sha256": hashlib.sha256((gen.TASK / "solution" / "model.py").read_bytes()).hexdigest(),
        "patch_sha256": hashlib.sha256((gen.TASK / "solution" / "fix.patch").read_bytes()).hexdigest(),
        "silent_case_shipped_equals_model": {
            "TA_plots_not_hail_thinned_checked": silent_plots,
            "TA_shipped_stand_figure_mismatches": mismatch_ship,
            "TB_replantings_0_to_99_tenths_checked": 100,
            "TB_shipped_replant_line_mismatches": rep_ship_mis,
        },
        "oracle_equals_model_function_level": {
            "every_plot_20_200_all_dead_mismatches": mismatch_oracle_all,
            "replant_0_to_50000_tenths_mismatches": rep_oracle_mis,
        },
        "family_scoring": {"seed": check_local.SEED, "per_family": check_local.PER,
                           "failed_families_by_variant": families},
    }
    ok = (mismatch_ship == 0 and rep_ship_mis == 0 and mismatch_oracle_all == 0 and rep_oracle_mis == 0
          and families["oracle"] == [] and all(f"D{k}" in families["shipped"] for k in range(1, 9))
          and all(f"D{k}" in families[f"rev-D{k}"] for k in range(1, 9))
          and all(families[v] == ["TA"] for v in variants.VARIANTS if v.startswith("TA-"))
          and all(families[v] == ["TB"] for v in variants.VARIANTS if v.startswith("TB-"))
          and all(families[v] == [] for v in variants.VARIANTS if v.startswith("alt-")))
    out["status"] = "pass" if ok else "fail"
    path = gen.HERE.parent / "receipts" / "departure-trap-checks.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["silent_case_shipped_equals_model"]), json.dumps(out["oracle_equals_model_function_level"]), out["status"])


if __name__ == "__main__":
    main()
