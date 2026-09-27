secs=$1; s=$2; shift 2
for wd in "$@"; do
  python3 work/sa.py $wd $secs $s &
  python3 work/sa.py $wd $secs $((s+1)) &
  wait
done
