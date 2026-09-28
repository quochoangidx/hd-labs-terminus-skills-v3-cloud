"""validate_scorer.py OUT: score every variant tree with score_skeleton.py through Docker (authoring only).

Expectations: oracle solved; shipped fails every departure family; the minimal natural fix of each trap's
departure fails only that trap's family; each single-departure revert fails its own departure family.
"""

import contextlib
import io
import json
import sys
from pathlib import Path

import score_skeleton
import variants

IMAGE = "tbrain-workers-comp-disability-benefit:skeleton3"


def main(out):
    trees = variants.build()
    res = {}
    for name, root in trees.items():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = score_skeleton.score(root, IMAGE, None)
        res[name] = {"verdict": r["verdict"], "failed_families": r["failed_families"], "docker_exit": r["docker_exit"],
                     "first_differences": {f: r["families"][f]["first_difference"] for f in r["failed_families"]}}
        print(f"{name:30s} {r['verdict']:11s} {r['failed_families']}")
    checks = {
        "oracle_solved": res["oracle"]["verdict"] == "solved",
        "shipped_fails_every_departure_family": all(f"D{k}" in res["shipped"]["failed_families"] for k in range(1, 9)),
        "each_revert_fails_its_family": all(f"D{k}" in res[f"revert-D{k}"]["failed_families"] for k in range(1, 9)),
        "T1_minimal_fix_of_D1_fails_only_T1": res["T1-shift-every-line"]["failed_families"] == ["T1"],
        "T2_minimal_fix_of_D3_fails_only_T2": res["T2-one-fraction-for-every-week"]["failed_families"] == ["T2"],
        "T1_exclusion_reading_fails_T1": "T1" in res["T1-drop-small-lines"]["failed_families"],
        "T2_exclusion_reading_fails_T2": "T2" in res["T2-pay-nothing-below-1000"]["failed_families"],
    }
    doc = {"image": IMAGE, "image_id": None, "scorer_seed": score_skeleton.SEED, "per_family": score_skeleton.PER_FAMILY,
           "variants": res, "checks": checks, "status": "pass" if all(checks.values()) else "FAIL"}
    import subprocess
    doc["image_id"] = subprocess.run(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
                                     capture_output=True, text=True).stdout.strip()
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(checks), doc["status"])


if __name__ == "__main__":
    main(sys.argv[1])
