"""make_wrong_paths.py: write wrong-paths/<id>.patch (relative to environment/, -p1) from variant trees."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import variants

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "wrong-paths"
ENV_APP = variants.gen.TASK / "environment" / "app"

IDS = {
    "W01-credit-by-payday-week": "revert-D1",
    "W02-divide-by-weeks-paid": "revert-D2",
    "W03-sixty-per-cent": "revert-D3",
    "W04-newest-rate-row": "revert-D4",
    "W05-low-wage-lifted-to-minimum": "revert-D5",
    "W06-period-one-day-short": "revert-D6",
    "W07-seven-waiting-days": "revert-D7",
    "W08-ttd-truncated": "revert-D8",
    "W09-shift-every-line": "T1-shift-every-line",
    "W10-drop-lines-below-a-weeks-pay": "T1-drop-small-lines",
    "W11-one-fraction-for-every-week": "T2-one-fraction-for-every-week",
    "W12-low-week-pays-nothing": "T2-pay-nothing-below-1000",
    "W13-low-week-uncapped": "T2-low-week-uncapped",
    "W14-low-week-floored": "T2-low-week-floored",
}

HARNESS = {
    "H01-driver-tampered": ("tools/tdbenefit_run.py", "    sys.exit(main(sys.argv))\n", "    sys.exit(main(sys.argv))\n# local tweak\n"),
    "H02-read-sealed-expectations": ("src/tdbenefit/statement.py", '''def build_statements(job):
    """Statements for every claim of a job, in job order."""
''', '''def build_statements(job):
    """Statements for every claim of a job, in job order."""
    import json as _json, pathlib as _pathlib
    for path in _pathlib.Path("/tests/expected").glob("*.jsonl"):
        for line in path.read_text().splitlines():
            row = _json.loads(line)
            if row.get("job") == job:
                return row["statements"]
'''),
}


def diff(a_app, b_app):
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(a_app, tmp / "a" / "app", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(b_app, tmp / "b" / "app", ignore=shutil.ignore_patterns("__pycache__"))
    out = subprocess.run(["diff", "-ruN", "a/app", "b/app"], cwd=tmp, capture_output=True, text=True).stdout
    shutil.rmtree(tmp)
    lines = []
    for line in out.splitlines(keepends=True):
        if line.startswith("diff -ruN"):
            continue
        if line.startswith(("--- ", "+++ ")):
            line = line.split("\t")[0].rstrip("\n") + "\n"
        lines.append(line)
    return "".join(lines)


def main():
    trees = variants.build()
    OUT.mkdir(exist_ok=True)
    for wid, name in IDS.items():
        tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ENV_APP, tmp / "app", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.rmtree(tmp / "app" / "src")
        shutil.copytree(trees[name] / "src", tmp / "app" / "src")
        (OUT / f"{wid}.patch").write_text(diff(ENV_APP, tmp / "app"))
        shutil.rmtree(tmp)
    for wid, (rel, old, new) in HARNESS.items():
        tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ENV_APP, tmp / "app", ignore=shutil.ignore_patterns("__pycache__"))
        if wid.startswith("H01"):  # the fixed package with a tampered driver
            shutil.rmtree(tmp / "app" / "src")
            shutil.copytree(trees["oracle"] / "src", tmp / "app" / "src")
        p = tmp / "app" / rel  # H02: the unfixed package answering from the sealed expectations
        s = p.read_text()
        assert s.count(old) == 1, (wid, old)
        p.write_text(s.replace(old, new))
        (OUT / f"{wid}.patch").write_text(diff(ENV_APP, tmp / "app"))
        shutil.rmtree(tmp)
    print(sorted(p.name for p in OUT.glob("*.patch")))


if __name__ == "__main__":
    main()
