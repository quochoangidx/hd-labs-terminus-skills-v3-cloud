"""validate_scorer.py OUT: score variant trees with skeleton_score.py through Docker (authoring only).

Expected: oracle solved; shipped fails every departure family; each trap's natural fix fails only
that trap's family; each single-departure revert fails its own family."""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import skeleton_score  # noqa: E402
import variants  # noqa: E402


def main(out):
    trees = variants.build()
    with ThreadPoolExecutor(4) as ex:
        results = dict(zip(trees, ex.map(lambda t: skeleton_score.score(t, skeleton_score.DEFAULT_IMAGE, quiet=True),
                                         trees.values())))
    res = {n: {"verdict": r["verdict"], "failed_families": r["failed_families"], "docker_exit": r["docker_exit"],
               "first_differences": {f: r["families"][f]["first_difference"] for f in r["failed_families"]}}
           for n, r in results.items()}
    for n, r in res.items():
        print(f"{n:28s} {r['verdict']:7s} {r['failed_families']}")
    checks = {
        "oracle_solved": res["oracle"]["verdict"] == "solved",
        "shipped_fails_every_departure_family": all(f"D{k}" in res["shipped"]["failed_families"] for k in range(1, 8)),
        "each_revert_fails_its_family": all(f"D{k}" in res[f"revert-D{k}"]["failed_families"] for k in range(1, 8)),
        "T1_natural_fix_fails_only_T1": res["T1-scale-every-span"]["failed_families"] == ["T1"],
        "T2_natural_fix_fails_only_T2": res["T2-cap-every-account"]["failed_families"] == ["T2"],
        "T2_exclusion_reading_fails_T2": "T2" in res["T2-no-sewer-for-multi-unit"]["failed_families"],
    }
    doc = {"image": skeleton_score.DEFAULT_IMAGE, "image_id": next(iter(results.values()))["image_id"],
           "scorer_seed": skeleton_score.SEED, "per_family": skeleton_score.PER_FAMILY,
           "variants": res, "checks": checks, "status": "pass" if all(checks.values()) else "FAIL"}
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(checks), doc["status"])


if __name__ == "__main__":
    main(sys.argv[1])
