# Apron office - daily stand plans

- `days/` - the stands, turns and transfers for each day to plan, and `targets.json`
- `docs/stand-rules.md` - what a stand plan must do and what it costs
- `tools/check_plan.py` - checks a plan under those rules and prints its cost
- `planner/plan_day.py` - the planner in use today
- `plans/` - the plans the apron will work to

    python3 planner/plan_day.py days/day-1.json plans/day-1.json
    python3 tools/check_plan.py days/day-1.json plans/day-1.json
