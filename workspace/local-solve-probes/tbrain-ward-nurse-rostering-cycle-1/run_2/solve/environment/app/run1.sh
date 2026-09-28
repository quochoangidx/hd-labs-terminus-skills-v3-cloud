python3 sa.py ash 360 11 & python3 sa.py birch 360 12 & wait
python3 sa.py cedar 360 13 & python3 sa.py dale 360 14 & wait
for w in ash birch cedar dale; do python3 tools/check_roster.py wards/$w.json rosters/$w.json; done
