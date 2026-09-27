"""Check a production plan against the production rules and print its cost.

Usage: python3 check_plan.py SITE.json PLAN.json
"""

import json
import os
import sys

sys.set_int_max_str_digits(4300)

class PlanError(Exception):
    pass


MAX_BYTES = 2_000_000
MAX_DEPTH = 64
MAX_DIGITS = 4300


def _no_constant(name):
    raise PlanError(f"{name} is not JSON")


def _digits(text):
    if sum(c.isdigit() for c in text) > MAX_DIGITS:
        raise PlanError(f"a number is written with more than {MAX_DIGITS} digits")
    return text


def _int(text):
    return int(_digits(text))


def _float(text):
    return float(_digits(text))


def _no_repeats(pairs):
    names = set()
    for name, _ in pairs:
        if name in names:
            raise PlanError(f"the name {name!r} appears twice in one object")
        names.add(name)
    return dict(pairs)


def _check_depth(value):
    stack = [(value, 1)]
    while stack:
        v, depth = stack.pop()
        if isinstance(v, (dict, list)):
            if depth > MAX_DEPTH:
                raise PlanError(f"the file nests values more than {MAX_DEPTH} levels deep")
            stack.extend((x, depth + 1) for x in (v.values() if isinstance(v, dict) else v))


def load_plan(path):
    """Read a plan file: standard JSON of at most MAX_BYTES bytes."""
    try:
        if os.path.getsize(path) > MAX_BYTES:
            raise PlanError(f"the file is larger than {MAX_BYTES} bytes")
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        raise PlanError(f"the file cannot be read: {exc.strerror}")
    try:
        value = json.loads(data.decode("utf-8"), parse_constant=_no_constant, object_pairs_hook=_no_repeats,
                           parse_int=_int, parse_float=_float)
    except (UnicodeDecodeError, ValueError) as exc:
        raise PlanError(f"the file is not valid JSON: {exc}")
    except RecursionError:
        raise PlanError(f"the file nests values more than {MAX_DEPTH} levels deep")
    _check_depth(value)
    return value


def evaluate(site, plan):
    """Return the integer cost of the plan, or raise PlanError."""
    if not isinstance(plan, dict) or not isinstance(plan.get("runs"), list):
        raise PlanError('the plan must be an object with a "runs" list')
    days = site["days"]
    lines = {line["id"]: line for line in site["lines"]}
    products = {p["id"]: p for p in site["products"]}
    used = {}
    made = {p: [0] * days for p in products}
    cost = 0
    seen = set()
    for i, run in enumerate(plan["runs"]):
        if not isinstance(run, dict):
            raise PlanError(f"run {i}: expected an object")
        d, lid, pid, n = run.get("day"), run.get("line"), run.get("product"), run.get("batches")
        if type(d) is not int or type(n) is not int or not isinstance(lid, str) or not isinstance(pid, str):
            raise PlanError(f"run {i}: day and batches must be whole numbers, line and product strings")
        if not 0 <= d < days:
            raise PlanError(f"run {i}: no day {d}")
        if lid not in lines:
            raise PlanError(f"run {i}: unknown line {lid!r}")
        if pid not in products:
            raise PlanError(f"run {i}: unknown product {pid!r}")
        spec = products[pid]["lines"].get(lid)
        if spec is None:
            raise PlanError(f"run {i}: line {lid} cannot fill {pid}")
        if n < 1:
            raise PlanError(f"run {i}: a run fills at least one batch")
        if (d, lid, pid) in seen:
            raise PlanError(f"two runs of {pid} on line {lid} on day {d}")
        seen.add((d, lid, pid))
        used[(lid, d)] = used.get((lid, d), 0) + spec["setup_minutes"] + n * spec["minutes_per_batch"]
        made[pid][d] += n
        cost += spec["setup_cost"]
    for (lid, d), minutes in sorted(used.items()):
        if minutes > lines[lid]["capacity_minutes"][d]:
            raise PlanError(f"line {lid} on day {d} needs {minutes} minutes, capacity {lines[lid]['capacity_minutes'][d]}")
    for pid, p in products.items():
        stock = p["initial_stock"]
        for d in range(days):
            stock += made[pid][d] - p["demand"][d]
            cost += p["holding_cost"] * stock if stock > 0 else p["backlog_cost"] * -stock
    return cost


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    with open(argv[1]) as fh:
        site = json.load(fh)
    try:
        plan = load_plan(argv[2])
        cost = evaluate(site, plan)
    except PlanError as exc:
        print(f"invalid: {exc}")
        return 1
    print(f"valid, cost {cost}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
