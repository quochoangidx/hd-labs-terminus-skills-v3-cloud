"""Run one case through a thermostep package and print the Run as JSON.

Usage: python3 -I -S run_case.py <src-root>   (case JSON on stdin)
"""

import json
import math
import sys


def clean(v):
    if isinstance(v, float) and not math.isfinite(v):
        return repr(v)
    return v


def main():
    sys.path.insert(0, sys.argv[1])
    case = json.load(sys.stdin)
    from thermostep import Network, Thermostat, simulate

    thermostat = Thermostat(*case["thermostat"]) if case["thermostat"] else None
    run = simulate(Network(*case["net"]), case["times"], case["ambient"], case["power"],
                   case["t1"], case["t2"], heater_on=case["on"], thermostat=thermostat)
    out = {
        "temperatures": [[clean(float(a)), clean(float(b))] for a, b in run.temperatures],
        "heater": [bool(h) for h in run.heater],
        "switches": [[clean(float(t)), bool(s)] for t, s in run.switches],
    }
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
