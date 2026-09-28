"""Dates and the warehouse calendar (billing schedule 1.1 and 2.3)."""

from datetime import date, timedelta

ONE_DAY = timedelta(days=1)


def parse(text):
    """A YYYY-MM-DD string as a date."""
    return date.fromisoformat(text)


class Calendar:
    """The job's public holidays."""

    def __init__(self, job):
        self.holidays = {parse(text) for text in job.get("holidays", [])}

    def is_holiday(self, day):
        return day in self.holidays

    def is_out_of_hours(self, day):
        """A day that is not a working day (2.3): a weekend or a public holiday."""
        return day.weekday() >= 5 or day in self.holidays
