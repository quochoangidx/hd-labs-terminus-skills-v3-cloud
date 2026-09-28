"""Write reports/<slug>/panel-precheck-manifest.json for the three optimisation tasks.

Usage: python3 gen_manifest.py SLUG [--snapshot SHA] [--prefix 'test_outputs.py::']
Wrong-path rows are read from reports/<slug>/wrong-paths/*.json receipts when present.
"""
import argparse, glob, json, os
ap = argparse.ArgumentParser()
ap.add_argument("slug"); ap.add_argument("--snapshot"); ap.add_argument("--prefix", default="test_outputs.py::")
a = ap.parse_args()
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
C = {
 "tbrain-bottling-line-lot-sizing": dict(
    insts=["dorset", "kent", "fife", "tyne"], noun="plan", rules="environment/app/docs/production-rules.md",
    outcome="four site production plans that keep every line within capacity and cost no more than each site's best-known target",
    hard="## What a plan must do", cost="A plan costs the sum of:", universal="These rules decide whether a site's production plan can be run",
    silence="Nothing else is charged.", envelope="For each site in `/app/sites/`", fmt="File format",
    fmt_why="the plant's line schedulers read runs by day, line, product and batches in this shape; the instruction names the rules document as the format authority",
    wrong_valid="overfill a line-day by forgetting the setup minutes, fill a product on a line not in its list, or split one product's day on a line into two runs",
    wrong_cost="the shipped lot-for-lot plan or a short local search that is valid but pays too many setups or too much backlog",
    interaction="line capacity with per-run setup minutes decides which lot sizes and pre-builds are possible, so setups, holding and backlog can only be traded inside that set"),
 "tbrain-airport-gate-assignment": dict(
    insts=["day_1", "day_2", "day_3", "day_4"], noun="plan", rules="environment/app/docs/stand-rules.md",
    outcome="four daily stand plans that obey the stand rules and cost no more than each day's best-known target",
    hard="What a plan must do", cost="A plan costs the sum of:", universal="These rules decide whether a day's stand plan can be flown and what it costs.",
    silence="Nothing else is charged.", envelope="For each day in `/app/days/`", fmt="Each key is a stand id",
    fmt_why="the apron's plan files are read by the stand-allocation display in this shape; the instruction names the rules document as the format authority",
    wrong_valid="put a turn on the nearest pier stand without checking the buffer, the wingtip pairs or border control",
    wrong_cost="a dispatch plan (first free stand in arrival order) or a single short local search that is valid but above target",
    interaction="the buffer, wingtip, size and border-control rules decide which low-walking assignments exist, so cost can only be lowered inside the feasible set"),
 "tbrain-ward-nurse-rostering": dict(
    insts=["ash", "birch", "cedar", "dale"], noun="roster", rules="environment/app/docs/roster-rules.md",
    outcome="four ward rosters that keep every hard rule and have a penalty no higher than each ward's best-known target",
    hard="## Hard rules", cost="A valid roster's penalty is the sum of:", universal="These rules decide whether a four-week ward roster can be worked",
    silence="the last day is taken into account.", envelope="For each ward in `/app/wards/`", fmt="File format",
    fmt_why="the ward office's roster files carry one code per nurse per day in this shape; the instruction names the rules document as the format authority",
    wrong_valid="fill the cover first and repair requests afterwards, leaving a late followed by an early, a missing senior or work inside the rest after nights",
    wrong_cost="the shipped fill-the-gaps roster or a single short local search that keeps the hard rules but leaves split weekends and missed requests above target",
    interaction="cover, rest, consecutive-day and night-rest rules decide which rosters are workable, so requests, weekends and hours can only be traded inside that set"),
 "tbrain-newspaper-ad-layout": dict(
    insts=["mon", "wed", "fri", "sat"], noun="layout", rules="environment/app/docs/makeup-rules.md",
    outcome="four edition ad layouts that can go to press and cost no more than each edition's best-known target",
    hard="What a layout must do", cost="A layout costs the sum of:", universal="These rules decide whether an edition's ad layout can go to press",
    silence="plays no part in the rules.", envelope="For each edition in `/app/editions/`", fmt="File format",
    fmt_why="the make-up room reads placements by page, column and row in this shape; the instruction names the rules document as the format authority",
    wrong_valid="stack an ad on a partly filled row, exceed the page's ad share, or put two ads of one competitor group on facing pages",
    wrong_cost="the shipped first-fit layout or a single short search that is valid but leaves paying ads out or on the wrong pages above target",
    interaction="the stacking, ad-share and competitor-spread rules decide which pages can take which ads, so lost revenue can only be lowered inside that set"),
}[a.slug]
P = a.prefix; noun = C["noun"]
valid = [f"{P}test_{i}_{noun}_is_valid" for i in C["insts"]]
target = [f"{P}test_{i}_{noun}_meets_target" for i in C["insts"]]
rep = os.path.join(ROOT, "reports", a.slug)
wps = []
spec_path = os.path.join(rep, "wrong-paths", "spec.json")
for row in (json.load(open(spec_path)) if os.path.exists(spec_path) else []):
    r = os.path.join(rep, "wrong-paths", row["id"] + ".json")
    if os.path.exists(r):
        wps.append({"id": row["id"], "kind": row["kind"], "obligation_ids": row["obligation_ids"], "receipt": os.path.relpath(r, rep)})
if a.snapshot == "auto":
    import importlib.util
    sp = importlib.util.spec_from_file_location("pp", os.path.join(os.path.dirname(ROOT), ".agent/skills/terminus-regular-task-authoring/scripts/panel_precheck.py"))
    pp = importlib.util.module_from_spec(sp); sp.loader.exec_module(pp)
    a.snapshot = pp.tree_hash(__import__("pathlib").Path(ROOT, "tasks", a.slug)) if hasattr(pp, "tree_hash") else None
m = {
 "schema_version": 1, "task_slug": a.slug, "primary_outcome": C["outcome"],
 "obligations": [
  {"id": "VALIDITY", "class": "core", "contribution": f"every {noun} keeps every hard rule of the rules document",
   "authority": {"file": C["rules"], "anchor": C["hard"]}, "implementation_sites": ["solution/solve.sh"],
   "separability": {"standalone_deliverable": False, "joins_before_output": True, "rationale": C["interaction"]},
   "witnesses": {"positive": valid, "boundary": [], "boundary_not_applicable": "each hard rule is checked exhaustively over the whole file; one wrong-path receipt per rule family shows the validity test for that instance rejects it"},
   "expected_source": "independent_model", "discriminating_instance": f"a {noun} that breaks exactly one hard rule",
   "wrong_but_plausible": C["wrong_valid"], "selfdescription_phrase": "rules"},
  {"id": "COST", "class": "core", "contribution": f"every {noun}'s cost under the rules is at or below its best-known target",
   "authority": {"file": C["rules"], "anchor": C["cost"]}, "implementation_sites": ["solution/solve.sh"],
   "separability": {"standalone_deliverable": False, "joins_before_output": True, "rationale": C["interaction"]},
   "witnesses": {"positive": target, "boundary": [], "boundary_not_applicable": "the reference sits exactly on each target (cost equal to target passes); a valid near-miss above target is a wrong-path receipt"},
   "expected_source": "authority_text", "discriminating_instance": f"a valid {noun} whose cost is above the target",
   "wrong_but_plausible": C["wrong_cost"], "selfdescription_phrase": "target"},
 ],
 "causal_graph": {"edges": [{"from": "VALIDITY", "to": "COST"}, {"from": "COST", "to": "PRIMARY_OUTCOME"}]},
 "interactions": [{"id": "feasibility-shapes-cost", "obligation_ids": ["VALIDITY", "COST"], "witness_ids": target, "joins_before_output": True}],
 "closure": {"universal_rule": {"file": C["rules"], "anchor": C["universal"]},
             "silence": {"file": C["rules"], "anchor": C["silence"], "named_cases": []},
             "coverage_envelope": {"file": "instruction.md", "anchor": C["envelope"]}},
 "determinism": {"seeds": [], "clock_dependence": "none", "network": "none", "order_sensitivity": "none"},
 "reference_selfdescription": "solution/solve.sh", "restrictions": [], "unclaimed_units_rationale": {}, "removed_obligations": [],
 "exact_output_requirements": [{"id": "FILE-FORMAT", "domain_required": True, "rationale": C["fmt_why"],
                                "authority_anchor": {"file": C["rules"], "anchor": C["fmt"]}}],
 "verifier_matrix": "verifier-matrix.json", "strict_preflight": os.environ.get("PREFLIGHT_JSON", "preflight-final.json"), "wrong_paths": wps,
}
if a.snapshot:
    m["task_snapshot_sha256"] = a.snapshot
json.dump(m, open(os.path.join(rep, "panel-precheck-manifest.json"), "w"), indent=1)
print("wrote", len(wps), "wrong paths")
