"""Job generators for tbrain-crop-hail-loss-adjustment (authoring only, never shipped).

Families: `broad` (trap-free, whole section 1 range), one per departure D1-D8, one per trap
TA (sample plots that are not hail-thinned but lost plants) and TB (replantings of 0.1 to
9.9 acres). Trap inputs appear only in their own family; `trap_inputs(job)` says which a
job carries. `fuzz_job(rng)` draws anything section 1 allows, traps included.
"""

import importlib.util
import sys as _sys
_sys.dont_write_bytecode = True
import random
import string
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-crop-hail-loss-adjustment"

_spec = importlib.util.spec_from_file_location("hail_model", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model)

STAGES = list(model.STAGE_SHARE)
OPTIONS = list(model.OPTIONS)
CODE_CHARS = string.ascii_letters + string.digits + " -_/#.'\"\\é"


# ---------------------------------------------------------------- building blocks

def code(rng, taken):
    while True:
        n = rng.choice([1, 2, 3, 5, 8, 12, 16])
        c = "".join(rng.choice(CODE_CHARS) for _ in range(n))
        if c not in taken:
            taken.add(c)
            return c


def leaf(rng):
    r = rng.random()
    if r < 0.15:
        return 0
    if r < 0.2:
        return 1000
    return rng.randint(0, 1000)


def plot_thinned(rng, stand=None):
    stand = stand or rng.randint(20, 200)
    lo = -(-stand // 10)
    dead = rng.choice([lo, stand, rng.randint(lo, stand), rng.randint(lo, min(stand, 3 * lo))])
    return [stand, dead, leaf(rng)]


def plot_clean(rng):
    return [rng.randint(20, 200), 0, leaf(rng)]


def silent_figure(stand, dead):
    return model.rounded(1000 * dead, stand)


def plot_silent(rng, band):
    """A plot that is not hail-thinned but lost plants, its figure in band (lo, hi) tenths."""
    lo, hi = band
    for _ in range(10000):
        stand = rng.randint(20, 200)
        dead = rng.randint(1, stand)
        if 10 * dead < stand and lo <= silent_figure(stand, dead) < hi:
            return [stand, dead, leaf(rng)]
    raise RuntimeError(band)


def trap_free_plot(rng, thinned_share=0.6):
    return plot_thinned(rng) if rng.random() < thinned_share else plot_clean(rng)


def acres(rng):
    r = rng.random()
    if r < 0.05:
        return 10
    if r < 0.1:
        return 50000
    if r < 0.5:
        return rng.randint(10, 2000)
    return rng.randint(10, 50000)


def per_acre(rng):
    r = rng.random()
    if r < 0.05:
        return 10
    if r < 0.1:
        return 2000
    return rng.randint(10, 2000)


def replanted_trap_free(rng, a):
    if a >= 100 and rng.random() < 0.3:
        return rng.choice([100, a, rng.randint(100, a)])
    return 0


def field(rng, taken, plots, **kw):
    a = kw.pop("acres", None) or acres(rng)
    f = {
        "field": code(rng, taken),
        "acres": a,
        "per_acre": kw.pop("per_acre", None) or per_acre(rng),
        "deductible": kw.pop("deductible", None) or rng.choice(OPTIONS),
        "stage": kw.pop("stage", None) or rng.choice(STAGES),
        "replanted": kw.pop("replanted") if "replanted" in kw else replanted_trap_free(rng, a),
        "plots": plots,
    }
    assert not kw, kw
    return f


def trap_free_field(rng, taken, n_plots=None, **kw):
    n = n_plots or rng.choice([1, 2, 4, 8, rng.randint(1, 40)])
    share = rng.choice([0.2, 0.5, 0.8, 1.0])
    return field(rng, taken, [trap_free_plot(rng, share) for _ in range(n)], **kw)


def job(claims):
    return {"claims": claims}


def claims_of(rng, make_fields, n_claims=None):
    numbers = set()
    out = []
    for _ in range(n_claims or rng.randint(1, 3)):
        out.append({"claim": code(rng, numbers), "fields": make_fields(set())})
    return out


# ---------------------------------------------------------------- families

def fam_broad(rng):
    return job(claims_of(rng, lambda t: [trap_free_field(rng, t) for _ in range(rng.randint(1, 6))],
                         rng.randint(1, 4)))


def fam_d1(rng):
    """3.3: averages over all plots; clean plots (no figure) sit beside thinned ones."""
    def fields(t):
        out = []
        for _ in range(rng.randint(1, 4)):
            n = rng.randint(2, 12)
            plots = [plot_thinned(rng) for _ in range(rng.randint(1, n - 1))]
            plots += [[rng.randint(20, 200), 0, rng.choice([0, 0, leaf(rng)])] for _ in range(n - len(plots))]
            rng.shuffle(plots)
            out.append(field(rng, t, plots, deductible="full", replanted=0))
        return out
    return job(claims_of(rng, fields))


def fam_d2(rng):
    """4.3: the R4 row of the chart."""
    def fields(t):
        return [field(rng, t, [[rng.randint(20, 200), 0, rng.randint(300, 1000)] for _ in range(rng.randint(1, 6))],
                      stage="R4", deductible="full", replanted=0) for _ in range(rng.randint(1, 4))]
    return job(claims_of(rng, fields))


def fam_d3(rng):
    """4.2: leaf loss on the surviving stand only."""
    def fields(t):
        return [field(rng, t, [[s, rng.randint(-(-s // 10), s // 2), rng.randint(200, 1000)]
                               for s in (rng.randint(20, 200) for _ in range(rng.randint(1, 8)))],
                      stage=rng.choice(["VT", "R2", "V14"]), deductible="full", replanted=0)
                for _ in range(rng.randint(1, 4))]
    return job(claims_of(rng, fields))


def fam_d4(rng):
    """1.1, 5.3: the indemnity rounded to the cent, half up."""
    def fields(t):
        return [trap_free_field(rng, t, deductible="full", acres=rng.randint(10, 5000),
                                per_acre=rng.randint(10, 2000), replanted=0)
                for _ in range(rng.randint(3, 8))]
    return job(claims_of(rng, fields))


def heavy_field(rng, t, **kw):
    plots = [[s, rng.randint(s // 2, s), rng.randint(500, 1000)] for s in (rng.randint(20, 200) for _ in range(rng.randint(1, 6)))]
    return field(rng, t, plots, **kw)


def fam_d5(rng):
    """5.2: the vanishing deductible never pays more than the loss."""
    def fields(t):
        return [heavy_field(rng, t, deductible="vanishing", replanted=0) for _ in range(rng.randint(1, 4))]
    return job(claims_of(rng, fields))


def fam_d6(rng):
    """5.1: a loss from 5.0 to 7.9 per cent pays nothing (full option, VT stage: loss = defoliation)."""
    def fields(t):
        out = []
        for _ in range(rng.randint(1, 4)):
            target = rng.randint(50, 79)
            n = rng.randint(1, 5)
            leaves = [target] * n
            plots = [[rng.randint(20, 200), 0, v] for v in leaves]
            out.append(field(rng, t, plots, stage="VT", deductible="full", replanted=0,
                             acres=rng.randint(1000, 50000), per_acre=rng.randint(200, 2000)))
        return out
    return job(claims_of(rng, fields))


def fam_d7(rng):
    """7.2: a claim total from 2,500 to 9,999 cents is not paid."""
    claims, numbers = [], set()
    for _ in range(rng.randint(1, 3)):
        for _ in range(100000):
            t = set()
            f = field(rng, t, [[100, rng.randint(10, 100), rng.randint(0, 1000)]], stage=rng.choice(STAGES),
                      deductible="full", replanted=0, acres=rng.randint(10, 150), per_acre=rng.randint(10, 120))
            total = model.claim({"claim": "x", "fields": [f]})["total"]
            if 2500 <= total <= 9999:
                break
        claims.append({"claim": code(rng, numbers), "fields": [f]})
    return job(claims)


def fam_d8(rng):
    """5.2: the straight deductible is 10.0 per cent."""
    def fields(t):
        return [trap_free_field(rng, t, deductible="straight", replanted=0) for _ in range(rng.randint(2, 6))]
    return job(claims_of(rng, fields))


def fam_ta(rng):
    """Trap TA: plots that are not hail-thinned but lost plants, figures across 0-9.9 per cent."""
    def fields(t):
        out = []
        for _ in range(rng.randint(1, 4)):
            plots = [plot_silent(rng, (50, 80)) for _ in range(rng.randint(1, 3))]
            plots += [plot_silent(rng, rng.choice([(1, 50), (80, 100), (50, 80)])) for _ in range(rng.randint(0, 3))]
            plots += [trap_free_plot(rng) for _ in range(rng.randint(0, 4))]
            rng.shuffle(plots)
            out.append(field(rng, t, plots, replanted=0))
        return out
    return job(claims_of(rng, fields))


def fam_tb(rng):
    """Trap TB: replantings of 0.1 to 9.9 acres, most priced from 2,500 to 9,999 cents."""
    def fields(t):
        out = []
        for _ in range(rng.randint(1, 4)):
            r = rng.choice([rng.randint(9, 33), rng.randint(9, 33), rng.randint(1, 99)])
            a = max(r, acres(rng))
            out.append(trap_free_field(rng, t, acres=a, replanted=r))
        return out
    return job(claims_of(rng, fields))


FAMILIES = {
    "broad": fam_broad,
    "D1": fam_d1, "D2": fam_d2, "D3": fam_d3, "D4": fam_d4,
    "D5": fam_d5, "D6": fam_d6, "D7": fam_d7, "D8": fam_d8,
    "TA": fam_ta, "TB": fam_tb,
}
TRAP_FAMILIES = {"TA", "TB"}


def trap_inputs(j):
    """Which trap inputs a job carries: TA (a plot not hail-thinned that lost plants),
    TB (a replanting of 0.1 to 9.9 acres)."""
    found = set()
    for c in j["claims"]:
        for f in c["fields"]:
            if 1 <= f["replanted"] <= 99:
                found.add("TB")
            for stand, dead, _ in f["plots"]:
                if dead > 0 and 10 * dead < stand:
                    found.add("TA")
    return found


def fuzz_job(rng):
    """Anything section 1 allows, trap inputs included."""
    numbers = set()
    claims = []
    for _ in range(rng.choice([1, 1, 2, 5, rng.randint(1, 50)])):
        t = set()
        fields = []
        for _ in range(rng.choice([1, 2, 5, rng.randint(1, 30)])):
            n = rng.choice([1, 3, 10, rng.randint(1, 40)])
            plots = []
            for _ in range(n):
                k = rng.random()
                if k < 0.35:
                    plots.append(plot_thinned(rng))
                elif k < 0.55:
                    plots.append(plot_clean(rng))
                else:
                    s = rng.randint(20, 200)
                    plots.append([s, rng.randint(0, max(0, (s - 1) // 10)), leaf(rng)])
            small = rng.random() < 0.3
            a = rng.randint(10, 120) if small else acres(rng)
            r = rng.choice([0, 0, rng.randint(0, min(a, 99)), rng.randint(0, a), a])
            fields.append(field(rng, t, plots, replanted=r, acres=a,
                                per_acre=rng.randint(10, 60) if small else None))
        claims.append({"claim": code(rng, numbers), "fields": fields})
    return {"claims": claims}


def draw(seed, per_family):
    """[(family, job)] for a seed, every job checked against the limits and its trap inputs."""
    rng = random.Random(seed)
    out = []
    for fam, fn in FAMILIES.items():
        for _ in range(per_family):
            j = fn(rng)
            bad = model.within_limits(j)
            assert not bad, (fam, bad)
            want = {fam} if fam in TRAP_FAMILIES else set()
            assert trap_inputs(j) == want, (fam, trap_inputs(j))
            out.append((fam, j))
    return out


if __name__ == "__main__":
    import json
    cases = draw(int(sys.argv[1]) if len(sys.argv) > 1 else 1, 2)
    print(json.dumps(cases[0][1])[:400])
    print(len(cases), "jobs")
