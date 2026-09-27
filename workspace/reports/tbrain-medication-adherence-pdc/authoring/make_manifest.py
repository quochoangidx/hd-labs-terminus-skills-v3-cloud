"""Write workspace/reports/<slug>/panel-precheck-manifest.json (builder_certified)."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "panel-precheck-manifest.json"
SPEC = "environment/app/docs/adherence-measure-spec.md"
T = "test_outputs.py::"
SITES = lambda *f: [f"environment/app/src/pdcmeasure/{x}" for x in f]

def ob(i, contrib, anchor, sites, pos, bnd, inst, wrong, phrase, rationale, file=SPEC):
    return {"id": i, "class": "core", "contribution": contrib, "authority": {"file": file, "anchor": anchor},
            "implementation_sites": sites, "separability": {"standalone_deliverable": False, "joins_before_output": True, "rationale": rationale},
            "witnesses": {"positive": [T + t for t in pos], "boundary": [T + t for t in bnd]}, "expected_source": "independent_model",
            "discriminating_instance": inst, "wrong_but_plausible": wrong, "selfdescription_phrase": phrase}

obs = [
 ob("FILL", "a claim line with no days supply is not a fill: it sets no index date, adds no fill date and lists no class", "fill is a claim line that dispensed a supply", SITES("measure.py", "claims.py"),
    ["test_rule_2_1_line_with_no_days_supply_is_not_a_fill"], ["test_rule_2_1_line_with_no_days_supply_is_not_a_fill"],
    "an adjustment line dated before the first fill; an adjustment before 2 October with the first fill after it; one fill date plus an adjustment on another date; a class of adjustment lines only",
    "take the earliest claim line as the index date, or count its date toward the two fill dates (natural rewrites of the index date and the measure test)", "fill", "decides the index date, the measure test and which rows exist"),
 ob("INDEX_DATE", "the index date is the earliest fill date, whatever the export order", "index date for a class is the fill date of the member's", SITES("measure.py"),
    ["test_rule_2_3_index_date_is_the_earliest_fill_date"], ["test_rule_2_3_index_date_is_the_earliest_fill_date"],
    "lines exported out of date order, the earliest fill listed last", "the first line with a supply in file order (shipped)", "index date", "the index date starts the treatment period and decides the 2 October test"),
 ob("START_DAY", "a fill starts on its fill date", "Every fill covers one or more consecutive days", SITES("coverage.py"),
    ["test_rule_3_1_fill_starts_on_its_fill_date"], ["test_rule_3_1_fill_starts_on_its_fill_date"],
    "fills on 1 January, 29 February and 31 December", "start the day after the fill date (shipped)", "start day", "every covered day"),
 ob("CARRY_OVER", "a fill whose date an earlier fill of the same drug covers starts the day after that coverage; fills of one date in file order; other drugs never move it", "then its start day is the day after the last day that the member's", SITES("coverage.py"),
    ["test_rule_3_2_refill_of_same_drug_carries_over", "test_rule_3_2_other_drugs_never_move_one_another"], ["test_rule_3_2_refill_of_same_drug_carries_over"],
    "a refill one day early, months early, two fills of one drug on one day, a chain past 31 December; two drugs overlapping in one class",
    "no carry-over (shipped); carry-over across drugs; carry-over from the previous fill only", "carry-over", "covered days feed the PDC"),
 ob("SUPPLY_LIMIT", "a fill within the limit covers its days supply; the specification gives no length for a fill above it, so today's 100 days stand", "A fill within the limit covers as many days as its days supply", SITES("coverage.py"),
    ["test_fill_above_the_supply_limit_keeps_todays_coverage"], ["test_fill_above_the_supply_limit_keeps_todays_coverage", "test_rule_1_3_limits_reached"],
    "fills of 101, 102, 120, 150, 180, 200 and 365 days followed by refills of the same drug; a 100-day fill", "cover the full supply, or one day, above the limit (natural over-repairs)", "supply limit", "the coverage length feeds covered days and carry-over"),
 ob("MEASURE", "in the measure: fills on two or more different fill dates and an index date no later than 2 October", "than 2 October of the measurement year", SITES("measure.py"),
    ["test_rule_2_4_fills_on_two_different_dates", "test_rule_2_4_index_date_no_later_than_2_october"], ["test_rule_2_4_index_date_no_later_than_2_october"],
    "two and three fills on one day; index 1, 2 and 3 October in 2000, 2023 and 2024", "count lines (shipped); no index test (shipped); 1 or 3 October; day 275", "in the measure", "decides the treatment period, adherence and the rate base"),
 ob("TREATMENT_PERIOD", "a member in the measure is measured to 31 December; the specification gives no period for a member outside it, so today's span stands", "The treatment period of a member in the measure runs from the index date", SITES("measure.py"),
    ["test_rule_2_5_treatment_period_runs_to_year_end", "test_member_outside_the_measure_keeps_todays_span"], ["test_rule_2_5_treatment_period_runs_to_year_end", "test_member_outside_the_measure_keeps_todays_span"],
    "members who stop in February; a fill on 31 December; members outside the measure with stays inside and after their coverage",
    "period to the last covered day (shipped); a year-end period or stay-free span for everyone (natural over-repairs)", "treatment period", "the PDC denominator"),
 ob("STAYS", "stay days leave both the period days and the covered days", "A member's period days for a class are the days of the treatment period", SITES("pdc.py"),
    ["test_rule_4_1_stay_days_leave_period_and_covered_days"], ["test_rule_4_1_stay_days_leave_period_and_covered_days"],
    "a stay before the index date, one across it, one of a single day, one on 31 December, sixty stay days in ten stays", "stay days out of covered days only (shipped); a stay's discharge day left out", "period days", "the PDC denominator and numerator"),
 ob("ROUNDING", "every PDC and rate to the nearest tenth, an exact half going up", "an exact half going up", SITES("rounding.py"),
    ["test_rule_1_2_percentages_round_half_up"], ["test_rule_1_2_percentages_round_half_up", "test_rule_5_1_reportable_class_rate_over_its_rate_base"],
    "PDCs of 1.25, 33.75, 66.67, 70.79; a rate of 43.75", "floor (shipped); round() half to even", "rounded", "adherence is judged on the reported PDC"),
 ob("ADHERENT", "adherent: in the measure and a reported PDC of 80.0 or more", "A member is adherent for a class when the member is in the measure", SITES("pdc.py"),
    ["test_rule_4_2_adherent_at_80_and_only_in_the_measure"], ["test_rule_4_2_adherent_at_80_and_only_in_the_measure"],
    "PDC exactly 80.0 twice, 79.4; fully covered members outside the measure", "above 80.0 (shipped); adherent outside the measure (shipped)", "adherent", "the class counts and rate"),
 ob("CLASS_RATE", "a reportable class divides by its rate base; a class below ten has no rate base in the specification, so today's divisor stands", "A class's adherence rate is 100 times the number of members adherent for", SITES("classes.py"),
    ["test_rule_5_1_reportable_class_rate_over_its_rate_base", "test_class_that_is_not_reportable_keeps_todays_divisor"], ["test_rule_5_1_reportable_class_rate_over_its_rate_base", "test_class_that_is_not_reportable_keeps_todays_divisor"],
    "classes with 10, 11 and 16 members in the measure beside members outside it; classes with 9, 5, 3, 1 and 0 in the measure",
    "divide by every member (shipped); divide by members in the measure, or zero, for every class (natural over-repairs)", "rate base", "the class rows"),
]
obs.append({"id": "DRIVER", "class": "support", "contribution": "fixed driver printing the report", "implementation_complete": True, "repair_surface": False,
            "paths": ["environment/app/tools/pdc_run.py"], "smoke_test_ids": [T + "test_submitted_driver_unchanged"]})
obs.append({"id": "CLAIMS_LOADER", "class": "support", "contribution": "decodes claim lines and stays", "implementation_complete": True, "repair_surface": False,
            "paths": ["environment/app/src/pdcmeasure/claims.py", "environment/app/src/pdcmeasure/days.py"], "smoke_test_ids": [T + "test_generated_claims_files"]})
edges = [("FILL", "INDEX_DATE"), ("FILL", "MEASURE"), ("INDEX_DATE", "MEASURE"), ("INDEX_DATE", "TREATMENT_PERIOD"), ("START_DAY", "CARRY_OVER"), ("SUPPLY_LIMIT", "CARRY_OVER"),
         ("CARRY_OVER", "TREATMENT_PERIOD"), ("MEASURE", "TREATMENT_PERIOD"), ("TREATMENT_PERIOD", "STAYS"), ("STAYS", "ROUNDING"), ("ROUNDING", "ADHERENT"),
         ("MEASURE", "ADHERENT"), ("ADHERENT", "CLASS_RATE"), ("MEASURE", "CLASS_RATE"), ("CLASS_RATE", "PRIMARY_OUTCOME"), ("ADHERENT", "PRIMARY_OUTCOME"), ("ROUNDING", "PRIMARY_OUTCOME")]
manifest = {
 "schema_version": 1, "task_slug": "tbrain-medication-adherence-pdc",
 "primary_outcome": "the report printed by /app/tools/pdc_run.py gives every member's index date, measure status, period days, covered days, PDC and adherence for each class, and every class's counts and adherence rate, as specification AM-2 gives them",
 "obligations": obs,
 "causal_graph": {"edges": [{"from": a, "to": b} for a, b in edges]},
 "interactions": [
  {"id": "fills-decide-the-index-and-the-measure", "obligation_ids": ["FILL", "INDEX_DATE", "MEASURE"], "witness_ids": [T + "test_rule_2_1_line_with_no_days_supply_is_not_a_fill", T + "test_rule_2_4_index_date_no_later_than_2_october"], "joins_before_output": True},
  {"id": "coverage-feeds-the-pdc", "obligation_ids": ["START_DAY", "CARRY_OVER", "SUPPLY_LIMIT", "STAYS"], "witness_ids": [T + "test_rule_3_2_refill_of_same_drug_carries_over", T + "test_fill_above_the_supply_limit_keeps_todays_coverage", T + "test_generated_claims_files"], "joins_before_output": True},
  {"id": "measure-sets-period-and-adherence", "obligation_ids": ["MEASURE", "TREATMENT_PERIOD", "ADHERENT"], "witness_ids": [T + "test_rule_2_5_treatment_period_runs_to_year_end", T + "test_rule_4_2_adherent_at_80_and_only_in_the_measure", T + "test_member_outside_the_measure_keeps_todays_span"], "joins_before_output": True},
  {"id": "adherence-makes-the-class-rate", "obligation_ids": ["ADHERENT", "MEASURE", "CLASS_RATE", "ROUNDING"], "witness_ids": [T + "test_rule_5_1_reportable_class_rate_over_its_rate_base", T + "test_class_that_is_not_reportable_keeps_todays_divisor"], "joins_before_output": True},
 ],
 "closure": {
  "universal_rule": {"file": "instruction.md", "anchor": "Each of its rules holds for every claims file within the limits of its rule 1.3"},
  "silence": {"file": "instruction.md", "anchor": "Where the specification gives no rule for a figure that one of the package's steps works out",
   "named_cases": [
    {"file": SPEC, "anchor": "The treatment period of a member in the measure runs from the index date", "witness_ids": [T + "test_member_outside_the_measure_keeps_todays_span", T + "test_figures_left_to_todays_code_together"]},
    {"file": SPEC, "anchor": "The rate base of a reportable class is the number of members in the measure", "witness_ids": [T + "test_class_that_is_not_reportable_keeps_todays_divisor", T + "test_figures_left_to_todays_code_together"]},
    {"file": SPEC, "anchor": "A fill within the limit covers as many days as its days supply", "witness_ids": [T + "test_fill_above_the_supply_limit_keeps_todays_coverage", T + "test_figures_left_to_todays_code_together"]}]},
  "coverage_envelope": {"file": "instruction.md", "anchor": "Claims files of one to a hundred members with fills under one to forty class codes will be measured"}},
 "determinism": {"seeds": ["solution/jobgen.py SEED=20260927 (authoring only; graded files are sealed)",
   "tests/test_outputs.py RELABEL_SEED from os.urandom: relabels the generated family only (plan, member ids, drug and class codes with their order kept, member and line order, the year moved 28 years), a transformation that leaves every expected figure unchanged; the seed is printed with any failure"],
   "clock_dependence": "none", "network": "none", "order_sensitivity": "none"},
 "reference_selfdescription": "solution/solve.sh",
 "restrictions": [{"id": "DRIVER-UNCHANGED", "statement": "leave that driver exactly as it is; the file you leave there has to match ours byte for byte",
   "enforced_by": [T + "test_submitted_driver_unchanged"], "enforcement_level": "source", "allowed_exceptions_disclosed": True}],
 "unclaimed_units_rationale": {
  T + "test_submitted_driver_unchanged": "restriction witness (DRIVER-UNCHANGED), checked before and after candidate code",
  T + "test_candidate_cannot_read_verifier_state": "isolation witness: the candidate user cannot read /tests, the sealed expectations, the shipped copy or /logs/verifier (with a readable control)",
  T + "test_generated_claims_files": "seeded files with every member in the measure and every fill within the limit, as sealed and relabelled at run time",
  T + "test_rule_1_3_limits_reached": "100 members, 40 class codes of one to eight characters, a 400-line member, 10 stays of 60 days in a leap year",
  T + "test_report_order_and_codes": "README order of members and classes, a member with no claim lines, codes of one and eight characters",
  T + "test_figures_left_to_todays_code_together": "the three figures left to today's code in one file (outside the measure, above the limit, a class below ten)"},
 "removed_obligations": [],
 "exact_output_requirements": [
  {"id": "REPORT-SCHEMA", "domain_required": True, "rationale": "the plan's quality reporting reads this JSON report; keys and list order are fixed by the README data contract", "authority_anchor": {"file": "environment/app/README.md", "anchor": "in ascending character order of their codes (digits before letters)"}},
  {"id": "PERCENT-ROUNDING", "domain_required": True, "rationale": "adherence is judged on the PDC as reported to a tenth", "authority_anchor": {"file": SPEC, "anchor": "an exact half going up"}}],
 "verifier_matrix": "verifier-matrix.json",
 "strict_preflight": "preflight/preflight.json",
 "wrong_paths": [],
}
OUT.write_text(json.dumps(manifest, indent=1) + "\n")
print("wrote", OUT)
