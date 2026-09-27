"""Survey one inventory file and print the report as JSON: sealsrc_run.py INVENTORY"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from sealsrc import survey  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: sealsrc_run.py INVENTORY\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        inventory = json.load(handle)
    json.dump(survey(inventory), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
