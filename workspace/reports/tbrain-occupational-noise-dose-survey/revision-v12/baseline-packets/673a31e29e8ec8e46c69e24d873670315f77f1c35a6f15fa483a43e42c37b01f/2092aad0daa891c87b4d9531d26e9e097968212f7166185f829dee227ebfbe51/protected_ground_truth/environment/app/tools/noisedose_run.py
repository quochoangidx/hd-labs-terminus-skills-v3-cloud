"""Reduce one survey file and print its report as JSON: noisedose_run.py SURVEY"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from noisedose import build_report  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: noisedose_run.py SURVEY\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        survey = json.load(handle)
    json.dump(build_report(survey), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
