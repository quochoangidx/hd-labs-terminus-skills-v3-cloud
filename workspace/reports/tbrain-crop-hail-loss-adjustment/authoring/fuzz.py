"""fuzz.py SEED N [OUT]: model vs Oracle-patched package on N generated jobs over the whole
section 1 range (trap inputs included); compares whole statements type-strictly."""

import hashlib
import json
import random
import sys

import gen
import pkgload

HERE = gen.HERE


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def main(seed, n, out=None):
    oracle = pkgload.load(HERE / "oracle" / "app")
    rng = random.Random(seed)
    stats = {"jobs": 0, "claims": 0, "fields": 0, "plots": 0, "mismatches": [],
             "silent_plots_with_loss": 0, "replant_patches": 0, "thinned_plots": 0,
             "options": {}, "stages": {}, "paid_claims": 0, "unpaid_claims": 0}
    for k in range(n):
        j = gen.fuzz_job(rng)
        assert not gen.model.within_limits(j), gen.model.within_limits(j)
        want = gen.model.statements(j)
        got = json.loads(json.dumps(oracle.build_statements(j)))
        stats["jobs"] += 1
        for c in want["claims"]:
            stats["paid_claims" if c["paid"] else "unpaid_claims"] += 1
        for c in j["claims"]:
            stats["claims"] += 1
            for f in c["fields"]:
                stats["fields"] += 1
                stats["options"][f["deductible"]] = stats["options"].get(f["deductible"], 0) + 1
                stats["stages"][f["stage"]] = stats["stages"].get(f["stage"], 0) + 1
                if 1 <= f["replanted"] <= 99:
                    stats["replant_patches"] += 1
                for s, d, _ in f["plots"]:
                    stats["plots"] += 1
                    if 10 * d >= s:
                        stats["thinned_plots"] += 1
                    elif d:
                        stats["silent_plots_with_loss"] += 1
        if not same(got, want):
            stats["mismatches"].append(k)
    stats["seed"] = seed
    stats["model_sha256"] = hashlib.sha256((gen.TASK / "solution" / "model.py").read_bytes()).hexdigest()
    stats["patch_sha256"] = hashlib.sha256((gen.TASK / "solution" / "fix.patch").read_bytes()).hexdigest()
    stats["status"] = "pass" if not stats["mismatches"] else "fail"
    print(json.dumps({k: v for k, v in stats.items() if k != "mismatches"} | {"mismatch_count": len(stats["mismatches"])}))
    if out:
        with open(out, "w") as fh:
            json.dump(stats, fh, indent=1)
            fh.write("\n")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
