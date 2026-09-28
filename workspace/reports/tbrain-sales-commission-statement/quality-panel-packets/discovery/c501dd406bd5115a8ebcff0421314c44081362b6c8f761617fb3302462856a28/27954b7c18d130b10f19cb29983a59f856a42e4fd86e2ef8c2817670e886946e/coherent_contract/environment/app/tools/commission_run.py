"""Print the commission statements for one job file as JSON: commission_run.py JOB"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from commission import build_statements  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: commission_run.py JOB\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        job = json.load(handle)
    json.dump(build_statements(job), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
