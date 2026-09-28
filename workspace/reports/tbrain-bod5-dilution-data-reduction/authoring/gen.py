"""Seeded batch generator for SOP WQ-14 (authoring only; never shipped in the task).

Every batch keeps within SOP section 1 (checked with model.limits_ok). Families:
broad (trap-free), one per departure D1-D8 (trap-free), and one per trap T1, T2
(each carrying only its own trap input).
"""

import importlib.util
import random
from pathlib import Path

TASK = Path(__file__).resolve().parents[3] / "tasks" / "tbrain-bod5-dilution-data-reduction"
_spec = importlib.util.spec_from_file_location("bod_model", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model)


def h(x):
    return round(x, 2)


def ini(rng):
    return h(rng.uniform(6.0, 9.5))


def bottle(rng, kind, sample_ml=None, seed_ml=None, sample_range=(0.5, 300.0)):
    """kind: usable | short | spent | shortneg."""
    if sample_ml is None:
        sample_ml = h(rng.uniform(*sample_range))
    if seed_ml is None:
        seed_ml = 0.0 if rng.random() < 0.3 else h(rng.uniform(0.0, 3.0))
    seed_ml = min(seed_ml, h(300.0 - sample_ml))
    i = ini(rng)
    if kind == "usable":
        f = h(rng.uniform(1.21, i - 2.51))
    elif kind == "short":
        f = h(rng.uniform(max(1.21, i - 2.49), i))
    elif kind == "shortneg":
        f = h(rng.uniform(i, 9.5))
    elif kind == "spent":
        f = h(rng.uniform(0.0, 1.19))
    else:
        raise ValueError(kind)
    return {"sample_ml": sample_ml, "seed_ml": seed_ml, "do_initial": i, "do_final": f}


def control(rng, kind, cid):
    i = ini(rng)
    if kind == "usable":
        seed = h(rng.uniform(9.0, 30.0))
        top = min(0.3 * seed, i - 1.21)
        dep = h(rng.uniform(2.51, top))
    elif kind == "short":
        seed = h(rng.uniform(5.0, 30.0))
        dep = h(rng.uniform(0.0, min(2.49, 0.3 * seed)))
    elif kind == "spent":  # oxygen ran out: needs depletion above initial - 1.2 within 0.3 * seed
        seed = h(rng.uniform(i / 0.3 + 0.1, 30.0)) if i / 0.3 + 0.1 < 30.0 else 30.0
        dep = h(rng.uniform(i - 1.19, min(i, 0.3 * seed)))
    else:
        raise ValueError(kind)
    f = h(i - dep)
    return {"id": cid, "seed_ml": seed, "do_initial": i, "do_final": f}


def blank(rng, bid, dep=None):
    i = ini(rng)
    if dep is None:
        dep = rng.uniform(-0.5, 1.0)
    f = h(min(9.5, i - dep))
    return {"id": bid, "do_initial": i, "do_final": f}


def check(rng):
    bots = []
    for k in range(rng.randint(1, 3)):
        kind = "usable" if k == 0 else rng.choice(["usable", "usable", "short", "spent"])
        sm = h(rng.uniform(2.0, 12.0))
        b = bottle(rng, kind, sample_ml=sm, seed_ml=h(rng.uniform(0.0, 3.0)))
        if kind == "usable" and rng.random() < 0.7:  # aim near 200 mg/L
            target = rng.uniform(150, 250) * sm / 300.0 + 0.1 * b["seed_ml"]
            i = b["do_initial"]
            f = h(i - target)
            if 1.21 <= f <= i - 2.51:
                b["do_final"] = f
        bots.append(b)
    rng.shuffle(bots)
    return {"id": "GGA", "bottles": bots}


def controls(rng, need_usable=True, n=None):
    n = n or rng.randint(1, 6)
    kinds = [rng.choice(["usable", "usable", "short", "spent"]) for _ in range(n)]
    if need_usable and "usable" not in kinds:
        kinds[rng.randrange(n)] = "usable"
    if not need_usable:
        kinds = [rng.choice(["short", "spent"]) for _ in range(n)]
    return [control(rng, k, f"SC{j + 1}") for j, k in enumerate(kinds)]


def measured_sample(rng, sid, nb=None):
    nb = nb or rng.randint(1, 5)
    kinds = [rng.choice(["usable", "short", "spent", "shortneg"]) for _ in range(nb)]
    kinds[rng.randrange(nb)] = "usable"
    return {"id": sid, "duplicate_of": None, "bottles": [bottle(rng, k) for k in kinds]}


def bound_sample(rng, sid, which=None):
    nb = rng.randint(1, 5)
    which = which or rng.choice(["short", "spent", "mixed"])
    if which == "spent":
        kinds = ["spent"] * nb
    elif which == "short":
        kinds = [rng.choice(["short", "shortneg"]) for _ in range(nb)]
    else:
        kinds = [rng.choice(["short", "spent", "shortneg"]) for _ in range(max(nb, 2))]
        kinds[0], kinds[1] = "short", "spent"
        rng.shuffle(kinds)
    return {"id": sid, "duplicate_of": None, "bottles": [bottle(rng, k) for k in kinds]}


def sid(rng, used):
    while True:
        s = rng.choice(["S", "WW", "EFF", "INF", "MH"]) + "-" + str(rng.randint(1, 99999))
        if s not in used:
            used.add(s)
            return s


def base(rng, name, need_usable_controls=True):
    return {
        "batch": name,
        "seed_controls": controls(rng, need_usable_controls),
        "blanks": [blank(rng, f"DW{k + 1}") for k in range(rng.randint(1, 4))],
        "check": check(rng),
        "samples": [],
    }


def add_samples(rng, b, n, measured_only_dups=True, bound_share=0.3):
    used = {s["id"] for s in b["samples"]}
    for _ in range(n):
        s = bound_sample(rng, sid(rng, used)) if rng.random() < bound_share else measured_sample(rng, sid(rng, used))
        b["samples"].append(s)


def add_dups(rng, b, k, need_bound=False):
    """Add k duplicates of existing non-duplicate samples."""
    used = {s["id"] for s in b["samples"]}
    parents = [s for s in b["samples"] if s["duplicate_of"] is None]
    for _ in range(k):
        p = rng.choice(parents)
        p_measured = any(model.usable(x) for x in p["bottles"])
        if need_bound:
            d = bound_sample(rng, sid(rng, used)) if (p_measured or rng.random() < 0.5) else measured_sample(rng, sid(rng, used))
        else:
            if not p_measured:
                continue
            d = measured_sample(rng, sid(rng, used))
            if rng.random() < 0.5:  # a close duplicate
                d["bottles"] = [dict(x, do_final=h(min(x["do_initial"] - 2.51, max(1.21, x["do_final"] + rng.uniform(-0.3, 0.3))))) if model.usable(x) else dict(x) for x in p["bottles"]]
                if not any(model.usable(x) for x in d["bottles"]):
                    d = measured_sample(rng, d["id"])
        d["duplicate_of"] = p["id"]
        b["samples"].insert(rng.randint(0, len(b["samples"])), d)


def has_measured(b, s):
    return any(model.usable(x) for x in s["bottles"])


def traps_in(b):
    out = set()
    if not any(model.usable(c) for c in b["seed_controls"]):
        out.add("T1")
    byid = {s["id"]: s for s in b["samples"]}
    for s in b["samples"]:
        of = s.get("duplicate_of")
        if of is not None and not (has_measured(b, s) and has_measured(b, byid[of])):
            out.add("T2")
    return out


# ---- families ----

def fam_broad(rng, name):
    b = base(rng, name)
    add_samples(rng, b, rng.randint(1, 30))
    add_dups(rng, b, rng.randint(0, 5))
    return b


def fam_d1(rng, name):  # 2.4 usable needs 2.50: short bottles with depletion 2.0-2.5 beside usable ones
    b = base(rng, name)
    used = set()
    for _ in range(rng.randint(1, 4)):
        s = measured_sample(rng, sid(rng, used), nb=rng.randint(2, 5))
        x = s["bottles"][0]
        i = x["do_initial"]
        x["do_final"] = h(rng.uniform(max(1.21, i - 2.49), i - 2.01))
        rng.shuffle(s["bottles"])
        if not any(model.usable(y) for y in s["bottles"]):
            s["bottles"].append(bottle(rng, "usable"))
        b["samples"].append(s)
    return b


def fam_d2(rng, name):  # 2.3 spent below 1.20: final DO 1.00-1.19 with large depletion
    b = base(rng, name)
    used = set()
    for _ in range(rng.randint(1, 4)):
        s = measured_sample(rng, sid(rng, used), nb=rng.randint(2, 5))
        s["bottles"][0]["do_final"] = h(rng.uniform(1.0, 1.19))
        rng.shuffle(s["bottles"])
        if not any(model.usable(y) for y in s["bottles"]):
            s["bottles"].append(bottle(rng, "usable"))
        b["samples"].append(s)
    return b


def fam_d3(rng, name):  # 3.2 mean seed rate of usable controls (short controls present)
    b = base(rng, name)
    n = rng.randint(2, 6)
    kinds = ["usable", "short"] + [rng.choice(["usable", "short", "spent"]) for _ in range(n - 2)]
    rng.shuffle(kinds)
    b["seed_controls"] = [control(rng, k, f"SC{j + 1}") for j, k in enumerate(kinds)]
    add_samples(rng, b, rng.randint(1, 5), bound_share=0.0)
    for s in b["samples"]:
        for x in s["bottles"]:
            x["seed_ml"] = min(h(rng.uniform(0.5, 3.0)), h(300 - x["sample_ml"]))
    return b


def fam_d4(rng, name):  # 4.1 correction removed before dividing
    b = base(rng, name)
    used = set()
    for _ in range(rng.randint(1, 4)):
        s = measured_sample(rng, sid(rng, used))
        for x in s["bottles"]:
            x["sample_ml"] = h(rng.uniform(1.0, 150.0))
            x["seed_ml"] = h(rng.uniform(1.0, 3.0))
        b["samples"].append(s)
    return b


def fam_d5(rng, name):  # 5.3 less-than from the bottle holding the most sample
    b = base(rng, name)
    used = set()
    for _ in range(rng.randint(1, 4)):
        s = bound_sample(rng, sid(rng, used), which=rng.choice(["short", "mixed"]))
        if len(s["bottles"]) < 2:
            s["bottles"].append(bottle(rng, "short"))
        b["samples"].append(s)
    return b


def fam_d6(rng, name):  # 7.1 largest blank depletion
    b = base(rng, name)
    b["blanks"] = [blank(rng, "DW1", rng.uniform(0.25, 1.0))] + [blank(rng, f"DW{k + 2}", rng.uniform(-0.5, 0.15)) for k in range(rng.randint(1, 3))]
    rng.shuffle(b["blanks"])
    add_samples(rng, b, rng.randint(1, 3))
    return b


def fam_d7(rng, name):  # 6.1 RPD over the mean of two measured BODs
    b = base(rng, name)
    add_samples(rng, b, rng.randint(1, 4), bound_share=0.0)
    add_dups(rng, b, rng.randint(1, 3))
    return b


def fam_d8(rng, name):  # 1.2 three significant figures (values of 1 to 5,700 mg/L)
    b = base(rng, name)
    used = set()
    for _ in range(rng.randint(2, 6)):
        s = measured_sample(rng, sid(rng, used), nb=1)
        s["bottles"][0]["sample_ml"] = h(rng.choice([rng.uniform(0.5, 3.0), rng.uniform(3.0, 30.0), rng.uniform(100.0, 300.0)]))
        s["bottles"][0]["seed_ml"] = min(s["bottles"][0]["seed_ml"], h(300 - s["bottles"][0]["sample_ml"]))
        b["samples"].append(s)
    return b


def fam_t1(rng, name):  # trap T1: no usable seed control (2.5: every control is a reference control)
    b = base(rng, name, need_usable_controls=False)
    b["seed_controls"] = controls(rng, need_usable=False, n=rng.randint(2, 6))
    cs = b["seed_controls"]
    pooled = sum(model.depletion(c) for c in cs) / sum(c["seed_ml"] for c in cs)
    if abs(pooled - model.seed_factor(cs)) <= 1e-4 * max(pooled, 1e-3):
        return {"batch": name, "samples": []}  # rejected by valid(): pooled and mean rate must differ
    add_samples(rng, b, rng.randint(1, 5))
    for s in b["samples"]:
        for x in s["bottles"]:
            x["seed_ml"] = min(h(rng.uniform(0.5, 3.0)), h(300 - x["sample_ml"]))
    return b


def fam_t2(rng, name):  # trap T2: a duplicate pair with a bound on one or both sides
    b = base(rng, name)
    add_samples(rng, b, rng.randint(1, 4), bound_share=0.5)
    add_dups(rng, b, rng.randint(1, 3), need_bound=True)
    return b


FAMILIES = {
    "broad": fam_broad, "D1": fam_d1, "D2": fam_d2, "D3": fam_d3, "D4": fam_d4, "D5": fam_d5,
    "D6": fam_d6, "D7": fam_d7, "D8": fam_d8, "T1": fam_t1, "T2": fam_t2,
}
TRAPS = {"T1", "T2"}


def valid(b):
    if not b["samples"]:
        return False
    if not (1 <= len(b["samples"]) <= 40):
        return False
    return model.limits_ok(b)


def batches(seed, per_family, families=None):
    rng = random.Random(seed)
    out = []
    for fam, gen in FAMILIES.items():
        if families and fam not in families:
            continue
        n = tries = 0
        while n < per_family:
            tries += 1
            assert tries < 5000, fam
            b = gen(rng, f"B{rng.randint(1000, 999999)}")
            if not valid(b):
                continue
            want = {fam} if fam in TRAPS else set()
            if traps_in(b) != want:
                continue
            out.append((fam, b))
            n += 1
    return out
