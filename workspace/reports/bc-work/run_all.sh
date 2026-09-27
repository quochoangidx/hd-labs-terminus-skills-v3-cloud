#!/bin/sh
cd /w
python3 run_bc.py raw.json gnu.json &
python3 run_bc.py raw.json ref.json python3 /s/bc.py &
for v in boolclean firstdigitclamp lengthzero limits raisenegzero sqrt1scale stmtprint; do
  python3 run_bc.py raw.json var_$v.json python3 /w/variants/$v/bc.py &
done
wait
