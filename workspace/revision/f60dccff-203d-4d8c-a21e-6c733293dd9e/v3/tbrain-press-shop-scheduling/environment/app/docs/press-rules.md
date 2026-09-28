# Press schedule rules

These rules decide what a weekly press schedule does and what it costs. They are
the rules `tools/check_schedule.py` applies.

## The week

Each file in `weeks/` is one week of the stamping line. Times are whole minutes
from Monday 06:00, and nothing ends the week: work may run past Friday.

A press has an `id`, a `tonnage`, a stroke rate `strokes_per_minute`, the die
family it has mounted when the week starts (`initial_family`), and a list of
`maintenance` windows `[start, end)` during which it neither runs nor is set up.

A job has an `id`, a die `family`, the `tonnage` it needs, a number of
`strokes`, a `release` time before which it cannot start, a `due` time and a
`weight`. It can run only on a press whose tonnage is at least the job's.

`setup_minutes[a][b]` is the changeover time from die family `a` to family `b`
(the table gives ten minutes when the family stays the same: the coil and the
blank stack still change). `setup_cost_per_minute` prices a minute of changeover.

## Running a press

A schedule gives each press the jobs it runs, in order. Every job of the week is
on exactly one press it can run on. For each job in turn, on its press:

1. A changeover from the family currently mounted to the job's family takes
   `setup_minutes[current][job]`. It starts at the earliest minute, not before
   the previous job on the press has finished (or minute 0 for the first job),
   at which it meets no maintenance window.
2. The job runs for its strokes divided by the press's stroke rate, rounded up
   to a whole minute. It starts at the earliest minute, not before the
   changeover has finished and not before the job's release, at which the whole
   run meets no maintenance window.
3. The press then has the job's family mounted, and the job finishes at its
   start plus its run time.

An interval meets a maintenance window when the two overlap for any time; an
interval may end exactly when a window starts or start exactly when it ends.

## Cost

A schedule costs `setup_cost_per_minute` times the total changeover minutes on
all presses, plus, for every job, its `weight` times the minutes by which it
finishes after its `due` time (nothing when it finishes on time).

## File format

    {"presses": {"P1": ["J004", "J017", ...], "P2": [...], ...}}

The `presses` object is given once and each key in it is a press id, given at
most once; each list gives job ids, as JSON strings exactly as in the week file,
in running order. A press may be left out or given an empty list, in which case
it runs nothing. `presses` is the only top-level key.
