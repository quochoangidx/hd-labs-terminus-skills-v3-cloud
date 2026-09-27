"""Build wrong-path patches for one optimisation task and run wrong_path_runner on each.

Usage: python3 gen_wrong.py SLUG [--run]
Each variant changes one reference file so that exactly one rule (checked against the
checker's message) or the cost bound breaks; the harness bypass edits the shipped
checker and targets instead of improving the plans. Patches and spec.json go to
reports/SLUG/wrong-paths/; --run writes a receipt per variant.
"""
import copy, glob, importlib.util, json, os, random, subprocess, sys, tempfile
slug = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = os.path.dirname(ROOT)
HERE = os.path.dirname(os.path.abspath(__file__))
task = os.path.join(ROOT, "tasks", slug)
rep = os.path.join(ROOT, "reports", slug)
wp = os.path.join(rep, "wrong-paths"); os.makedirs(os.path.join(wp, "patches"), exist_ok=True)
CFG = {"tbrain-bottling-line-lot-sizing": ("check_plan", "PlanError", "sites", "plans", "plan", ["dorset", "kent", "fife", "tyne"]),
       "tbrain-airport-gate-assignment": ("check_plan", "PlanError", "days", "plans", "plan", ["day-1", "day-2", "day-3", "day-4"]),
       "tbrain-ward-nurse-rostering": ("check_roster", "RosterError", "wards", "rosters", "roster", ["ash", "birch", "cedar", "dale"]),
       "tbrain-newspaper-ad-layout": ("check_layout", "LayoutError", "editions", "layouts", "layout", ["mon", "wed", "fri", "sat"])}
mod, err, infolder, outfolder, noun, insts = CFG[slug]
spec = importlib.util.spec_from_file_location(mod, os.path.join(task, "tests", mod + ".py"))
chk = importlib.util.module_from_spec(spec); spec.loader.exec_module(chk)
targets = json.load(open(os.path.join(task, "tests", "targets.json")))
def inp(i): return json.load(open(os.path.join(task, "environment", "app", infolder, i + ".json")))
def ref(i): return json.load(open(os.path.join(task, "solution", outfolder, i + ".json")))
def tid(i): return f"test_outputs.py::test_{i.replace('-', '_')}_{noun}_is_valid"
def ttg(i): return f"test_outputs.py::test_{i.replace('-', '_')}_{noun}_meets_target"
rng = random.Random(7)
variants = []   # (id, kind, obligations, {relpath: newtext}, expect_failing, expect_msg)

def add(vid, inst, sol, msg, kind="semantic_partial", obl=("VALIDITY",), expect=None):
    try:
        cost = chk.evaluate(inp(inst), sol); got = f"valid, cost {cost}"
    except getattr(chk, err) as e:
        got = str(e)
    if msg == "ABOVE":
        assert got.startswith("valid") and cost > targets[inst], (vid, got, targets[inst])
    else:
        assert msg in got, (vid, got)
    variants.append((vid, kind, list(obl), {f"solution/{outfolder}/{inst}.json": json.dumps(sol)}, expect or [tid(inst)], got))

def above_target_file(inst):
    """Cheapest valid authoring file above the target: the natural near miss."""
    best = None
    for f in glob.glob(os.path.join(rep, "authoring", "**", "*.json"), recursive=True):
        b = os.path.basename(f)
        if not (b.startswith(inst + ".") or b == "p-" + inst + ".json"):
            continue
        try:
            c = chk.evaluate(inp(inst), chk.__dict__["load_" + noun](f))
        except Exception:
            continue
        if c > targets[inst] and (best is None or c < best[0]):
            best = (c, f)
    return best

big = insts[-1]; mid = insts[1]
nm = above_target_file(big)
add("near-miss-" + big, big, json.load(open(nm[1])), "ABOVE", obl=("COST",), expect=[ttg(big)])
pl = json.load(open(os.path.join(rep, "authoring", "p-" + insts[0] + ".json")))
add("shipped-planner-" + insts[0], insts[0], pl, "ABOVE", obl=("COST",), expect=[ttg(insts[0])])

if "airport" in slug:
    day = inp(mid); sol = ref(mid)
    T = {t["id"]: t for t in day["turns"]}; S = {s["id"]: s for s in day["stands"]}
    where = {t: s for s, l in sol["stands"].items() for t in l}
    def moved(t, s):
        x = copy.deepcopy(sol); x["stands"][where[t]].remove(t); x["stands"].setdefault(s, []).append(t); return x
    t3 = next(t for t in T if T[t]["size"] == 3); small = next(s for s in S if S[s]["size"] < 3 and (S[s]["international"] or not T[t3]["international"]))
    add("size-ignored", mid, moved(t3, small), "does not fit stand")
    ti = next(t for t in T if T[t]["international"] and T[t]["size"] <= 1)
    dom = next(s for s in S if not S[s]["international"] and S[s]["size"] >= T[ti]["size"])
    add("border-control-ignored", mid, moved(ti, dom), "no passport control")
    # buffer: a turn that fits a stand whose occupant overlaps it within the buffer only
    b = day["buffer_minutes"]; done = False
    for t in T:
        for s in S:
            if s == where[t] or T[t]["size"] > S[s]["size"] or (T[t]["international"] and not S[s]["international"]):
                continue
            occ = [u for u in sol["stands"].get(s, [])]
            gaps = [u for u in occ if not (T[u]["depart"] + b <= T[t]["arrive"] or T[t]["depart"] + b <= T[u]["arrive"])]
            hard = [u for u in occ if T[u]["arrive"] < T[t]["depart"] and T[t]["arrive"] < T[u]["depart"]]
            if gaps and not hard:
                x = moved(t, s)
                try:
                    chk.evaluate(day, x)
                except chk.PlanError as e:
                    if "buffer" in str(e):
                        add("buffer-without-margin", mid, x, "buffer"); done = True
                if done: break
        if done: break
    assert done, "no buffer variant"
    # wingtip: two widebodies on a wingtip pair at once
    done = False
    for a_, b_ in day["wingtip_pairs"]:
        for u in sol["stands"].get(a_, []):
            if T[u]["size"] != 3: continue
            for t in T:
                if T[t]["size"] == 3 and where[t] != b_ and S[b_]["size"] == 3 and (S[b_]["international"] or not T[t]["international"]) \
                   and T[u]["arrive"] < T[t]["depart"] and T[t]["arrive"] < T[u]["depart"]:
                    x = moved(t, b_)
                    # clear b_ of anything overlapping t so only the wingtip rule can break
                    for v in list(x["stands"][b_]):
                        if v != t and not (T[v]["depart"] + b <= T[t]["arrive"] or T[t]["depart"] + b <= T[v]["arrive"]):
                            x["stands"][b_].remove(v); x["stands"][where[t]].append(v)
                    try:
                        chk.evaluate(day, x)
                    except chk.PlanError as e:
                        if "on the ground together" in str(e):
                            add("wingtip-pairs-ignored", mid, x, "on the ground together"); done = True
                    if done: break
            if done: break
        if done: break
    if not done:
        print("note: no single-move wingtip variant found on", mid)
    x = copy.deepcopy(sol); s0 = next(s for s in x["stands"] if x["stands"][s]); x["stands"][s0].pop()
    add("turn-left-out", mid, x, "is not placed")
elif "nurse" in slug:
    w = inp(mid); sol = ref(mid); R = sol["roster"]; days = w["days"]
    N = {n["id"]: n for n in w["nurses"]}
    def with_row(nid, row):
        x = copy.deepcopy(sol); x["roster"][nid] = row; return x
    def setc(nid, d, c):
        r = list(R[nid]); r[d] = c; return "".join(r)
    names = [("works-on-leave", "is on leave"), ("cover-short", "on duty, minimum"),
             ("registered-short", "registered nurses, need"), ("no-senior-on-shift", "no senior nurse"),
             ("late-then-early", "too little rest"), ("too-many-days-in-a-row", "days in a row"),
             ("no-rest-after-nights", "too soon after the nights")]
    cells = [(nid, d, c) for nid in R for d in range(days) for c in "ELN." if R[nid][d] != c]
    rng.shuffle(cells)
    for vid, msg in names:
        for nid, d, c in cells:
            x = with_row(nid, setc(nid, d, c))
            try:
                chk.evaluate(w, x)
            except chk.RosterError as e:
                if msg in str(e):
                    add(vid, mid, x, msg); break
        else:
            print("note: no single-cell variant for", vid)
elif "lot" in slug:
    site = inp(mid); sol = ref(mid); runs = sol["runs"]
    lines = {l["id"]: l for l in site["lines"]}; prods = {p["id"]: p for p in site["products"]}
    def with_runs(rs):
        return {"runs": rs}
    # capacity: grow one run until its line-day overflows
    for k, r in enumerate(runs):
        spec = prods[r["product"]]["lines"][r["line"]]
        x = copy.deepcopy(runs); x[k]["batches"] += lines[r["line"]]["capacity_minutes"][r["day"]] // spec["minutes_per_batch"] + 1
        try:
            chk.evaluate(site, with_runs(x))
        except chk.PlanError as e:
            if "needs" in str(e):
                add("capacity-ignored", mid, with_runs(x), "capacity"); break
    r0 = runs[0]; bad = next(l for l in lines if l not in prods[r0["product"]]["lines"]) if len(prods[r0["product"]]["lines"]) < len(lines) else None
    if bad is None:
        pid = next(p for p in prods if len(prods[p]["lines"]) < len(lines)); r0 = next(r for r in runs if r["product"] == pid)
        bad = next(l for l in lines if l not in prods[pid]["lines"])
    x = copy.deepcopy(runs); i0 = runs.index(r0); x[i0]["line"] = bad
    add("ineligible-line", mid, with_runs(x), "cannot fill")
    x = copy.deepcopy(runs); x.append(dict(runs[0], batches=1))
    add("duplicate-run", mid, with_runs(x), "two runs of")
    x = copy.deepcopy(runs); x.append({"day": runs[0]["day"], "line": runs[0]["line"], "product": next(p for p in prods if runs[0]["line"] in prods[p]["lines"] and not any(r["product"] == p and r["day"] == runs[0]["day"] and r["line"] == runs[0]["line"] for r in runs)), "batches": 0})
    add("zero-batch-run", mid, with_runs(x), "at least one batch")
    x = copy.deepcopy(runs); x[0]["day"] = site["days"]
    add("day-out-of-range", mid, with_runs(x), "no day")
else:
    ed = inp(mid); sol = ref(mid); P = sol["placements"]; A = {a["id"]: a for a in ed["ads"]}
    def rel(x): return x
    for booked in [a for a in P if A[a]["booked"]]:
        x = copy.deepcopy(sol); del x["placements"][booked]
        try:
            chk.evaluate(ed, x)
        except chk.LayoutError as e:
            if "is not placed" in str(e):
                add("booked-ad-dropped", mid, x, "is not placed"); break
    a0 = next(a for a in P if P[a]["row"] + A[a]["depth"] < ed["rows"])      # an ad resting on ads
    x = copy.deepcopy(sol); x["placements"][a0]["row"] -= 1
    add("ad-floating", mid, x, "not resting")
    a1 = next(a for a in P if P[a]["row"] + A[a]["depth"] == ed["rows"] and P[a]["page"] > 1)
    x = copy.deepcopy(sol); other = next(b for b in P if b != a1 and P[b]["page"] == P[a1]["page"] and P[b]["row"] + A[b]["depth"] == ed["rows"])
    x["placements"][a1]["column"] = P[other]["column"]
    msg = ""
    try:
        chk.evaluate(ed, x)
    except chk.LayoutError as e:
        msg = str(e)
    if "overlap" in msg:
        add("ads-overlap", mid, x, "overlap")
    shared = mid_limit = None
    pg = next(p for p in range(2, ed["pages"] + 1) if any(P[a]["page"] == p for a in P))
    lim = ed["max_ad_share_percent"] * ed["rows"] * ed["columns"] // 100
    used = sum(A[a]["width"] * A[a]["depth"] for a in P if P[a]["page"] == pg)
    extra = [a for a in A if a not in P]
    x = copy.deepcopy(sol)
    for a in sorted(extra, key=lambda a: -A[a]["width"] * A[a]["depth"]):
        h = [0] * ed["columns"]
        for b, q in x["placements"].items():
            if q["page"] == pg:
                for c in range(q["column"], q["column"] + A[b]["width"]):
                    h[c] = max(h[c], ed["rows"] - q["row"])
        for c in range(ed["columns"] - A[a]["width"] + 1):
            if len(set(h[c:c + A[a]["width"]])) == 1 and h[c] + A[a]["depth"] <= ed["rows"]:
                x["placements"][a] = {"page": pg, "column": c, "row": ed["rows"] - h[c] - A[a]["depth"]}
                used += A[a]["width"] * A[a]["depth"]
                break
        if used > lim:
            break
    msg = ""
    try:
        chk.evaluate(ed, x)
    except chk.LayoutError as e:
        msg = str(e)
    if "more than its limit" in msg:
        add("ad-share-exceeded", mid, x, "more than its limit")
    else:
        print("note: share variant gave", msg[:80])
    def drop(x, a, pg):
        h = [0] * ed["columns"]
        for b, q in x["placements"].items():
            if q["page"] == pg and b != a:
                for c in range(q["column"], q["column"] + A[b]["width"]):
                    h[c] = max(h[c], ed["rows"] - q["row"])
        for c in range(ed["columns"] - A[a]["width"] + 1):
            if len(set(h[c:c + A[a]["width"]])) == 1 and h[c] + A[a]["depth"] <= ed["rows"]:
                x["placements"][a] = {"page": pg, "column": c, "row": ed["rows"] - h[c] - A[a]["depth"]}
                return True
        return False
    groups = {}
    for a in A.values():
        if a["competitor_group"]:
            groups.setdefault(a["competitor_group"], []).append(a["id"])
    done = False
    spread = lambda q: 0 if q == 1 else q // 2
    for i in [a for a in P if A[a]["competitor_group"]]:
        rivals = {spread(P[j]["page"]) for j in groups[A[i]["competitor_group"]] if j in P and j != i}
        for k in P:
            if k == i or (A[k]["width"], A[k]["depth"]) != (A[i]["width"], A[i]["depth"]):
                continue
            if spread(P[k]["page"]) not in rivals:
                continue
            x = copy.deepcopy(sol)
            x["placements"][i], x["placements"][k] = dict(P[k]), dict(P[i])
            try:
                chk.evaluate(ed, x)
            except chk.LayoutError as e:
                if "face each other" in str(e):
                    add("competitors-facing", mid, x, "face each other"); done = True
            if done: break
        if done: break
    if not done:
        print("note: no competitor variant found on", mid)

# harness bypass: edit the shipped checker and targets, keep the shipped planner's output
hb = {}
for i in insts:
    hb[f"solution/{outfolder}/{i}.json"] = open(os.path.join(rep, "authoring", "p-" + i + ".json")).read()
tool = f"environment/app/tools/{mod}.py"
src = open(os.path.join(task, tool)).read()
hb[tool] = src.replace("def evaluate(", "def evaluate(*_a, **_k):\n    return 0\n\n\ndef _real_evaluate(", 1)
hb[f"environment/app/{infolder}/targets.json"] = json.dumps({i: 10**12 for i in insts}, indent=1) + "\n"
variants.append(("edit-checker-and-targets", "harness_bypass", [], hb, [ttg(i) for i in insts], "planner output graded against the verifier's own copies"))

specs = []
for vid, kind, obl, files, expect, got in variants:
    diff = []
    for relp, text in files.items():
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as fh:
            fh.write(text if text.endswith("\n") or relp.endswith(".py") else text)
        r = subprocess.run(["diff", "-u", "--label", "a/" + relp, "--label", "b/" + relp, os.path.join(task, relp), fh.name], capture_output=True, text=True)
        diff.append(r.stdout)
    pp = os.path.join(wp, "patches", vid + ".patch")
    open(pp, "w").write("".join(diff))
    specs.append({"id": vid, "kind": kind, "obligation_ids": obl, "patch": os.path.relpath(pp, rep), "expect_failing": expect, "checker_says": got})
json.dump(specs, open(os.path.join(wp, "spec.json"), "w"), indent=1)
for s in specs:
    print(s["id"], "|", s["checker_says"][:80])
if "--run" in sys.argv:
    for s in specs:
        ctrf = os.path.join(wp, s["id"] + ".ctrf.json")
        cmd = [sys.executable, os.path.join(REPO, ".agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py"), task,
               "--id", s["id"], "--patch", os.path.join(rep, s["patch"]), "--verifier", os.path.join(HERE, "score_variant.sh"),
               "--ctrf", ctrf, "--receipt", os.path.join(wp, s["id"] + ".json")]
        for e in s["expect_failing"]:
            cmd += ["--expect-failing", e]
        r = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, WP_CTRF=ctrf), cwd=REPO)
        print(r.stdout.strip() or r.stderr.strip())
