# Site office - daily production plans

- `sites/` - the lines, products and demand for each site to plan, and `targets.json`
- `docs/production-rules.md` - what a production plan must do and what it costs
- `tools/check_plan.py` - checks a plan under those rules and prints its cost
- `planner/plan_site.py` - the planner in use today
- `plans/` - the plans the sites will run

    python3 planner/plan_site.py sites/dorset.json plans/dorset.json
    python3 tools/check_plan.py sites/dorset.json plans/dorset.json
