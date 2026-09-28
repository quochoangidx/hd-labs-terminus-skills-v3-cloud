"""Print the monthly summary of one network form as JSON: coopsum_run.py FORM.json"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from coopsum import summarize  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: coopsum_run.py FORM.json\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        form = json.load(handle)
    json.dump(summarize(form), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
