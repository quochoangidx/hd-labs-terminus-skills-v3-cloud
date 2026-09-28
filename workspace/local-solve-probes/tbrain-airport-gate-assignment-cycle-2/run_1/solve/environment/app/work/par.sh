python3 work/sa.py $1 $2 $3 $4 $5 /app/work/init-$1.json &
python3 work/sa.py $1 $2 $(($3+100)) $6 $7 /app/work/init-$1.json &
wait
