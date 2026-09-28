"""score_skeleton.py APP_DIR [--image TAG] [--json OUT]: rough skeleton-probe scorer (authoring only).

Runs the candidate package APP_DIR/src through our own pristine copy of the fixed driver (the documented
command, `python3 /app/tools/coopsum_run.py FORM.json`) inside the task environment image, candidate src
mounted read-only, --network none, as an unprivileged uid. Forms are seeded and generated per family: a
trap-free broad family, one family per departure D1-D8 and one per trap T1, T2. Each trap input sits only
in its own family (checked with the model's predicates); a departure or trap family keeps only forms on
which the Oracle with that one departure reverted (or that one natural over-repair) differs from the model.
Each summary is compared type-strictly with solution/model.py. Prints PASS/FAIL per family (with the first
differing field of the first failing form) and a VERDICT line; never shipped in the task.
"""

import argparse
import hashlib
import importlib.util
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobs  # noqa: E402
import variants  # noqa: E402

model = jobs.model
TASK = jobs.TASK
DEFAULT_IMAGE = "tbrain-climate-observer-monthly-summary:final"
SEED = 20260927
PER_FAMILY = 8
DRIVER = "coopsum_run.py"


def load_variant(name):
    src = HERE / "variants" / name / "app" / "src" / "coopsum"
    alias = f"coopsum_{name}"
    spec = importlib.util.spec_from_file_location(alias, src / "__init__.py", submodule_search_locations=[str(src)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def first_diff(got, want, path="$"):
    if type(got) is not type(want):
        return f"{path}: got {got!r}, want {want!r}"
    if isinstance(got, dict):
        if list(got) != list(want):
            return f"{path}: keys {list(got)} != {list(want)}"
        for k in got:
            d = first_diff(got[k], want[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(got, list):
        if len(got) != len(want):
            return f"{path}: {len(got)} items, want {len(want)}"
        for i, (x, y) in enumerate(zip(got, want)):
            d = first_diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if got == want else f"{path}: got {got!r}, want {want!r}"


# -- family generators ------------------------------------------------------------------------------

def form_of(rng, stations):
    return {"network": "Upper Basin Cooperative Network", "month": jobs.rand_month(rng), "stations": stations}


def stations_for(rng, month, k, **kw):
    n = model.days_in(month)
    used = set()
    return [jobs.rand_station(rng, jobs.rand_id(rng, used), n, **kw) for _ in range(k)]


def gen_trap_free(rng, morning=None, k=None, **kw):
    month = jobs.rand_month(rng)
    kw.setdefault("missing", (0, 2))
    out = []
    used = set()
    n = model.days_in(month)
    for _ in range(k or rng.randint(1, 4)):
        m = (rng.random() < 0.5) if morning is None else morning
        out.append(jobs.rand_station(rng, jobs.rand_id(rng, used), n, morning=m, unread_ok=not m, **kw))
    return {"network": "Upper Basin Cooperative Network", "month": month, "stations": out}


def fam_broad(rng):
    return jobs.broad_form(rng)


def fam_d1(rng):  # 3.1 a morning observer's maximum belongs to the day before
    return gen_trap_free(rng, morning=True)


def fam_d2(rng):  # 3.3 a morning observer's precipitation belongs to the day before
    form = gen_trap_free(rng, morning=True)
    for s in form["stations"]:
        s["days"][0]["precip"] = jobs.fmt_amt(rng.randint(1, 300))
        s["next"]["precip"] = jobs.fmt_amt(rng.randint(1, 300))
    return form


def fam_d3(rng):  # 4.4 degree days from the day's mean rounded to the whole degree
    return gen_trap_free(rng)


def fam_d4(rng):  # 4.3 a complete month's mean is the average of mean maximum and mean minimum
    return gen_trap_free(rng, missing=(1, 5))


def fam_d5(rng):  # 4.5 thresholds include their own value
    form = gen_trap_free(rng)
    for s in form["stations"]:
        for e in rng.sample(s["days"] + [s["next"]], 6):
            key, value = rng.choice([("max", "90.0"), ("max", "32.0"), ("min", "32.0"), ("min", "0.0")])
            e[key] = value
    return form


def fam_d6(rng):  # 4.2 / 5.4 a tied extreme is given with its latest day
    form = gen_trap_free(rng)
    for s in form["stations"]:
        rows = s["days"] + [s["next"]]
        a, b = sorted(rng.sample(range(1, len(rows) - 1), 2))
        for key in ("max", "min"):
            vals = [model.temp_tenths(r[key]) for r in rows]
            best = (max if key == "max" else min)(v for v in vals if v is not None)
            rows[a][key] = rows[b][key] = jobs.fmt_temp(best)
        top = max(model.amount_hundredths(r["precip"]) or 0 for r in rows)
        rows[a]["precip"] = rows[b]["precip"] = jobs.fmt_amt(max(top, 1))
    return form


def fam_d7(rng):  # 1.2 a trace counts as nought
    return gen_trap_free(rng, trace_rate=0.5)


def fam_d8(rng):  # 5.3 0.10 and 1.00 inch count as 0.10 and 1.00 inch or more
    form = gen_trap_free(rng, morning=False)
    for s in form["stations"]:
        for e in rng.sample(s["days"], 6):
            e["precip"] = rng.choice(["0.10", "1.00"])
    return form


def fam_t1(rng):  # trap T1: an accumulated amount entered at a morning observation
    form = gen_trap_free(rng, morning=True, k=rng.randint(1, 3))
    for s in form["stations"]:
        rows = s["days"] + [s["next"]]
        n = len(s["days"])
        for e in rows:
            if e["precip"] == "A":
                e["precip"] = "0.00"
        length = rng.randint(1, 6)
        if rng.random() < 0.3:
            start = n - length  # the run ends the month: the accumulated amount is `next`
        else:
            start = rng.randint(1, n - 1 - length)
        for k in range(start, start + length):
            rows[k]["precip"] = "A"
        rows[start + length]["precip"] = jobs.fmt_amt(rng.randint(150, 2000))
    return form


def fam_t2(rng):  # trap T2: a month that is not complete for temperature
    month = jobs.rand_month(rng)
    n = model.days_in(month)
    used = set()
    out = []
    for _ in range(rng.randint(1, 3)):
        m = rng.random() < 0.5
        s = jobs.rand_station(rng, jobs.rand_id(rng, used), n, morning=m, missing=(0, 2), unread_ok=not m)
        key = rng.choice(["max", "min"])
        for d in rng.sample(range(n + 1), rng.randint(7, 16)):
            (s["days"] + [s["next"]])[d][key] = "M"
        out.append(s)
    return {"network": "Upper Basin Cooperative Network", "month": month, "stations": out}


FAMILIES = {
    "broad": (fam_broad, None),
    "D1": (fam_d1, "D1_max_on_form_day"),
    "D2": (fam_d2, "D2_precip_on_form_day"),
    "D3": (fam_d3, "D3_dd_from_unrounded_mean"),
    "D4": (fam_d4, "D4_mean_of_daily_means"),
    "D5": (fam_d5, "D5_strict_temperature_thresholds"),
    "D6": (fam_d6, "D6_first_day_on_ties"),
    "D7": (fam_d7, "D7_trace_as_hundredth"),
    "D8": (fam_d8, "D8_strict_precip_thresholds"),
    "T1": (fam_t1, "T1_natural_shift_every_amount"),
    "T2": (fam_t2, ("T2_natural_null_when_incomplete", "T2_natural_new_formula_everywhere")),
}
TRAPS = {"T1": model.carries_accumulated_at_morning, "T2": model.carries_incomplete_month}


def cases():
    variants.build()
    loaded = {}
    rng = random.Random(SEED)
    out = []
    for fam, (gen, discriminate) in FAMILIES.items():
        names = () if discriminate is None else (discriminate if isinstance(discriminate, tuple) else (discriminate,))
        for name in names:
            loaded.setdefault(name, load_variant(name))
        n = tries = 0
        while n < PER_FAMILY:
            tries += 1
            assert tries < 5000, fam
            form = gen(rng)
            model.within_limits(form)
            carried = {t for t, pred in TRAPS.items() if pred(form)}
            if carried != ({fam} if fam in TRAPS else set()):
                continue
            want = model.summarize(form)
            if not all(not same(json.loads(json.dumps(loaded[v].summarize(form))), want) for v in names):
                continue
            out.append((fam, form, want))
            n += 1
    return out


def ensure_image(image):
    if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode:
        subprocess.run(["docker", "build", "-q", "-t", image, str(TASK / "environment")], check=True)


def score(app_dir, image=DEFAULT_IMAGE, out_json=None):
    app_dir = Path(app_dir).resolve()
    ensure_image(image)
    all_cases = cases()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "tools").mkdir()
        shutil.copy2(TASK / "environment" / "app" / "tools" / DRIVER, tmp / "tools" / DRIVER)
        (tmp / "forms").mkdir()
        for k, (_fam, form, _want) in enumerate(all_cases):
            (tmp / "forms" / f"{k:04d}.json").write_text(json.dumps(form))
        loop = ('for f in /forms/*.json; do printf "@@%s\\n" "$(basename "$f")"; '
                f'timeout 60 python3 -I -S /app/tools/{DRIVER} "$f" 2>/dev/null || echo "@@ERROR"; done')
        proc = subprocess.run(["docker", "run", "--rm", "--network", "none", "--user", "65534:65534",
                               "-e", "PYTHONDONTWRITEBYTECODE=1",
                               "-v", f"{app_dir / 'src'}:/app/src:ro", "-v", f"{tmp / 'tools'}:/app/tools:ro",
                               "-v", f"{tmp / 'forms'}:/forms:ro", image, "bash", "-c", loop],
                              capture_output=True, text=True, timeout=1800)
    outputs, current = {}, None
    for line in proc.stdout.splitlines():
        if line.startswith("@@") and line.endswith(".json"):
            current = int(line[2:6])
            outputs[current] = None
        elif current is not None and outputs.get(current) is None and line != "@@ERROR":
            try:
                outputs[current] = json.loads(line)
            except ValueError:
                outputs[current] = None
    families = {fam: {"passed": 0, "total": 0, "first_diff": None} for fam in FAMILIES}
    for k, (fam, _form, want) in enumerate(all_cases):
        got = outputs.get(k)
        c = families[fam]
        c["total"] += 1
        if same(got, want):
            c["passed"] += 1
        elif c["first_diff"] is None:
            c["first_diff"] = f"form {k}: " + (first_diff(got, want) if got is not None else "no output")
    failed = [f for f, c in families.items() if c["passed"] != c["total"]]
    result = {
        "app_dir": str(app_dir), "image": image, "seed": SEED, "per_family": PER_FAMILY,
        "families": families, "failed_families": failed,
        "verdict": "SOLVED" if not failed else "NOT_SOLVED",
        "model_sha256": hashlib.sha256((TASK / "solution" / "model.py").read_bytes()).hexdigest(),
        "driver_sha256": hashlib.sha256((TASK / "environment" / "app" / "tools" / DRIVER).read_bytes()).hexdigest(),
    }
    if out_json:
        Path(out_json).write_text(json.dumps(result, indent=1) + "\n")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("app_dir")
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    ap.add_argument("--json", dest="out_json")
    args = ap.parse_args()
    r = score(args.app_dir, args.image, args.out_json)
    for fam, c in r["families"].items():
        ok = c["passed"] == c["total"]
        print(f"{'PASS' if ok else 'FAIL'} {fam} {c['passed']}/{c['total']}" + ("" if ok else f"  first diff: {c['first_diff']}"))
    print(f"VERDICT {r['verdict']} failed={r['failed_families']}")


if __name__ == "__main__":
    main()
