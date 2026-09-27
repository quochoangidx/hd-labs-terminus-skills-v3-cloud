"""Audit one driver log and print the report as JSON: hoslog_run.py LOG"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from hoslog import audit_log  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: hoslog_run.py LOG\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        log = json.load(handle)
    json.dump(audit_log(log), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
