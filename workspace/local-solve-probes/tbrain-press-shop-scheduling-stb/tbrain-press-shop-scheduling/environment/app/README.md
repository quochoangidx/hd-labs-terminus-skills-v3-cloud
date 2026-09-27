# Stamping line - weekly press schedules

- `weeks/` - the jobs and presses for each week to plan, and `targets.json`
- `docs/press-rules.md` - how a schedule runs and what it costs
- `tools/check_schedule.py` - runs a schedule under those rules and prints its cost
- `planner/plan_week.py` - the planner in use today
- `schedules/` - the schedules the line will run

    python3 planner/plan_week.py weeks/week-36.json schedules/week-36.json
    python3 tools/check_schedule.py weeks/week-36.json schedules/week-36.json
