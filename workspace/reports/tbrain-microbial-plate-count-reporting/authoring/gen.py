"""Seeded batch generator for tbrain-microbial-plate-count-reporting (authoring only, never shipped).

One family per departure (D1-D8), one per trap (T1, T2) and a trap-free `broad` family. Each
family function takes a random.Random and returns one batch inside the SOP 1.3 limits. Trap
inputs appear only in their own family (`trap_inputs` detects them). The `*_neutral` trap
families avoid every departure's inputs, so the unpatched package must already match the model
there (the trap's silent/kept step is today's step).
"""

import random
import sys
from pathlib import Path

TASK = Path(__file__).resolve().parents[3] / "tasks" / "tbrain-microbial-plate-count-reporting"
sys.path.insert(0, str(TASK / "solution"))
import model  # noqa: E402

VOLS = (1.0, 0.1)


def countable(rng, lo=20, hi=300):
    return rng.randint(lo, hi)


def sparse(rng, zero_ok=True):
    return rng.randint(0 if zero_ok else 1, 19)


def crowded(rng, null_ok=True):
    if null_ok and rng.random() < 0.35:
        return None
    return rng.randint(301, 5000)


def dil(step, volume, plates):
    return {"step": step, "volume": volume, "plates": plates}


def steps_run(rng, n, lo=0, hi=9, gaps=False):
    """n increasing steps; consecutive unless gaps."""
    if not gaps:
        start = rng.randint(lo, hi - n + 1)
        return list(range(start, start + n))
    while True:
        s = sorted(rng.sample(range(lo, hi + 1), n))
        if any(b - a > 1 for a, b in zip(s, s[1:])):
            return s


# ---------------------------------------------------------------- sample shapes (governed, trap-free)

def s_single_countable(rng, vol=None, lo=20, hi=300):
    """Countable plates at one dilution; the next step (if plated) holds no countable plate."""
    n = rng.randint(1, 4)
    steps = steps_run(rng, n)
    k = rng.randrange(n)
    dils = []
    for i, st in enumerate(steps):
        v = vol or rng.choice(VOLS)
        m = rng.randint(1, 4)
        if i < k:
            plates = [crowded(rng) if rng.random() < 0.8 else sparse(rng) for _ in range(m)]
        elif i == k:
            plates = [countable(rng, lo, hi) if j == 0 or rng.random() < 0.6 else
                      crowded(rng) for j in range(m)]
        else:
            plates = [sparse(rng) for _ in range(m)]
        dils.append(dil(st, v, plates))
    if k > 0 and any(model.is_countable(r) for r in dils[k - 1]["plates"]):
        return s_single_countable(rng, vol, lo, hi)
    return dils


def s_pair_countable(rng, vol=None, lo=20, hi=300):
    """Countable plates at two consecutive steps (both plated, listed together)."""
    n = rng.randint(2, 5)
    steps = steps_run(rng, n)
    k = rng.randrange(n - 1)
    dils = []
    for i, st in enumerate(steps):
        v = vol or rng.choice(VOLS)
        m = rng.randint(1, 4)
        if i < k:
            plates = [crowded(rng) for _ in range(m)]
        elif i in (k, k + 1):
            plates = [countable(rng, lo, hi) if j == 0 or rng.random() < 0.6 else
                      crowded(rng) for j in range(m)]
        else:
            plates = [sparse(rng) if rng.random() < 0.7 else countable(rng, lo, hi) for _ in range(m)]
        dils.append(dil(st, v, plates))
    return dils


def s_sparse(rng, vol=None, colony=True, multi=False):
    """Every plate sparse; with a colony somewhere (or none)."""
    n = rng.randint(2 if multi else 1, 5)
    steps = steps_run(rng, n, gaps=rng.random() < 0.3 and n > 1)
    dils = []
    for st in steps:
        m = rng.randint(1, 4)
        dils.append(dil(st, vol or rng.choice(VOLS), [sparse(rng) if colony else 0 for _ in range(m)]))
    if colony:
        if not any(r for d in dils for r in d["plates"]):
            dils[rng.randrange(n)]["plates"][0] = rng.randint(1, 19)
        if multi and sum(1 for d in dils if any(d["plates"])) < 2:
            for d in dils[:2]:
                d["plates"][0] = rng.randint(1, 19)
    return dils


def s_crowded(rng, vol=None, null_ok=True, multi=False):
    n = rng.randint(2 if multi else 1, 5)
    steps = steps_run(rng, n, gaps=rng.random() < 0.3 and n > 1)
    return [dil(st, vol or rng.choice(VOLS), [crowded(rng, null_ok) for _ in range(rng.randint(1, 4))])
            for st in steps]


def s_mixed(rng, vol=None, null_ok=True):
    """No countable plate; crowded at the low steps, sparse (with colonies) further on."""
    n = rng.randint(2, 6)
    steps = steps_run(rng, n, gaps=rng.random() < 0.4)
    k = rng.randint(1, n - 1)  # dilutions [0, k) crowded, [k, n) sparse
    dils = []
    for i, st in enumerate(steps):
        m = rng.randint(1, 4)
        v = vol or rng.choice(VOLS)
        if i < k:
            plates = [crowded(rng, null_ok) for _ in range(m)]
        else:
            plates = [sparse(rng) for _ in range(m)]
        dils.append(dil(st, v, plates))
    if not any(r for d in dils[k:] for r in d["plates"]):
        dils[k]["plates"][0] = rng.randint(1, 19)
    return dils


def s_gap(rng, vol=None, lo=20, hi=300, null_ok=True):
    """Countable plates at the first counted dilution and at a later listed one that is not a tenth of it."""
    shape = rng.choice(["skip", "between"])
    if shape == "skip":  # list-next is two or more steps on
        a = rng.randint(0, 7)
        b = rng.randint(a + 2, 9)
        steps = [a, b]
        more = [s for s in range(b + 1, 10)]
        steps += sorted(rng.sample(more, rng.randint(0, min(2, len(more)))))
        pre = [s for s in range(0, a)]
        pre = sorted(rng.sample(pre, rng.randint(0, min(2, len(pre)))))
        steps = pre + steps
        first = len(pre)
        cnt = {first, first + 1}
        empty_next = set()
    else:  # step+1 plated without a countable plate, a later step with one
        a = rng.randint(0, 7)
        b = rng.randint(a + 2, 9)
        steps = [a, a + 1, b] if b > a + 1 else [a, a + 1]
        first = 0
        cnt = {0, 2}
        empty_next = {1}
    dils = []
    for i, st in enumerate(steps):
        m = rng.randint(1, 4)
        v = vol or rng.choice(VOLS)
        if i < first:
            plates = [crowded(rng, null_ok) for _ in range(m)]
        elif i in cnt:
            plates = [countable(rng, lo, hi) if j == 0 or rng.random() < 0.6 else
                      crowded(rng, null_ok) for j in range(m)]
        elif i in empty_next:
            plates = [sparse(rng) if rng.random() < 0.5 else crowded(rng, null_ok) for _ in range(m)]
        else:
            plates = [sparse(rng) for _ in range(m)]
        dils.append(dil(st, v, plates))
    return dils


# ---------------------------------------------------------------- trap detection

def _first_counted(dils):
    for i, d in enumerate(dils):
        if any(model.is_countable(r) for r in d["plates"]):
            return i
    return None


def is_t1(dils):
    """Countable plates at a listed dilution after the first counted one that is not a tenth of it,
    where the list-next or the next-with-a-countable-plate reading would pool it."""
    i = _first_counted(dils)
    if i is None:
        return False
    later = [d for d in dils[i + 1:] if any(model.is_countable(r) for r in d["plates"])]
    nxt_listed = dils[i + 1] if i + 1 < len(dils) else None
    step = dils[i]["step"]
    if nxt_listed is not None and nxt_listed["step"] != step + 1 and any(model.is_countable(r) for r in nxt_listed["plates"]):
        return True
    return bool(later) and later[0]["step"] != step + 1


def is_t2(dils):
    """A counted dilution holds a sparse (or empty) plate: a counted plate that is not countable."""
    return any(model.is_sparse(r) for d in model.counted_dilutions(dils) for r in d["plates"])


def trap_inputs(batch):
    out = set()
    for s in batch["samples"]:
        if is_t1(s["dilutions"]):
            out.add("T1")
        if is_t2(s["dilutions"]):
            out.add("T2")
    return out


# ---------------------------------------------------------------- batches

def batch_of(rng, makers, n_lo=4, n_hi=12, unit=None):
    n = rng.randint(n_lo, n_hi)
    samples = []
    for i in range(n):
        dils = rng.choice(makers)(rng)
        samples.append({"id": f"S{rng.randint(0, 99999):05d}{chr(65 + i % 26)}", "unit": unit or rng.choice(["g", "mL"]),
                        "dilutions": dils})
    ids = set()
    for s in samples:
        while s["id"] in ids:
            s["id"] = f"S{rng.randint(0, 99999):05d}{chr(65 + rng.randrange(26))}"
        ids.add(s["id"])
    return {"batch": f"B{rng.randint(1000, 9999)}", "samples": samples}


def half_sample(rng):
    """One countable plate whose result lands on an exact half at the second figure (even second digit)."""
    reading = rng.choice([105, 125, 145, 165, 185, 205, 225, 245, 265, 285])
    st = rng.randint(0, 9)
    return [dil(st, rng.choice(VOLS), [reading])]


def fam_broad(rng):
    return batch_of(rng, [s_single_countable, s_pair_countable, lambda r: s_sparse(r),
                          lambda r: s_sparse(r, colony=False), lambda r: s_crowded(r), lambda r: s_mixed(r)], 8, 20)


def fam_D1(rng):  # 2.4 countable range 20-300
    return batch_of(rng, [lambda r: s_single_countable(r, lo=20, hi=24), lambda r: s_single_countable(r, lo=251, hi=300),
                          lambda r: s_pair_countable(r, lo=251, hi=300)])


def fam_D2(rng):  # 2.7 / 4.1 pooling two consecutive dilutions
    return batch_of(rng, [s_pair_countable])


def fam_D3(rng):  # 2.2 plated amount = volume x dilution
    return batch_of(rng, [lambda r: s_single_countable(r, vol=0.1), lambda r: s_sparse(r, vol=0.1)])


def fam_D4(rng):  # 1.2 exact half goes up
    return batch_of(rng, [half_sample])


def fam_D5(rng):  # 4.3 less-than at the first dilution
    return batch_of(rng, [lambda r: s_sparse(r, colony=False, multi=True)])


def fam_D6(rng):  # 4.4 greater-than at the last dilution holding a crowded plate, mixed samples included
    return batch_of(rng, [lambda r: s_crowded(r, null_ok=False, multi=True), lambda r: s_mixed(r, null_ok=False)])


def fam_D7(rng):  # 4.2 estimate from the first dilution holding a colony
    return batch_of(rng, [lambda r: s_sparse(r, multi=True)])


def fam_D8(rng):  # 2.5 too numerous to count is crowded
    def all_null(r):
        n = r.randint(1, 4)
        return [dil(st, r.choice(VOLS), [None] * r.randint(1, 4)) for st in steps_run(r, n)]
    return batch_of(rng, [all_null])


def fam_T1(rng):
    return batch_of(rng, [s_gap], 3, 8)


def s_with_sparse_counted(rng, vol=None, lo=20, hi=300, pair=None, null_ok=True):
    """Countable plates beside sparse or empty plates on the counted dilution(s)."""
    pair = rng.random() < 0.5 if pair is None else pair
    dils = s_pair_countable(rng, vol, lo, hi) if pair else s_single_countable(rng, vol, lo, hi)
    counted = model.counted_dilutions(dils)
    for d in counted:
        if len(d["plates"]) < 4 and (rng.random() < 0.7 or d is counted[0]):
            d["plates"].insert(rng.randint(0, len(d["plates"])), rng.choice([0, sparse(rng), 19]))
    if not null_ok:
        for d in dils:
            d["plates"] = [p if p is not None else 301 + rng.randint(0, 4000) for p in d["plates"]]
    if not is_t2(dils):
        return s_with_sparse_counted(rng, vol, lo, hi, pair, null_ok)
    return dils


def fam_T2(rng):
    return batch_of(rng, [s_with_sparse_counted], 3, 8)


# neutral trap variants: no input any departure touches (1.0 mL, readings countable only in 25-250,
# crowded only above 300 and never null, no exact half), used only by check_departures.py
def on_half(sample):
    """The model's exact result lands on a half at the second significant figure."""
    from fractions import Fraction
    _kind, value = model.result(sample)
    power = 0
    while value >= Fraction(10) ** (power + 1):
        power += 1
    while value < Fraction(10) ** power:
        power -= 1
    scaled = value / Fraction(10) ** (power - 1)
    return scaled - int(scaled) == Fraction(1, 2)


def no_halves(batch):
    batch["samples"] = [s for s in batch["samples"] if not on_half(s)] or batch["samples"][:0]
    return batch


def fam_T1_neutral(rng):
    while True:
        b = batch_of(rng, [lambda r: s_gap(r, vol=1.0, lo=25, hi=250, null_ok=False)], 3, 8)
        for s in b["samples"]:
            for d in s["dilutions"]:
                d["plates"] = [p for p in d["plates"] if p is None or not (20 <= p < 25 or 250 < p <= 300)] or [300 + 1]
        b = no_halves(b)
        if b["samples"] and all(is_t1(s["dilutions"]) for s in b["samples"]):
            return b


def fam_T2_neutral(rng):
    while True:
        b = no_halves(batch_of(rng, [lambda r: s_with_sparse_counted(r, vol=1.0, lo=25, hi=250, pair=False,
                                                                     null_ok=False)], 3, 8))
        if b["samples"] and all(is_t2(s["dilutions"]) and not is_t1(s["dilutions"]) for s in b["samples"]):
            return b


FAMILIES = {
    "broad": fam_broad, "D1": fam_D1, "D2": fam_D2, "D3": fam_D3, "D4": fam_D4, "D5": fam_D5,
    "D6": fam_D6, "D7": fam_D7, "D8": fam_D8, "T1": fam_T1, "T2": fam_T2,
}
TRAP_FAMILIES = {"T1", "T2"}
