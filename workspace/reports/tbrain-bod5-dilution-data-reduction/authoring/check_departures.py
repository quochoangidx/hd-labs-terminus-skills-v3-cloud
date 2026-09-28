"""Departure/trap checks: each revert_Dk variant (Oracle with one departure put back) differs from the model on its
family; the shipped package differs on every departure family; the shipped package matches the model on each trap's
silent value (T1: seed_factor; T2: rpd on duplicates with a bound, on inputs no departure confounds);
each trap's natural fix fails only its trap family. Writes ../receipts/departure-trap-checks.json"""
import json, random
from pathlib import Path
import gen, fuzz, variants

def fam_stats(app, seed=11, per=30):
    s, _ = fuzz.run(app, seed, per)
    return {k: v["agree"] == v["total"] for k, v in s.items()}

def unconfounded_t2(rng, name):
    """T2 batches whose sample values no departure moves: unseeded bottles clear of every shipped/SOP threshold gap,
    bound samples of one spent bottle (a less-than bound carries the 2.50 constant, so it is left out), usable seed controls only."""
    def clean(kind):
        while True:
            b = gen.bottle(rng, kind, seed_ml=0.0)
            d, f = gen.model.depletion(b), b["do_final"]
            if 2.0 <= d < 2.5 or 1.0 <= f < 1.2:
                continue
            return b
    used = set()
    samples = []
    for k in range(rng.randint(2, 5)):
        if rng.random() < 0.5:
            s = {"id": gen.sid(rng, used), "duplicate_of": None, "bottles": [clean("spent")]}
        else:
            s = {"id": gen.sid(rng, used), "duplicate_of": None, "bottles": [clean("usable")]}
        samples.append(s)
    parents = list(samples)
    for p in parents[:2]:
        pm = gen.model.usable(p["bottles"][0])
        kind = "spent" if pm else rng.choice(["usable", "spent"])
        samples.append({"id": gen.sid(rng, used), "duplicate_of": p["id"], "bottles": [clean(kind)]})
    b = {"batch": name, "seed_controls": [gen.control(rng, "usable", "SC1")], "blanks": [gen.blank(rng, "DW1")],
         "check": gen.check(rng), "samples": samples}
    return b

def main():
    root = variants.build()
    rec = {"departures": {}, "traps": {}}
    shipped = fam_stats("shipped/app")
    rec["shipped_family_agreement"] = shipped
    for d in [f"D{k}" for k in range(1, 9)]:
        st = fam_stats(str(root / f"revert_{d}" / "app"))
        rec["departures"][d] = {"revert_variant_fails_own_family": not st[d], "shipped_fails_family": not shipped[d]}
    ship = fuzz.load_pkg("shipped/app")
    # T1 (governed by 2.5): shipped pools every control; the SOP takes the mean seed rate of every control
    t1 = [b for f, b in gen.batches(5, 60, {"T1"})]
    diff = sum(1 for b in t1 if abs(ship.reduce_batch(b)["seed_factor"] - gen.model.report(b)["seed_factor"]) > 1e-9)
    rec["traps"]["T1"] = {"kind": "governed definition hop (2.5 reference controls)", "shipped_differs_from_model_on_seed_factor": f"{diff}/{len(t1)}"}
    # T2 silent value: RPD of a duplicate pair with a bound
    rng = random.Random(9)
    n = eq2 = 0
    while n < 60:
        b = unconfounded_t2(rng, f"U{n}")
        if not gen.model.limits_ok(b) or gen.traps_in(b) != {"T2"}:
            continue
        n += 1
        got = ship.reduce_batch(b)["duplicates"]
        exp = gen.model.report(b)["duplicates"]
        byid = {s["id"]: s for s in b["samples"]}
        ok = True
        for g, e in zip(got, exp):
            s = byid[e["id"]]
            if not (gen.has_measured(b, s) and gen.has_measured(b, byid[e["of"]])):
                ok &= abs(g["rpd"] - e["rpd"]) <= 1e-9 * max(1, e["rpd"]) and g["pass"] == e["pass"]
        eq2 += ok
    rec["traps"]["T2"] = {"silent_value": "rpd/pass of a duplicate pair with a bound", "shipped_equals_model": f"{eq2}/{n}"}
    for name in ["natural_T1_keep_pooled", "natural_T1_zero", "natural_T2_mean_always"]:
        st = fam_stats(str(root / name / "app"))
        rec["traps"].setdefault(name.split("_")[1], {})[name] = {"failing_families": sorted(k for k, v in st.items() if not v)}
    Path("../receipts/departure-trap-checks.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec, indent=1))

main()
