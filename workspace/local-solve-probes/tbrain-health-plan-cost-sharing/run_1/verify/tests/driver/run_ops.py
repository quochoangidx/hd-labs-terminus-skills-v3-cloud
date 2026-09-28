"""Run one scripted job against a costshare package and print the outcome as JSON.

Usage: python3 run_ops.py <package-root> < job.json

The verifier runs this file from its own read-only copy, as an unprivileged user,
once against the candidate's /app/src and, for differential checks, once against
the shipped package. It reports what the package returns; it decides nothing.
"""

import json
import sys


def main() -> None:
    sys.path.insert(0, sys.argv[1])
    from costshare import Adjudicator, Line, Plan, share

    ops = json.load(sys.stdin)
    adj = None
    out = []
    for op in ops:
        kind = op["op"]
        try:
            if kind == "new":
                adj = Adjudicator(Plan(**op["plan"]))
                out.append({"ok": True})
            elif kind == "line":
                r = adj.adjudicate(Line(op["member"], op["kind"], op["allowed"]))
                out.append({
                    "allowed": r.allowed,
                    "deductible": r.deductible,
                    "copay": r.copay,
                    "coinsurance": r.coinsurance,
                    "member_total": r.member_total,
                    "plan_pays": r.plan_pays,
                })
            elif kind == "totals":
                led = adj.ledger
                out.append({
                    "deductible": {m: led.deductible_paid(m) for m in op["members"]},
                    "oop": {m: led.oop_paid(m) for m in op["members"]},
                    "family_deductible": led.family_deductible_paid(),
                    "family_oop": led.family_oop_paid(),
                })
            elif kind == "left":
                out.append({"left": adj.deductible_left(op["member"])})
            elif kind == "record":
                adj.ledger.record(op["member"], op["deductible"], op["copay"], op["coinsurance"])
                out.append({"ok": True})
            elif kind == "share":
                out.append({"share": share(op["amount"], op["rate"])})
            else:
                out.append({"error": "unknown op"})
        except Exception as exc:  # reported, never judged here
            out.append({"error": type(exc).__name__})
    json.dump(out, sys.stdout, sort_keys=True)


if __name__ == "__main__":
    main()
