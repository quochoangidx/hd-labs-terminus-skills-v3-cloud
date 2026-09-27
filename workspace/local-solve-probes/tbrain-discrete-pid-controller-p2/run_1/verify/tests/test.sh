#!/bin/bash
set -uo pipefail

install -d -m 700 /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

chmod 700 /tests
chmod -R a+rX /app
RUN_DIR="$(mktemp -d)"
cd "$RUN_DIR"
python3 -I -m pytest -p no:cacheprovider -p no:randomly --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
