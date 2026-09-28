"""make_matrix.py: verifier-matrix.json from the Oracle CTRF and the precheck manifest's witnesses."""
import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent
c = json.loads((R / "oracle-ctrf.json").read_text())
ids = ["test_outputs.py::" + t["name"].split("::")[-1] for t in c["results"]["tests"]]
m = json.loads((R / "panel-precheck-manifest.json").read_text())
clusters = {}
for o in m["obligations"]:
    w = o.get("witnesses", {})
    for u in w.get("positive", []) + w.get("boundary", []) + o.get("smoke_test_ids", []):
        clusters.setdefault(u, set()).add(o["id"])
for u in ids:
    clusters.setdefault(u, set()).add("HARNESS" if "driver" in u or "cannot_read" in u else "WHOLE_STATEMENT")
vm = {"schema_version": 1, "status": "pass", "task_slug": "tbrain-sales-commission-statement", "profile": "cheap_deterministic",
      "unit_ids": ids, "platform_visible_unit_count": len(ids), "unit_clusters": {u: sorted(clusters[u]) for u in ids},
      "cross_cluster_unit_ids": [u for u in ids if len(clusters[u]) > 1],
      "verifier_shapes": ["sealed-independent-model", "verifier-owned-driver", "unprivileged-candidate", "shipped-differential-own-uid"],
      "non_behavior_test_ids": [], "ctrf": {"path": "oracle-ctrf.json", "sha256": hashlib.sha256((R / "oracle-ctrf.json").read_bytes()).hexdigest()}}
(R / "verifier-matrix.json").write_text(json.dumps(vm, indent=1) + "\n")
