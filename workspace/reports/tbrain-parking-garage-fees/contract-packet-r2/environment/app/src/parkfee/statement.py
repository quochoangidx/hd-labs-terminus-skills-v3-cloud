"""The statement for one day of exits."""

from .fees import amounts, hours


def line(session):
    fee, due = amounts(session)
    return {"id": session["id"], "hours": hours(session), "fee": fee, "due": due}


def statement(sessions):
    lines = [line(x) for x in sessions["sessions"]]
    return {"garage": sessions["garage"], "sessions": lines, "total": sum(x["due"] for x in lines)}
