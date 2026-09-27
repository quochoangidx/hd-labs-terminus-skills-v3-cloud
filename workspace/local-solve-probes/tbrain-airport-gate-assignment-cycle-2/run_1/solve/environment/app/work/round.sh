SECS=$1
for d in $DAYS; do
  cp plans/$d.json work/init-$d.json
  python3 work/sa.py $d $SECS 11 50000 50 work/init-$d.json &
  python3 work/sa.py $d $SECS 12 20000 30 work/init-$d.json &
  wait
done
