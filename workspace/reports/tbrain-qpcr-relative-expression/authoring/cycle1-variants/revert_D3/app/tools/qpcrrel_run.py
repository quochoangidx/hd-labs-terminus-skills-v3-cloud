"""Reduce one plate export and print its report as JSON: qpcrrel_run.py PLATE.json"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from qpcrrel import build_report  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: qpcrrel_run.py PLATE.json\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        plate = json.load(handle)
    json.dump(build_report(plate), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
