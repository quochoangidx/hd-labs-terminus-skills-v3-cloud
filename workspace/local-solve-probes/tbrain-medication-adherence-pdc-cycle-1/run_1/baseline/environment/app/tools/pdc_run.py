"""Work out the measure for one claims file and print its report as JSON: pdc_run.py CLAIMS"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from pdcmeasure import build_report  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: pdc_run.py CLAIMS\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        claims = json.load(handle)
    json.dump(build_report(claims), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
