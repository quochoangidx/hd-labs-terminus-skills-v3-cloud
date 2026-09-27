#!/usr/bin/env python3
"""Write each wrong path as a patch against the shipped environment (reference fix + one slip).

  make_wrong_paths.py <shipped-parent-with-app> <oracle-parent-with-app> <out-dir>
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = "test_outputs.py::"
Q = '\\"'
WRONG = {
    # id: (obligations, kind, witness, [(file, old, new)] or "SHIPPED:<file>" / "DRIVER")
    "revert-d1-gain": (["WA_GAIN"], "semantic_partial", "test_rule_2_2_record_amplitude_uses_magnification_2080",
                       [("mlnet/amplitude.py", "WOOD_ANDERSON_GAIN = 2080.0", "WOOD_ANDERSON_GAIN = 2800.0")]),
    "revert-d2-half": (["HALF_P2P"], "semantic_partial", "test_rule_2_2_record_amplitude_is_half_peak_to_peak",
                       [("mlnet/amplitude.py", "float(amplitude_nm) / 2.0 *", "float(amplitude_nm) *")]),
    "revert-d3-epicentral": (["HYPOCENTRAL"], "semantic_partial", "test_rule_3_1_distance_is_hypocentral",
                             [("mlnet/distance.py", "math.sqrt(float(epi_km) ** 2 + float(depth_km) ** 2)", "float(epi_km)")]),
    "revert-d4-log-interpolation": (["LINEAR_INTERP"], "semantic_partial", "test_rule_3_3_correction_linear_between_listed_distances",
                                    [("mlnet/attenuation.py", "    if CALIBRATION[0][0] <= distance_km <= CALIBRATION[-1][0]:\n", "    if False:\n")]),
    "t2-linear-extrapolation": (["OFF_TABLE_KEPT"], "semantic_partial", "test_station_beyond_the_table_keeps_the_shipped_correction",
                                [("mlnet/attenuation.py", "    if CALIBRATION[0][0] <= distance_km <= CALIBRATION[-1][0]:\n", "    if True:\n")]),
    "t2-clamp-to-table-ends": (["OFF_TABLE_KEPT"], "semantic_partial", "test_station_beyond_the_table_keeps_the_shipped_correction",
                               [("mlnet/attenuation.py", "    if CALIBRATION[0][0] <= distance_km <= CALIBRATION[-1][0]:\n",
                                 "    distance_km = min(max(distance_km, CALIBRATION[0][0]), CALIBRATION[-1][0])\n    if True:\n")]),
    "revert-d5-correction-subtracted": (["CORRECTION_SIGN"], "semantic_partial", "test_rule_4_2_station_correction_is_added",
                                        [("mlnet/station.py", "minus_log_a0(distance_km) + correction", "minus_log_a0(distance_km) - correction")]),
    "revert-d6-largest-channel": (["STATION_MEAN"], "semantic_partial", "test_rule_4_3_station_magnitude_is_mean_of_channel_magnitudes",
                                  [("mlnet/station.py", "    return sum(magnitudes) / len(magnitudes)", "    return max(magnitudes)")]),
    "t1-mean-over-every-amplitude": (["READINGS"], "semantic_partial", "test_rule_2_3_station_mean_leaves_out_amplitudes_under_three_times_noise",
                                     [("mlnet/station.py", "        if float(item[\"amplitude_nm\"]) >= 3.0 * float(item[\"noise_nm\"])\n", "")]),
    "revert-d7-mean": (["NETWORK_MEDIAN"], "semantic_partial", "test_rule_5_2_network_magnitude_is_median_of_contributors",
                       [("mlnet/network.py", "    middle = len(values) // 2\n", "    return sum(values) / len(values)\n    middle = len(values) // 2\n")]),
    "median-lower-middle": (["NETWORK_MEDIAN"], "semantic_partial", "test_rule_5_2_even_number_takes_mean_of_middle_two",
                            [("mlnet/network.py", "    return (values[middle - 1] + values[middle]) / 2.0", "    return values[middle - 1]")]),
    "revert-d8-no-minimum": (["MIN_THREE"], "semantic_partial", "test_rule_5_3_fewer_than_three_contributors_has_no_network_magnitude",
                             [("mlnet/network.py", "if len(values) < 3:", "if not values:")]),
    "t3-recording-is-a-station": (["STATION_GROUPING"], "semantic_partial", "test_two_sensors_of_one_site_are_one_station", "SHIPPED:mlnet/bulletin.py"),
    "t3-median-over-recordings": (["STATION_GROUPING"], "semantic_partial", "test_two_sensors_of_one_site_are_one_station",
                                  [("mlnet/bulletin.py", "    counted = [row[\"ml\"] for row in stations.values() if row[\"contributes\"]]",
                                    "    counted = [row[\"ml\"] for row in rows if row[\"contributes\"]]")]),
    "driver-side-shim": ([], "harness_bypass", "test_submitted_driver_matches_ours", "DRIVER"),
}


def main():
    shipped, oracle, out = map(Path, sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    plan = {}
    for wid, (obls, kind, witness, edits) in WRONG.items():
        with tempfile.TemporaryDirectory() as tmp:
            var = Path(tmp) / "v"
            shutil.copytree(oracle / "app", var / "app", ignore=shutil.ignore_patterns("__pycache__"))
            if edits == "DRIVER":
                p = var / "app/tools/ml_bulletin.py"
                s = p.read_text()
                p.write_text(s.replace("    json.dump(reduce_bulletin(bulletin), sys.stdout)",
                                       "    report = reduce_bulletin(bulletin)\n    json.dump(report, sys.stdout)"))
                # the package is the reference fix: only the frozen driver differs
            elif isinstance(edits, str):
                rel = edits.split(":", 1)[1]
                shutil.copy2(shipped / "app" / rel, var / "app" / rel)
            else:
                for f, old, new in edits:
                    p = var / "app" / f
                    s = p.read_text()
                    assert s.count(old) == 1, (wid, old)
                    p.write_text(s.replace(old, new))
            diff = subprocess.run([str(HERE / "mkpatch.sh"), str(shipped), str(var)], capture_output=True, text=True).stdout
            (out / f"{wid}.patch").write_text(diff)
        plan[wid] = {"obligation_ids": obls, "kind": kind, "witness": T + witness}
    (out / "plan.json").write_text(json.dumps(plan, indent=1))


if __name__ == "__main__":
    main()
