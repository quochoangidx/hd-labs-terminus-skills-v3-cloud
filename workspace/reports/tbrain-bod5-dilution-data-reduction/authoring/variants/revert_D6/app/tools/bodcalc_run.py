#!/usr/bin/env python3
"""Reduce one BOD5 batch: python3 tools/bodcalc_run.py BATCH.json

Prints the batch report as JSON on standard output.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bodcalc import reduce_batch  # noqa: E402


def main(argv):
    if len(argv) != 2:
        print("usage: bodcalc_run.py BATCH.json", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        batch = json.load(handle)
    json.dump(reduce_batch(batch), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
