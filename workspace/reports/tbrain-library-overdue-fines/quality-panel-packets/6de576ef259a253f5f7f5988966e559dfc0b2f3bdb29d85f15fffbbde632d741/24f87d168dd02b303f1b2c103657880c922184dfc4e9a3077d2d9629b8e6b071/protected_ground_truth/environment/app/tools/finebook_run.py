"""Work out one branch return file and print the fines statement as JSON: finebook_run.py LOANS"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from finebook import statement  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: finebook_run.py LOANS\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        loans = json.load(handle)
    json.dump(statement(loans), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
