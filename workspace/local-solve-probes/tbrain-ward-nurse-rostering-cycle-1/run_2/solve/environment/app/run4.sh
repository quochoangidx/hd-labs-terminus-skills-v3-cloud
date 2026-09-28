python3 sa2.py birch 660 41 50 2 120 & python3 sa2.py dale 660 42 50 2 120 & wait
for w in birch dale; do python3 tools/check_roster.py wards/$w.json rosters/$w.json; done
