"""Write panel-precheck-manifest.json and verifier-matrix.json for tbrain-icpms-sop-data-reduction."""
import glob, hashlib, importlib.util, json, os, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
R = HERE.parent
REPO = R.parents[2]
TASK = REPO / "workspace/tasks/tbrain-icpms-sop-data-reduction"
P = "test_outputs.py::"
SOP = "environment/app/docs/reduction-sop.md"
INS = "instruction.md"
def t(*names): return [P + n for n in names]
def ob(id, contribution, anchor, sites, pos, bnd, inst, wrong, phrase, bna=None, src="independent_model", rationale=None):
    w = {"positive": t(*pos), "boundary": t(*bnd)}
    if bna: w["boundary_not_applicable"] = bna
    return {"id": id, "class": "core", "contribution": contribution, "authority": {"file": SOP, "anchor": anchor},
            "implementation_sites": [f"environment/app/src/metalquant/{s}" for s in sites],
            "separability": {"standalone_deliverable": False, "joins_before_output": True,
                             "rationale": rationale or "the value feeds the reported amounts, flags or QC figures of the same batch report"},
            "witnesses": w, "expected_source": src, "discriminating_instance": inst, "wrong_but_plausible": wrong, "selfdescription_phrase": phrase}
obs = [
 ob("CALIBRATION", "readings come from the least-squares line with its intercept fitted", "its intercept fitted (not forced through the origin)", ["calib.py"],
    ["test_calibration_line_has_fitted_intercept"], ["test_section_one_limits_reached"], "standards on a line with a large intercept, and standards at concentration 1000, counts 0 and 10^9, is_counts 1000 and 10^9, only two different concentrations, and a slope of 2 x 10^-12", "keep the fit through the origin", "calibration line"),
 ob("BLANK_LEVEL", "the blank level is the mean of the batch's blank results, every blank wherever it sits; with no result the SOP gives no rule and the shipped first-blank reading stands", "The blank level of an analyte is the mean of the batch's method-blank results", ["blanks.py", "report.py"],
    ["test_blank_level_is_mean_of_results_anywhere", "test_single_blank_result_is_the_level"], ["test_nondetect_blanks_stay_out_of_the_mean", "test_batch_without_blank_results_keeps_shipped_level", "test_readings_below_nought_are_not_clamped"],
    "blanks after the samples, non-detect blanks among results, and a batch whose blanks are all non-detects", "average every blank reading, or use 0.0 when no blank is a result", "blank level"),
 ob("AMOUNT", "the blank level comes off the reading before the dilution multiplies", "Its amount is the corrected reading multiplied by its `dilution`", ["samples.py"],
    ["test_blank_comes_off_before_dilution"], ["test_readings_below_nought_are_not_clamped"], "a non-zero blank level with dilutions 1, 10, 37 and 1000, and a reading of 10^4 at dilution 1000 (an amount of 10^7)", "multiply the reading by the dilution and then subtract the blank level", "amount"),
 ob("FLAGS", "ND, J and unflagged are judged on the corrected reading, J only below the loq", "`J` when the corrected reading is at or above the `mdl` and below the `loq`", ["samples.py"],
    ["test_flags_judged_on_corrected_reading"], ["test_flags_just_either_side_of_mdl_and_loq", "test_section_one_limits_reached"], "corrected readings a hair either side of the mdl and the loq, and diluted samples whose amount crosses the mdl while the corrected reading does not", "judge the flag on the amount, or add a tolerance to a limit", "flags"),
 ob("CCV", "a CCV passes on its recovery rounded to one decimal, 90.0 to 110.0 inclusive; a run with a CCV on each side needs both to pass; otherwise the shipped nearest-earlier check stands", "The CCV passes for that analyte when the recovery, rounded to one", ["qc.py"],
    ["test_bracketed_runs_need_both_ccvs"], ["test_ccv_pass_on_rounded_recovery_inclusive", "test_unbracketed_runs_keep_shipped_check"], "recoveries of 90.0, 110.00000000000001, 110.04, 110.06, 89.96 and 89.94; runs before the first and after the last CCV", "compare the unrounded recovery, or use the CCV on whichever side exists", "CCV"),
 ob("SPIKE", "spike recovery is (spike amount - parent amount) / added when both are results; otherwise the shipped calculation stands", "A spike's recovery for an analyte is the amount of the spike's result less the", ["qc.py", "report.py"],
    ["test_spike_recovery_of_results"], ["test_nondetect_spikes_keep_shipped_recovery"], "a non-detect parent, a non-detect spike and a spike with a different dilution from its parent", "divide by the amount added for every spike, or take a non-detect parent as zero", "spike recovery"),
]
edges = [("CALIBRATION", "BLANK_LEVEL"), ("CALIBRATION", "CCV"), ("BLANK_LEVEL", "AMOUNT"), ("BLANK_LEVEL", "FLAGS"), ("AMOUNT", "SPIKE"), ("FLAGS", "SPIKE"), ("CCV", "PRIMARY_OUTCOME"), ("SPIKE", "PRIMARY_OUTCOME"), ("AMOUNT", "PRIMARY_OUTCOME"), ("FLAGS", "PRIMARY_OUTCOME")]
spec = {  # wrong path -> obligations
 "cal-through-origin": ["CALIBRATION"], "blank-first-blank-only": ["BLANK_LEVEL"], "blank-mean-of-all-blanks": ["BLANK_LEVEL"],
 "blank-no-results-zero": ["BLANK_LEVEL"], "blank-level-floor-zero": ["BLANK_LEVEL", "AMOUNT"], "amount-dilute-then-subtract": ["AMOUNT"], "flag-on-amount": ["FLAGS"],
 "ccv-exclusive-unrounded": ["CCV"], "ccv-inclusive-unrounded": ["CCV"], "bracket-preceding-only": ["CCV"],
 "bracket-either-side": ["CCV"], "unbracketed-is-not-ok": ["CCV"], "spike-dilution-in-denominator": ["SPIKE"], "spike-added-for-every-spike": ["SPIKE"],
 "spike-nondetect-parent-as-zero": ["SPIKE"], "spike-result-on-spike-only": ["SPIKE", "FLAGS"], "reads-expected-files": [], "driver-shim": [],
}
kinds = {k: ("harness_bypass" if k in ("reads-expected-files", "driver-shim") else "semantic_partial") for k in spec}
wps = [{"id": k, "kind": kinds[k], "obligation_ids": v, "receipt": f"wrong-paths/{k}.json"} for k, v in spec.items() if (R / "wrong-paths" / f"{k}.json").exists()]
sp = importlib.util.spec_from_file_location("pp", REPO / ".agent/skills/terminus-regular-task-authoring/scripts/panel_precheck.py")
pp = importlib.util.module_from_spec(sp); sp.loader.exec_module(pp)
m = {
 "schema_version": 1, "task_slug": TASK.name, "task_snapshot_sha256": pp.tree_hash(TASK),
 "primary_outcome": "the batch report the fixed driver prints follows SOP TM-07: blank levels, sample amounts and flags with CCV qualifiers, CCV recoveries and spike recoveries",
 "obligations": obs,
 "causal_graph": {"edges": [{"from": a, "to": b} for a, b in edges]},
 "interactions": [
   {"id": "blank-level-decides-detection", "obligation_ids": ["BLANK_LEVEL", "FLAGS"], "witness_ids": t("test_flags_just_either_side_of_mdl_and_loq", "test_generated_batches"), "joins_before_output": True},
   {"id": "detection-decides-spike-rule", "obligation_ids": ["FLAGS", "SPIKE"], "witness_ids": t("test_nondetect_spikes_keep_shipped_recovery"), "joins_before_output": True},
   {"id": "calibration-sets-ccv-and-blank-readings", "obligation_ids": ["CALIBRATION", "CCV", "BLANK_LEVEL"], "witness_ids": t("test_calibration_line_has_fitted_intercept", "test_bracketed_runs_need_both_ccvs", "test_generated_batches"), "joins_before_output": True},
   {"id": "ccv-verdict-qualifies-samples", "obligation_ids": ["CCV", "FLAGS"], "witness_ids": t("test_bracketed_runs_need_both_ccvs", "test_report_order_and_types"), "joins_before_output": True},
   {"id": "blank-and-dilution-make-the-amount", "obligation_ids": ["BLANK_LEVEL", "AMOUNT"], "witness_ids": t("test_blank_comes_off_before_dilution"), "joins_before_output": True},
 ],
 "closure": {
   "universal_rule": {"file": INS, "anchor": "Every rule in the SOP holds for every batch within the limits of its section 1"},
   "silence": {"file": INS, "anchor": "Where the SOP gives no rule for a value, keep the calculation the code makes for that value today", "named_cases": []},
   "coverage_envelope": {"file": INS, "anchor": "Batches of one to eighty runs and one to four analytes will be reduced"},
 },
 "determinism": {"seeds": ["solution/seal.py SEED=20260926 (authoring only; graded batches are sealed files)"], "clock_dependence": "none", "network": "none", "order_sensitivity": "none"},
 "reference_selfdescription": "solution/solve.sh",
 "restrictions": [{"id": "DRIVER-UNCHANGED", "statement": "Leave /app/tools/metalquant_run.py exactly as it is", "enforced_by": t("test_driver_is_unchanged"), "enforcement_level": "source", "allowed_exceptions_disclosed": True}],
 "unclaimed_units_rationale": {
   P + "test_driver_is_unchanged": "restriction witness (DRIVER-UNCHANGED)",
   P + "test_candidate_cannot_read_expected_reports": "isolation witness: the candidate user cannot read the sealed expectations",
   P + "test_candidate_cannot_read_verifier_logs": "isolation witness: the candidate user cannot read /logs/verifier",
   P + "test_report_order_and_types": "section 8 report shape over four analytes and every run kind; exercises all obligations together",
   P + "test_generated_batches": "6 seeded batches across the section 1 domain; exercises all obligations together",
   P + "test_capacity_batch": "80 runs, four analytes, eight standards, dilution 1000: the section 1 maxima",
 },
 "removed_obligations": [
   {"id": "ON_LIMIT", "reason": "v9 panel finding 3: an ordinary double-precision reduction cannot decide a value mathematically on a decimal limit (0.1 + 0.2); exact on-limit inclusivity is not core to the task (its hard part is where the SOP stops), so SOP section 1 now keeps every judged value 10^-5 from each limit and the fixtures sit a hair either side",
    "former_anchor": {"file": "instruction.md", "anchor": "values that land exactly on a detection limit"}},
 ],
 "exact_output_requirements": [
   {"id": "REPORT-SCHEMA", "domain_required": True, "rationale": "the laboratory's reporting step reads this JSON report; its keys, list order and null for ND are fixed by SOP section 8", "authority_anchor": {"file": SOP, "anchor": "prints one JSON object"}},
   {"id": "FLAG-STRINGS", "domain_required": True, "rationale": "ND and J are the standard laboratory data qualifiers; the SOP names them", "authority_anchor": {"file": SOP, "anchor": "`ND` when the corrected reading is below the `mdl`"}},
   {"id": "CCV-ROUNDING", "domain_required": True, "rationale": "laboratories judge CCV acceptance on the recovery reported to one decimal place", "authority_anchor": {"file": SOP, "anchor": "rounded to one"}},
   {"id": "TOLERANCE", "domain_required": True, "rationale": "numbers are compared to one part in a million, stated in the instruction", "authority_anchor": {"file": INS, "anchor": "within one part in a million of its size"}},
 ],
 "verifier_matrix": "verifier-matrix.json", "strict_preflight": "preflight.json", "wrong_paths": wps,
}
json.dump(m, open(R / "panel-precheck-manifest.json", "w"), indent=1)
ctrf = R / "preflight-evidence" / "oracle-ctrf.json"
if ctrf.exists():
    shutil.copy(ctrf, R / "oracle-ctrf.json")
    d = json.load(open(R / "oracle-ctrf.json"))
    ids = [x["name"] for x in d["results"]["tests"]]
    assert len(ids) == len(set(ids)) and all(x["status"] == "passed" for x in d["results"]["tests"])
    owner = {}
    for o in obs:
        for u in o["witnesses"]["positive"] + o["witnesses"]["boundary"]:
            owner.setdefault(u, []).append(o["id"])
    mx = {"schema_version": 1, "status": "pass", "task_slug": TASK.name, "profile": "cheap_deterministic", "unit_ids": ids,
          "platform_visible_unit_count": len(ids), "unit_clusters": {u: owner.get(u, ["harness-or-integration"]) for u in ids},
          "cross_cluster_unit_ids": [u for u in ids if len(owner.get(u, [])) > 1],
          "verifier_shapes": ["sealed-independent-model", "verifier-owned-driver", "unprivileged-candidate"], "non_behavior_test_ids": t("test_driver_is_unchanged", "test_candidate_cannot_read_expected_reports", "test_candidate_cannot_read_verifier_logs"),
          "ctrf": {"path": "oracle-ctrf.json", "sha256": hashlib.sha256(open(R / "oracle-ctrf.json", "rb").read()).hexdigest()}}
    json.dump(mx, open(R / "verifier-matrix.json", "w"), indent=1)
print("manifest written;", len(wps), "wrong paths; snapshot", m["task_snapshot_sha256"][:12])
