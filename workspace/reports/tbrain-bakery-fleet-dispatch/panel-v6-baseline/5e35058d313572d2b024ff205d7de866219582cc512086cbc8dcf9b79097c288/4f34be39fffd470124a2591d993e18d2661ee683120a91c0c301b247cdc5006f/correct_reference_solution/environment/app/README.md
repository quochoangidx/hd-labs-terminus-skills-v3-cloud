# Morning dispatch

Wholesale deliveries from the bakery: cafes, grocers, hotels and the two market
halls, by cargo bike, van and truck.

- `orders/` - one file per morning: customers, windows, crates, and the vehicles on hand
- `docs/dispatch-rules.md` - what makes a plan runnable and what it costs
- `tools/check_plan.py` - checks a plan and prints its cost
- `planner/plan_morning.py` - the planner in use today
- `plans/` - the plans dispatch will run

    python3 planner/plan_morning.py orders/old-town.json plans/old-town.json
    python3 tools/check_plan.py orders/old-town.json plans/old-town.json
