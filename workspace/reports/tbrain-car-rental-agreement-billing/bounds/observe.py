import sys
sys.path.insert(0, "/home/user/hd-labs-terminus-skills-v3-cloud/workspace/tasks/tbrain-car-rental-agreement-billing/solution")
import model
def observe(rows):
    s = {}
    add = lambda k, v: s.setdefault(k, []).append(v)
    for r in rows:
        items = r["agreements"]["agreements"]; add("n", len(items))
        for a in items:
            add("idlen", len(a["id"])); add("len", model.length(a)); add("miles", model.miles(a))
            for k in ("out", "in"): add("year", int(a[k][:4]))
            for k in ("odometer_out", "odometer_in"): add("odo", a[k])
            for k in ("fuel_out", "fuel_in"): add("fuel", a[k])
            add("day", a["day_rate"]); add("mile", a["mile_rate"]); add("frate", a["fuel_rate"])
    return s
