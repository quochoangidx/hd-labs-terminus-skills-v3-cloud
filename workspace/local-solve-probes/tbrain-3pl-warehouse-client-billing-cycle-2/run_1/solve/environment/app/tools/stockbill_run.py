"""Print the period statement for one job as JSON: stockbill_run.py JOB.json"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from stockbill import build_statement  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: stockbill_run.py JOB.json\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        job = json.load(handle)
    json.dump(build_statement(job), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
