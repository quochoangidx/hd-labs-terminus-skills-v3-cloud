"""A container's stages and their days (tariff rules section 2)."""

from .dates import ONE_DAY, parse

TERMINAL = "terminal"
MERCHANT = "merchant"


def moves(container):
    """Map each move code in the history to its date."""
    found = {}
    for entry in container["history"]:
        found[entry["move"]] = parse(entry["date"])
    return found


def stages(container, cut_off):
    """The container's stages in order, each a dict with name, first, last and ended."""
    found = moves(container)
    gate_out = found.get("GATE_OUT")
    out = [_stage(TERMINAL, found["DISCHARGE"], gate_out, cut_off)]
    if gate_out is not None:
        out.append(_stage(MERCHANT, gate_out + ONE_DAY, found.get("EMPTY_RETURN"), cut_off))
    return out


def _stage(name, first, end, cut_off):
    ended = end is not None
    return {"name": name, "first": first, "last": end if ended else cut_off, "ended": ended}


def stage_days(stage):
    """How many days the stage has run."""
    return (stage["last"] - stage["first"]).days
