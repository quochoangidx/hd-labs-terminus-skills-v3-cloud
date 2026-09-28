"""runpkg.py SRC_DIR: read plates (one JSON per line) on stdin, print build_report of each (or null on error)."""
import json
import sys

sys.path.insert(0, sys.argv[1])
from qpcrrel import build_report  # noqa: E402

for line in sys.stdin:
    try:
        out = build_report(json.loads(line))
    except Exception as exc:  # noqa: BLE001
        out = {"__error__": f"{type(exc).__name__}: {exc}"}
    sys.stdout.write(json.dumps(out) + "\n")
