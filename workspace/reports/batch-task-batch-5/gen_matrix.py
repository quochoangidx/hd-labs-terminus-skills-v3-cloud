"""Write reports/SLUG/verifier-matrix.json from the Oracle CTRF of a preflight run.

Usage: python3 gen_matrix.py SLUG PREFLIGHT_LOG_DIR_NAME
"""
import hashlib, json, os, shutil, sys
slug, logs = sys.argv[1], sys.argv[2]
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rep = os.path.join(ROOT, "reports", slug)
src = os.path.join(rep, logs, "oracle-ctrf.json")
dst = os.path.join(rep, "oracle-ctrf.json")
shutil.copy(src, dst)
d = json.load(open(dst))
ids = [t["name"] for t in d["results"]["tests"]]
assert all(t["status"] == "passed" for t in d["results"]["tests"]), "oracle must pass every unit"
clusters = {u: ["validity" if u.endswith("_is_valid") else "cost-bound", u.split("::test_")[1].rsplit("_", 3)[0]] for u in ids}
m = {"schema_version": 1, "status": "pass", "task_slug": slug, "profile": "cheap_deterministic",
     "unit_ids": ids, "platform_visible_unit_count": len(ids), "unit_clusters": clusters,
     "cross_cluster_unit_ids": [], "verifier_shapes": ["artifact-data-check", "independent-rule-checker", "cost-threshold"],
     "non_behavior_test_ids": [],
     "ctrf": {"path": "oracle-ctrf.json", "sha256": hashlib.sha256(open(dst, "rb").read()).hexdigest()}}
json.dump(m, open(os.path.join(rep, "verifier-matrix.json"), "w"), indent=1)
print(len(ids), "units")
