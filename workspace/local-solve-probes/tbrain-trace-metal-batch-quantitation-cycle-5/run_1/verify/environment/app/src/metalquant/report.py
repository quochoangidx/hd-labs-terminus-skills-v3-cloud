"""Assemble the batch report (SOP section 8)."""

from metalquant import blanks, calib, qc, samples

REPORTED = ("sample", "spike")


def reduce_batch(batch):
    analytes = batch["analytes"]
    standards = batch["standards"]
    runs = batch["runs"]

    lines = {a["name"]: calib.fit_line(standards, a["name"]) for a in analytes}
    readings = {
        a["name"]: {run["id"]: calib.reading(run, a["name"], lines[a["name"]]) for run in runs}
        for a in analytes
    }
    levels = {a["name"]: blanks.blank_level(runs, a, readings[a["name"]]) for a in analytes}

    ccv_pass = {a["name"]: {} for a in analytes}
    ccvs = []
    for run in runs:
        if run["kind"] != "ccv":
            continue
        for a in analytes:
            name = a["name"]
            recovery = qc.ccv_recovery(readings[name][run["id"]], run["true"][name])
            passed = qc.ccv_passes(recovery)
            ccv_pass[name][run["id"]] = passed
            ccvs.append({"id": run["id"], "analyte": name, "recovery": recovery, "pass": passed})

    amounts = {a["name"]: {} for a in analytes}
    reported = []
    for index, run in enumerate(runs):
        if run["kind"] not in REPORTED:
            continue
        for a in analytes:
            name = a["name"]
            value = samples.amount(readings[name][run["id"]], levels[name], run["dilution"])
            amounts[name][run["id"]] = value
            mark = samples.flag(readings[name][run["id"]], levels[name], run["dilution"], a)
            reported.append(
                {
                    "id": run["id"],
                    "analyte": name,
                    "value": None if mark == "ND" else value,
                    "flag": mark,
                    "ccv_ok": qc.bracket_ok(runs, index, ccv_pass[name]),
                }
            )

    spikes = []
    for run in runs:
        if run["kind"] != "spike":
            continue
        for a in analytes:
            name = a["name"]
            recovery = qc.spike_recovery(
                amounts[name][run["id"]],
                amounts[name][run["parent"]],
                run["added"][name],
            )
            spikes.append({"id": run["id"], "analyte": name, "recovery": recovery})

    return {"blank_levels": levels, "samples": reported, "ccvs": ccvs, "spikes": spikes}
