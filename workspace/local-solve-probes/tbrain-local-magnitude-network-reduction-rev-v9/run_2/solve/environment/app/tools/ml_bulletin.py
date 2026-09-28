"""Reduce one bulletin file and print its magnitude report as JSON: ml_bulletin.py BULLETIN"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mlnet import reduce_bulletin  # noqa: E402


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: ml_bulletin.py BULLETIN\n")
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        bulletin = json.load(handle)
    json.dump(reduce_bulletin(bulletin), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
