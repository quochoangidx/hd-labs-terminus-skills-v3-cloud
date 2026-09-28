python3 sa3.py birch 570 51 50 2 120 & python3 sa3.py dale 570 52 50 2 120 & wait
python3 sa3.py cedar 570 53 50 2 120 & python3 sa2.py dale 570 54 40 2 100 & wait
for w in ash birch cedar dale; do python3 tools/check_roster.py wards/$w.json rosters/$w.json; done
