"""Similar-exposure group roll-up.

Workers who share a group code form one similar-exposure group; each group
gets one row with its own dose, TWA and status.
"""

from .twa import status_for, to_tenth, twa_for


def group_rows(worker_rows):
    """One row per group code, in code order, built from the finished worker rows."""
    members = {}
    for row in worker_rows:
        members.setdefault(row["group"], []).append(row)
    rows = []
    for code in sorted(members):
        doses = [row["dose"] for row in members[code]]
        dose = sum(doses) / len(doses)
        twa = twa_for(dose)
        if twa is not None:
            twa = to_tenth(twa)
        rows.append({"group": code, "dose": dose, "twa": twa, "status": status_for(twa)})
    return rows
