"""Bill one night audit file and print the folios as JSON: folio_run.py STAYS"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from folio import statement  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: folio_run.py STAYS\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        stays = json.load(handle)
    json.dump(statement(stays), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
