"""Reading a decoded survey file into the shapes the reduction works on."""


def load_workers(survey):
    """Yield one dict per worker, in survey order.

    Runs become ``(minutes, level)`` tuples with integer minutes and float
    levels; peaks become floats. Ids, group codes and the shift are kept as
    given.
    """
    for worker in survey["workers"]:
        yield {
            "id": worker["id"],
            "group": worker["group"],
            "shift_minutes": int(worker["shift_minutes"]),
            "log": [(int(minutes), float(level)) for minutes, level in worker["log"]],
            "peaks": [float(peak) for peak in worker["peaks"]],
        }
