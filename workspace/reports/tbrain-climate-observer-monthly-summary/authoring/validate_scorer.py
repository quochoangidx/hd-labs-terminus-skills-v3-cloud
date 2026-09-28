"""Validate score_skeleton.py (authoring only): Oracle all-pass, unpatched fails every departure family,
each one-departure revert fails its own family, each natural trap over-repair fails only its own family.
python3 validate_scorer.py OUT.json"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_skeleton as sk  # noqa: E402
import variants  # noqa: E402

DEPARTURES = [f"D{k}" for k in range(1, 9)]


def main():
    out = Path(sys.argv[1])
    runs = {"oracle": HERE / "oracle" / "app", "unpatched": sk.TASK / "environment" / "app"}
    for name in sorted(variants.EDITS):
        runs[name] = HERE / "variants" / name / "app"
    results, checks = {}, {}
    for name, app in runs.items():
        r = sk.score(app)
        results[name] = {"failed": r["failed_families"],
                         "first_diffs": {f: r["families"][f]["first_diff"] for f in r["failed_families"]}}
        print(name, r["failed_families"], flush=True)
    checks["oracle_all_pass"] = results["oracle"]["failed"] == []
    checks["unpatched_fails_every_departure_family"] = all(d in results["unpatched"]["failed"] for d in DEPARTURES)
    checks["unpatched_fails_broad"] = "broad" in results["unpatched"]["failed"]
    for name in variants.EDITS:
        fam = name.split("_")[0]
        if fam.startswith("T"):
            checks[f"{name}_fails_only_{fam}"] = results[name]["failed"] == [fam]
        else:
            checks[f"{name}_fails_{fam}"] = fam in results[name]["failed"]
    image_id = subprocess.run(["docker", "image", "inspect", "-f", "{{.Id}}", sk.DEFAULT_IMAGE],
                              capture_output=True, text=True).stdout.strip()
    ok = all(v for k, v in checks.items() if k != "unpatched_fails_broad")
    payload = {"status": "pass" if ok else "fail", "image": sk.DEFAULT_IMAGE, "image_id": image_id,
               "seed": sk.SEED, "per_family": sk.PER_FAMILY, "checks": checks, "results": results,
               "note": "unpatched_fails_broad is informational (true: the unpatched package also fails the trap-free broad family)"}
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(checks, indent=1))
    print("STATUS", payload["status"])


if __name__ == "__main__":
    main()
