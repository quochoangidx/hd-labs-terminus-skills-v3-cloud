"""jobgen.py: seeded plate generators for the skeleton scorer, the fuzz and the departure/trap checks.

Authoring-only (never shipped in the task). Every family draws plates inside SOP QP-7
section 1 (checked with model.within_limits) and declares which trap inputs it carries
(checked with model.trap_inputs): broad and departure families carry none; TA carries only
"every reportable replicate an outlier"; TB carries only "fewer than three curve points".
"""

import importlib.util
import math
import random
import string
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # never leave __pycache__ under the task tree

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-qpcr-relative-expression"

_spec = importlib.util.spec_from_file_location("qpcr_model", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model)

NAME_CHARS = string.ascii_letters + string.digits + "-"


def ct2(x):
    """A Ct rounded to two decimals, kept inside 5.00-45.00."""
    return round(min(45.0, max(5.0, x)), 2)


def names(rng, n, lo=1, hi=10):
    out = []
    while len(out) < n:
        s = "".join(rng.choice(NAME_CHARS) for _ in range(rng.randint(lo, hi)))
        if s not in out:
            out.append(s)
    return out


class Builder:
    def __init__(self, rng):
        self.rng = rng
        self.wells = []
        self.n = 0

    def add(self, kind, gene, ct, **extra):
        self.n += 1
        well = {"well": f"{'ABCDEFGHIJKLMNOP'[(self.n - 1) // 24 % 16]}{(self.n - 1) % 24 + 1:02d}", "kind": kind, "gene": gene, "ct": ct}
        well.update(extra)
        self.wells.append(well)


def standard_series(rng, levels, slope_range=(-4.2, -2.9), wells=(2, 4), undetermined=0.0, single=0.0, window=True):
    """[(quantity, [ct,...])] for a dilution series of `levels` levels.

    window=True keeps every standard Ct inside 10.5-34.5 (no T1 input from the window side)."""
    s = rng.uniform(*slope_range)
    top_ct = rng.uniform(11.0, 16.0) if window else rng.uniform(6.0, 16.0)
    room = 34.3 - top_ct
    steps = [x for x in (1.0, 0.5, 0.30103) if (levels - 1) * x * -s <= room] if window else [1.0, 0.5, 0.30103]
    if not steps:
        steps = [0.30103]
        levels = max(0, min(levels, int(room / (0.30103 * -s)) + 1))
    step = rng.choice(steps)
    top_log = min(8.0, rng.uniform(-3 + step * max(0, levels - 1), 8.0)) if levels else 0.0
    out = []
    for k in range(levels):
        lq = top_log - step * k
        q = min(1e8, max(0.001, float(f"{10 ** lq:.6g}")))
        base = top_ct + s * (math.log10(q) - top_log)
        n = rng.randint(*wells)
        cts = [ct2(base + rng.uniform(-0.12, 0.12)) for _ in range(n)]
        if rng.random() < single:
            cts = [cts[0]] + ["Undetermined"] * rng.randint(0, 2)
        elif rng.random() < undetermined and n >= 3:
            cts[rng.randrange(n)] = "Undetermined"
        out.append((q, cts))
    return out


def tight(rng, centre, n, spread=0.18):
    return [ct2(centre + rng.uniform(-spread, spread)) for _ in range(n)]


def plate_of(rng, refs, targets, samples, cal, series, reps, ntc=None):
    """Assemble a plate dict; series: gene -> [(q, cts)], reps: (sample, gene) -> [ct], ntc: gene -> [ct]."""
    b = Builder(rng)
    order = []
    for gene, levels in series.items():
        for q, cts in levels:
            for ct in cts:
                order.append(("standard", gene, ct, {"quantity": q}))
    for (sample, gene), cts in reps.items():
        for ct in cts:
            order.append(("unknown", gene, ct, {"sample": sample}))
    for gene, cts in (ntc or {}).items():
        for ct in cts:
            order.append(("ntc", gene, ct, {}))
    if rng.random() < 0.5:
        rng.shuffle(order)
    for kind, gene, ct, extra in order:
        b.add(kind, gene, ct, **extra)
    return {"plate": "P-" + "".join(rng.choice(NAME_CHARS) for _ in range(rng.randint(1, 12))),
            "calibrator": cal, "reference_genes": refs, "target_genes": targets, "wells": b.wells}


def base_plate(rng, *, n_ref=None, n_tgt=None, n_samples=None, slope_range=(-4.2, -2.9), levels=(3, 8),
               reps=(1, 4), centre=(14.0, 32.0), equal_factor=False, ntc_undetermined=True):
    """A trap-free governed plate: every gene has three or more curve points, tight replicates."""
    n_ref = n_ref or rng.randint(1, 4)
    n_tgt = n_tgt or rng.randint(1, 8)
    gene_names = names(rng, n_ref + n_tgt, 1, 8)
    refs, targets = gene_names[:n_ref], gene_names[n_ref:]
    n_samples = n_samples or rng.randint(1, 12)
    samples = names(rng, n_samples, 1, 12)
    cal = rng.choice(samples)
    series = {}
    shared = standard_series(rng, rng.randint(*levels), slope_range) if equal_factor else None
    for g in gene_names:
        series[g] = shared if equal_factor else standard_series(rng, rng.randint(*levels), slope_range)
    reps_map = {}
    for s in samples:
        for g in gene_names:
            reps_map[(s, g)] = tight(rng, rng.uniform(*centre), rng.randint(*reps))
    ntc = {}
    for g in gene_names:
        k = rng.randint(0, 2)
        if k:
            ntc[g] = ["Undetermined"] * k if ntc_undetermined else [ct2(rng.uniform(36.0, 45.0)) for _ in range(k)]
    return refs, targets, samples, cal, series, reps_map, ntc


def assemble(rng, parts):
    refs, targets, samples, cal, series, reps_map, ntc = parts
    return plate_of(rng, refs, targets, samples, cal, series, reps_map, ntc)


# ---------------------------------------------------------------- families


def fam_broad(rng):
    """Trap-free governed plates mixing every governed feature."""
    parts = base_plate(rng, reps=(1, 6), ntc_undetermined=False)
    refs, targets, samples, cal, series, reps_map, ntc = parts
    genes = refs + targets
    for g in genes:  # some Undetermined standards, some single-determined levels (curve points stay >= 3)
        if rng.random() < 0.3:
            series[g] = standard_series(rng, rng.randint(5, 8), undetermined=0.3, single=0.15)
    for key in list(reps_map):
        r = rng.random()
        if r < 0.08:
            reps_map[key] = ["Undetermined"] * rng.randint(1, 3)
        elif r < 0.14:
            reps_map[key] = reps_map[key] + [35.0]
        elif r < 0.2:
            c = rng.uniform(15, 30)
            reps_map[key] = tight(rng, c, 3, 0.1) + [ct2(c + rng.choice([-1, 1]) * rng.uniform(0.8, 3.0))]
    for g in genes:
        if rng.random() < 0.15:
            ntc[g] = [ct2(rng.uniform(10.0, 35.0))]
    return assemble(rng, parts)


def _neutral(rng, slope_range=(-4.2, -3.4), equal_factor=True, **kw):
    """Plate whose governed rules all agree between the shipped package and the SOP
    (factors at most 2 and shared by every gene, tight pairs of replicates inside the
    window, determined standards, no NTC signal), so one change shows alone."""
    kw.setdefault("reps", (1, 2))
    kw.setdefault("centre", (14.0, 30.0))
    return base_plate(rng, slope_range=slope_range, equal_factor=equal_factor, **kw)


def fam_d1(rng):
    """2.2 reportable window: replicates at exactly 35.00 and earlier than 10.00 (sets of one or two)."""
    parts = _neutral(rng, centre=(20.0, 30.0))
    refs, targets, samples, cal, series, reps_map, ntc = parts
    shapes = [
        lambda: [35.0],
        lambda: [35.0, ct2(rng.uniform(34.51, 34.99))],
        lambda: [ct2(rng.uniform(5.0, 9.99))],
        lambda: [ct2(rng.uniform(12.0, 20.0)), ct2(rng.uniform(5.0, 9.99))],
        lambda: [35.0, 35.0],
    ]
    keys = [k for k in reps_map if k[1] in targets]
    for key in rng.sample(keys, rng.randint(1, min(4, len(keys)))):
        reps_map[key] = rng.choice(shapes)()
    return assemble(rng, parts)


def fam_d2(rng):
    """2.4 curve points: Undetermined standards and single-determined levels (three or more curve points remain)."""
    parts = _neutral(rng)
    refs, targets, samples, cal, series, reps_map, ntc = parts
    while True:
        levels = standard_series(rng, rng.randint(5, 8), (-4.2, -3.4), wells=(3, 4), undetermined=0.6, single=0.3)
        pts = model.curve_points([(q, ct) for q, cts in levels for ct in cts])
        if len(pts) >= 3 and any(ct == "Undetermined" for _q, cts in levels for ct in cts):
            break
    for g in refs + targets:
        series[g] = levels
    return assemble(rng, parts)


def fam_d4(rng):
    """3.1 a standard curve's factor above 2 is not capped."""
    parts = _neutral(rng, slope_range=(-3.30, -2.90))
    return assemble(rng, parts)


def fam_d5(rng):
    """4.1 every replicate more than 0.50 from the median is an outlier (two or more strays, not all)."""
    parts = _neutral(rng)
    refs, targets, samples, cal, series, reps_map, ntc = parts
    keys = list(reps_map)
    for key in rng.sample(keys, rng.randint(1, min(6, len(keys)))):
        c = rng.uniform(16, 30)
        shape = rng.choice([3, 5, 6])
        if shape == 3:
            vals = [c, c - rng.uniform(0.56, 3.0), c + rng.uniform(0.56, 3.0)]
        elif shape == 5:
            vals = [c - 0.1, c, c + 0.1, c - rng.uniform(0.7, 3.0), c + rng.uniform(0.7, 3.0)]
        else:
            vals = [c - 0.1, c, c + 0.05, c + 0.1, c - rng.uniform(0.7, 3.0), c + rng.uniform(0.7, 3.0)]
        vals = [ct2(v) for v in vals]
        rng.shuffle(vals)
        reps_map[key] = vals
    return assemble(rng, parts)


def fam_d6(rng):
    """4.3/5.4 a gene not detected in a sample or the calibrator: no mean Ct, no fold change."""
    parts = _neutral(rng, n_samples=rng.randint(2, 10))
    refs, targets, samples, cal, series, reps_map, ntc = parts
    for _ in range(rng.randint(1, 4)):
        s = rng.choice(samples)
        g = rng.choice(refs + targets)
        reps_map[(s, g)] = rng.choice([["Undetermined"] * rng.randint(1, 3), [ct2(rng.uniform(35.01, 42.0)), "Undetermined"]])
    return assemble(rng, parts)


def fam_d7(rng):
    """5.1/5.2 every gene uses its own factor; geometric mean over reference genes."""
    parts = _neutral(rng, equal_factor=False, n_ref=rng.randint(1, 4))
    return assemble(rng, parts)


def fam_t1(rng):
    """Trap T1: dilution levels whose wells a replicate rule would change (a stray well among three or
    more, a concentrated standard earlier than 10.00, a dilute one later than 35.00); 2.4 averages them all."""
    parts = _neutral(rng)
    refs, targets, samples, cal, series, reps_map, ntc = parts
    while True:
        levels = standard_series(rng, rng.randint(3, 6), (-4.2, -3.4), wells=(3, 4), window=False)
        shaped = []
        for q, cts in levels:
            cts = list(cts)
            if rng.random() < 0.5:
                cts[rng.randrange(len(cts))] = ct2(cts[0] + rng.choice([-1, 1]) * rng.uniform(0.6, 1.6))
            shaped.append((q, cts))
        pts = model.curve_points([(q, ct) for q, cts in shaped for ct in cts])
        if len(pts) >= 2 and -4.2 <= model.fitted_slope(pts) <= -3.4:
            break
    for g in refs + targets:
        series[g] = shaped
    return assemble(rng, parts)


def fam_t2(rng):
    """Trap T2: an NTC well earlier than 10.00 (2.6: at or below the cut-off contaminates)."""
    parts = _neutral(rng)
    refs, targets, samples, cal, series, reps_map, ntc = parts
    genes = refs + targets
    for g in rng.sample(genes, rng.randint(1, len(genes))):
        ntc[g] = [ct2(rng.uniform(5.0, 9.99))] + ["Undetermined"] * rng.randint(0, 2)
    return assemble(rng, parts)


FAMILIES = {
    "broad": fam_broad, "D1": fam_d1, "D2": fam_d2, "D4": fam_d4,
    "D5": fam_d5, "D6": fam_d6, "D7": fam_d7, "T1": fam_t1, "T2": fam_t2,
}
TRAP_FAMILY = {"T1": {"T1"}, "T2": {"T2"}}


def draw(family, rng, tries=400):
    for _ in range(tries):
        plate = FAMILIES[family](rng)
        if not model.within_limits(plate):
            continue
        if model.trap_inputs(plate) != TRAP_FAMILY.get(family, set()):
            continue
        return plate
    raise RuntimeError(f"family {family}: no plate within limits")


def cases(seed, per_family):
    rng = random.Random(seed)
    out = []
    for fam in FAMILIES:
        for i in range(per_family):
            p = draw(fam, rng)
            p["plate"] = f"P{fam}{i:02d}" if rng.random() < 0.5 else p["plate"]
            out.append((fam, p))
    return out
