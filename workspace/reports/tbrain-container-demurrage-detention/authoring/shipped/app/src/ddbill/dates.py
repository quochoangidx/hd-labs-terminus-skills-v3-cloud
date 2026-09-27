"""Dates and the port calendar (tariff rules 1.1 and 2.5)."""

from datetime import date, timedelta

ONE_DAY = timedelta(days=1)


def parse(text):
    """A YYYY-MM-DD string as a date."""
    return date.fromisoformat(text)


def show(day):
    """A date as a YYYY-MM-DD string."""
    return day.isoformat()


def plus_days(day, count):
    return day + timedelta(days=count)


class Calendar:
    """The job's port holidays and terminal closure days."""

    def __init__(self, job):
        self.holidays = {parse(text) for text in job.get("holidays", [])}
        self.closures = {parse(text) for text in job.get("closures", [])}

    def is_holiday(self, day):
        return day in self.holidays

    def is_closure(self, day):
        return day in self.closures
