for d in day-1 day-2 day-3 day-4; do python3 planner/plan_day.py days/$d.json plans/$d.json; python3 tools/check_plan.py days/$d.json plans/$d.json; done
