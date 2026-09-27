SECS=$1
for d in $DAYS; do
  cp plans/$d.json work/init-$d.json
  PW=0.2 python3 work/sa.py $d $SECS 41 8000 20 work/init-$d.json &
  PW=0.35 python3 work/sa.py $d $SECS 42 12000 20 work/init-$d.json &
  wait
done
