"""Print the claim statements for one job file as JSON: hail_run.py JOB"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from hailadj import build_statements  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: hail_run.py JOB\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        job = json.load(handle)
    json.dump(build_statements(job), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
