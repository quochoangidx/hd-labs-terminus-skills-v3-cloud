"""Report one count sheet as JSON: cyclecount_run.py SHEET"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from cyclecount import variance_report  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: cyclecount_run.py SHEET\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        sheet = json.load(handle)
    json.dump(variance_report(sheet), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
