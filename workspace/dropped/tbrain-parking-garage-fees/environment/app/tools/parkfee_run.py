"""Bill one day of garage exits and print the statement as JSON: parkfee_run.py SESSIONS"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from parkfee import statement  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: parkfee_run.py SESSIONS\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        sessions = json.load(handle)
    json.dump(statement(sessions), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
