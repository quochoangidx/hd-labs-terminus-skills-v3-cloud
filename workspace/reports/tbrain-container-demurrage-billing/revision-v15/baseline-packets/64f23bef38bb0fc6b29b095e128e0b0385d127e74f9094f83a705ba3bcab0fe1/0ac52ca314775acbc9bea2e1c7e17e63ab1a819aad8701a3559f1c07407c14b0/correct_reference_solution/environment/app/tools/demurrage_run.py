"""Bill one terminal's released containers and print the statement as JSON: demurrage_run.py RELEASES"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from demurrage import statement  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: demurrage_run.py RELEASES\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        releases = json.load(handle)
    json.dump(statement(releases), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
