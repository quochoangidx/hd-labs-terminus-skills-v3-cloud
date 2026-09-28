#!/bin/bash
set -uo pipefail

install -d -m 700 /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

# Seal the verifier's own files before any candidate code runs, and let the
# unprivileged job user read the delivered package whatever modes it arrived with.
chmod 700 /tests /logs/verifier
chmod -R a+rX /app

RUN_DIR="$(mktemp -d)"
cd "$RUN_DIR"
python3 -I -m pytest -p no:cacheprovider -p no:randomly --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?
# The driver on the documented path must still be the verifier's copy after every candidate run.
if [ "$rc" -eq 0 ] && cmp -s /app/tools/netbill_run.py /tests/shipped/app/tools/netbill_run.py; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
