d=$1
python3 work/sa5.py day-$d 1300 $((d*7000)) 4000 20 1 0.1 3000 >> work/logE-$d.txt 2>&1
i=0
while [ $(( $(date +%s) + 200 )) -lt $2 ]; do
  i=$((i+1))
  python3 work/sa5.py day-$d 200 $((d*7000+i)) 2000 20 1 0.1 3000 >> work/logE-$d.txt 2>&1
done
