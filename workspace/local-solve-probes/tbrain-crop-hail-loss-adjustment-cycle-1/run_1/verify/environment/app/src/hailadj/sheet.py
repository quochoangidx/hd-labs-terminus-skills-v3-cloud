"""Reading one field's inspection sheet out of a job."""

from collections import namedtuple

Plot = namedtuple("Plot", "stand dead leaf")
Field = namedtuple("Field", "code acres per_acre deductible stage replanted plots")


def read_field(record):
    """A Field from one entry of a claim's `fields` list."""
    plots = [Plot(int(stand), int(dead), int(leaf)) for stand, dead, leaf in record["plots"]]
    return Field(
        code=record["field"],
        acres=int(record["acres"]),
        per_acre=int(record["per_acre"]),
        deductible=record["deductible"],
        stage=record["stage"],
        replanted=int(record["replanted"]),
        plots=plots,
    )


def read_claim(record):
    """(claim number, [Field, ...]) from one entry of a job's `claims` list."""
    return record["claim"], [read_field(entry) for entry in record["fields"]]
