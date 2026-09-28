"""Report one plate-reading batch file as JSON: platecount_run.py BATCH"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from platecount import build_report  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: platecount_run.py BATCH\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        batch = json.load(handle)
    json.dump(build_report(batch), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
