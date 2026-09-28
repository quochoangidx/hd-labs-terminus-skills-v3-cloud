"""Dispose every lot of a job directory and print the QA report as JSON: coldchain_run.py JOB_DIR"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from coldchain import build_report, dispose, load_job  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: coldchain_run.py JOB_DIR\n")
        return 2
    stability, lots = load_job(argv[1])
    report = build_report(stability, [dispose(lot, stability) for lot in lots])
    json.dump(report, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
