"""Section-1-valid batches that separate the surviving mutants from the reference repair.
usage: python3 out/discriminators.py  (run from the packet root after work/ exists)"""
import json, subprocess, sys
STD = [{"conc": {"Pb": c, "Cd": c}, "counts": {"Pb": 1024.0 * (100 + 10 * c), "Cd": 1024.0 * (20 + 4 * c)}, "is_counts": 1024.0} for c in (0.0, 10.0, 20.0, 40.0)]
AN = [{"name": "Pb", "mdl": 1.0, "loq": 5.0}, {"name": "Cd", "mdl": 0.5, "loq": 2.0}]
def cnt(pb, cd): return {"Pb": 1024.0 * (100 + 10 * pb), "Cd": 1024.0 * (20 + 4 * cd)}
BATCHES = {
  # W01: counts keys listed Cd-first while analytes are Pb, Cd
  "D1_counts_key_order": {"analytes": AN, "standards": STD, "runs": [
      {"id": "S1", "kind": "sample", "counts": dict(reversed(list(cnt(12, 3).items()))), "is_counts": 1024.0, "dilution": 1}]},
  # W02: replicate standards at 0 (three) and 40 (one): OLS through all points != OLS through group means
  "D2_replicate_standards": {"analytes": AN[:1], "standards": [
      {"conc": {"Pb": 0.0}, "counts": {"Pb": 102400.0}, "is_counts": 1024.0},
      {"conc": {"Pb": 0.0}, "counts": {"Pb": 104448.0}, "is_counts": 1024.0},
      {"conc": {"Pb": 0.0}, "counts": {"Pb": 106496.0}, "is_counts": 1024.0},
      {"conc": {"Pb": 10.0}, "counts": {"Pb": 204800.0}, "is_counts": 1024.0},
      {"conc": {"Pb": 40.0}, "counts": {"Pb": 512000.0}, "is_counts": 1024.0}], "runs": [
      {"id": "S1", "kind": "sample", "counts": {"Pb": 225280.0}, "is_counts": 1024.0, "dilution": 1}]},
  # W03: spike whose corrected reading lands exactly on the mdl (a result), parent a result
  "D3_spike_at_mdl": {"analytes": AN[:1], "standards": STD and [{"conc": {"Pb": s["conc"]["Pb"]}, "counts": {"Pb": s["counts"]["Pb"]}, "is_counts": 1024.0} for s in STD], "runs": [
      {"id": "P1", "kind": "sample", "counts": {"Pb": 1024.0 * (100 + 10 * 3.0)}, "is_counts": 1024.0, "dilution": 2},
      {"id": "P1S", "kind": "spike", "parent": "P1", "added": {"Pb": 4.0}, "counts": {"Pb": 1024.0 * (100 + 10 * 1.0)}, "is_counts": 1024.0, "dilution": 8}]},
  # W16: corrected reading 5e-8 below the mdl must be ND
  "D4_just_below_mdl": {"analytes": AN[:1], "standards": [{"conc": {"Pb": s["conc"]["Pb"]}, "counts": {"Pb": s["counts"]["Pb"]}, "is_counts": 1024.0} for s in STD], "runs": [
      {"id": "S1", "kind": "sample", "counts": {"Pb": 1024.0 * (100 + 10 * (1.0 - 5e-8))}, "is_counts": 1024.0, "dilution": 1}]},
}
def run(src, batch):
    code = "import sys,json;sys.path.insert(0,%r);from metalquant import reduce_batch;print(json.dumps(reduce_batch(json.loads(sys.stdin.read()))))" % src
    return json.loads(subprocess.run([sys.executable, "-c", code], input=json.dumps(batch), capture_output=True, text=True, check=True).stdout)
PAIRS = {"D1_counts_key_order": "W01_counts_key_order", "D2_replicate_standards": "W02_dedupe_standards", "D3_spike_at_mdl": "W03_spike_result_strict", "D4_just_below_mdl": "W16_epsilon_guard"}
for name, batch in BATCHES.items():
    ref = run("work/ref/app/src", batch); alt = run("work/A01_fraction_exact/app/src", batch); mut = run(f"work/{PAIRS[name]}/app/src", batch)
    print(f"== {name}: mutant {PAIRS[name]} {'DIFFERS' if mut != ref else 'same'}; exact-arith alternative {'agrees' if alt == ref else 'DIFFERS'}")
    print("  ref:", json.dumps({k: ref[k] for k in ('samples', 'spikes')}))
    print("  mut:", json.dumps({k: mut[k] for k in ('samples', 'spikes')}))
json.dump(BATCHES, open("out/discriminators.json", "w"), indent=1)
