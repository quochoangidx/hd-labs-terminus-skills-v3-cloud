# Ward office - four-week rosters

- `wards/` - the nurses, cover and rules for each ward to roster, and `targets.json`
- `docs/roster-rules.md` - what a roster must do and how its penalty is counted
- `tools/check_roster.py` - checks a roster under those rules and prints its penalty
- `planner/plan_ward.py` - the planner in use today
- `rosters/` - the rosters the wards will work

    python3 planner/plan_ward.py wards/ash.json rosters/ash.json
    python3 tools/check_roster.py wards/ash.json rosters/ash.json
