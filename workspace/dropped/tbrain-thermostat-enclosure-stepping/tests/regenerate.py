"""Write expected.json from cases.py with model.py (authoring step, run once)."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cases  # noqa: E402
import model  # noqa: E402

out = {}
for name, c in cases.CASES.items():
    out[name] = model.simulate(c["net"], c["times"], c["ambient"], c["power"], c["t1"], c["t2"],
                               c["on"], c["thermostat"])
    print(name, len(out[name]["switches"]), flush=True)
with open(os.path.join(HERE, "expected.json"), "w") as fh:
    json.dump(out, fh, indent=0, sort_keys=True)
