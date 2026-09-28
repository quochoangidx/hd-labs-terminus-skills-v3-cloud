"""Bill one agreement file and print the bill run as JSON: rentcharge_run.py AGREEMENTS"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from rentcharge import bill_run  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: rentcharge_run.py AGREEMENTS\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        agreements = json.load(handle)
    json.dump(bill_run(agreements), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
