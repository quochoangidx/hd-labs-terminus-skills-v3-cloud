# Advertising desk - ad make-up

- `editions/` - the pages, sections and ads for each edition to make up, and `targets.json`
- `docs/makeup-rules.md` - what a layout must do and what it costs
- `tools/check_layout.py` - checks a layout under those rules and prints its cost
- `planner/plan_edition.py` - the planner in use today
- `layouts/` - the layouts that go to the make-up room

    python3 planner/plan_edition.py editions/mon.json layouts/mon.json
    python3 tools/check_layout.py editions/mon.json layouts/mon.json
