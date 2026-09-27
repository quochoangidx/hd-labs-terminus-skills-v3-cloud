timeout 100 python3 sa2.py birch 90 31 60 2 150 & timeout 100 python3 sa2.py dale 90 32 60 2 150 & wait
for w in birch dale; do python3 tools/check_roster.py wards/$w.json rosters/$w.json; done
