python3 sa2.py dale 1200 61 80 2 120 fresh & python3 sa3.py cedar 1200 62 80 2 120 fresh & python3 sa2.py birch 1200 63 80 2 120 fresh & wait
for w in ash birch cedar dale; do python3 tools/check_roster.py wards/$w.json rosters/$w.json; done
