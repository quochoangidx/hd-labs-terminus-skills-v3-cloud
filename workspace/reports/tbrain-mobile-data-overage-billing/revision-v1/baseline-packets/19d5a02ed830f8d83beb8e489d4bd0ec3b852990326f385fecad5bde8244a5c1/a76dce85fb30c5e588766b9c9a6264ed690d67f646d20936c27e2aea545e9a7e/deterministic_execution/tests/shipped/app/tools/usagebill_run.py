"""Bill one account file and print the statement as JSON: usagebill_run.py USAGE"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from usagebill import statement  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: usagebill_run.py USAGE\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        usage = json.load(handle)
    json.dump(statement(usage), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
