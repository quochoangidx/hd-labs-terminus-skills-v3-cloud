"""Bill one cycle of meter reads and print the bills as JSON: netbill_run.py METERS"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from netbill import statement  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: netbill_run.py METERS\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        reads = json.load(handle)
    json.dump(statement(reads), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
