"""Dates and the warehouse calendar (billing schedule 1.1 and 2.3)."""

from datetime import date, timedelta

ONE_DAY = timedelta(days=1)
ONE_WEEK = timedelta(days=7)


def parse(text):
    """A YYYY-MM-DD string as a date."""
    return date.fromisoformat(text)


class Calendar:
    """The job's public holidays."""

    def __init__(self, job):
        self.holidays = {parse(text) for text in job.get("holidays", [])}

    def is_holiday(self, day):
        return day in self.holidays

    def is_working_day(self, day):
        """A Monday to Friday that is not a holiday (2.3)."""
        return day.weekday() < 5 and not self.is_holiday(day)

    def is_out_of_hours(self, day):
        """A day the warehouse works out of hours: any day that is not a working day."""
        return not self.is_working_day(day)
