"""variants.py: build natural over-repair trees (Oracle plus one edit) under authoring/variants/."""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATCHED = HERE / "patched" / "app"

R, C, E, P, N = 'src/qpcrrel/replicates.py', 'src/qpcrrel/curve.py', 'src/qpcrrel/expression.py', 'src/qpcrrel/plate.py', 'src/qpcrrel/ntc.py'
VARIANTS = {
    # T1 natural over-repairs: the replicate rules put into the shared mean_ct(), which curve points also use
    "T1_outliers_in_shared_mean": [
        (R, "    return sum(cts) / len(cts)\n", "    kept = without_outliers(cts)\n    return sum(kept) / len(kept)\n"),
        (R, "    return mean_ct(without_outliers(replicates))", "    return mean_ct(replicates)")],
    "T1_pipeline_in_shared_mean": [
        (R, "    return sum(cts) / len(cts)\n",
         "    kept = without_outliers([ct for ct in cts if EARLIEST_CYCLE <= ct <= 35.0])\n    return sum(kept) / len(kept)\n"),
        (R, "    return mean_ct(without_outliers(replicates))", "    return mean_ct(replicates)")],
    # T2 natural over-repairs: the 10.00 floor put into the shared called(), which the NTC test also uses
    "T2_floor_in_called": [
        (P, "ct is not None and ct <= CUTOFF_CYCLE", "ct is not None and 10.0 <= ct <= CUTOFF_CYCLE")],
    "T2_ntc_uses_reportable": [
        (N, "from .plate import called\n", "from .replicates import reportable\n"),
        (N, "return bool(called(ntc_cts))", "return bool(reportable(ntc_cts))")],
    # each departure reverted on its own (the shipped step put back into the Oracle)
    "revert_D1": [(R, "    return [ct for ct in called(cts) if ct >= EARLIEST_CYCLE]", "    return called(cts)")],
    "revert_D2": [(C, "        if ct is not None:\n            levels.setdefault(quantity, []).append(ct)",
                   "        levels.setdefault(quantity, []).append(40.0 if ct is None else ct)")],
    "revert_D4": [(C, "    return 10 ** (-1.0 / slope(points))", "    return min(10 ** (-1.0 / slope(points)), PERFECT_DOUBLING)")],
    "revert_D5": [(R, "    return mean_ct(without_outliers(replicates))", "    return mean_ct(replicates)")],
    "revert_D6": [(R, "        return None\n", "        return 40.0\n"),
                  (E, "fold = None if flags else", 'fold = None if "ntc" in flags else')],
    "revert_D7": [(E, """    def relative_quantity(gene):
        delta = sample_ct(plate.replicates(cal, gene)) - sample_ct(plate.replicates(sample, gene))
        return factors[gene] ** delta

    logs = [math.log(relative_quantity(gene)) for gene in plate.reference_genes]
    return relative_quantity(target) / math.exp(sum(logs) / len(logs))""", """    factor = factors[target]
    shifts = [sample_ct(plate.replicates(cal, g)) - sample_ct(plate.replicates(sample, g)) for g in plate.reference_genes]
    delta = sample_ct(plate.replicates(cal, target)) - sample_ct(plate.replicates(sample, target))
    return factor ** delta / factor ** (sum(shifts) / len(shifts))""")],
}


def build():
    out = {}
    for name, edits in VARIANTS.items():
        dst = HERE / "variants" / name / "app"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(PATCHED, dst)
        for rel, old, new in edits:
            f = dst / rel
            text = f.read_text()
            assert text.count(old) == 1, (name, rel, old)
            f.write_text(text.replace(old, new))
        out[name] = dst
    return out


if __name__ == "__main__":
    for k, v in build().items():
        print(k, v)
