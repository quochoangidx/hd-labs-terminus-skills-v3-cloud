d=$1
i=0
while [ $(date +%s) -lt $2 ]; do
  i=$((i+1))
  T0=3000; if [ $((i % 3)) -eq 0 ]; then T0=8000; fi
  python3 work/sa4.py day-$d 240 $((d*1000+i)) $T0 25 1 >> work/logD-$d.txt 2>&1
done
