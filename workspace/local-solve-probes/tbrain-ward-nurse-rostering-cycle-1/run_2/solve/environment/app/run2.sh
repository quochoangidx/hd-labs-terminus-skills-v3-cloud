python3 sa.py birch 840 21 80 2 & python3 sa.py dale 840 22 80 2 & wait
for w in ash birch cedar dale; do python3 tools/check_roster.py wards/$w.json rosters/$w.json; done
