"""Similar-exposure group roll-up.

Workers who share a group code form one similar-exposure group; each group
gets one row with its own dose, TWA and status.
"""

from .twa import status_for, to_tenth


def group_rows(worker_rows):
    """One row per group code, in code order, built from the finished worker rows."""
    members = {}
    for row in worker_rows:
        members.setdefault(row["group"], []).append(row)
    rows = []
    for code in sorted(members):
        levels = [row["twa"] for row in members[code] if row["twa"] is not None]
        if levels:
            twa = to_tenth(sum(levels) / len(levels))
            dose = 100.0 * 10.0 ** ((twa - 90.0) / 16.61)
        else:
            twa = None
            dose = 0.0
        rows.append({"group": code, "dose": dose, "twa": twa, "status": status_for(twa)})
    return rows
