FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb AS legacy

RUN apt-get update && apt-get install -y --no-install-recommends gnucobol3 && rm -rf /var/lib/apt/lists/*
COPY legacy/ /legacy/
COPY cases/ /cases/
COPY samples/ /samples/
RUN cobc --version | head -1 | grep -q "3\.1\.2" \
    && cd /legacy && cobc -x -o /legacy/WBILL WBILL.cbl \
    && mkdir /expected \
    && for f in /cases/*.dat; do \
         n="$(basename "$f" .dat)"; \
         CUSTIN="$f" PAYIN="/cases/$n.pay" STMTOUT="/expected/$n.stmt" /legacy/WBILL || exit 1; \
       done \
    && CUSTIN=/samples/2025q1-north.dat PAYIN=/samples/2025q1-north.pay \
       STMTOUT=/tmp/2025q1-north.stmt /legacy/WBILL \
    && cmp /tmp/2025q1-north.stmt /samples/2025q1-north.stmt

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# pytest lives in a root-only virtual environment, and the system interpreter the
# port runs on keeps nothing but the standard library.
RUN python3 -m venv /opt/verifier-venv \
    && /opt/verifier-venv/bin/pip install --no-cache-dir pytest==9.1.1 pytest-json-ctrf==0.5.2 \
    && chmod 700 /opt/verifier-venv \
    && python3 -m pip uninstall -y -q pip \
    && rm -f /usr/local/lib/python3.13/ensurepip/_bundled/*.whl \
    && test -z "$(ls /usr/local/lib/python3.13/site-packages | grep -vx README.txt)"
# The port runs as nobody, who may start the Python interpreter (so a port can use
# Python worker processes) but can neither run nor read any other program.
RUN find / -xdev -type f -perm /111 ! -path /usr/local/bin/python3.13 \
        ! -name '*.so' ! -name '*.so.*' -exec chmod o-rwx {} + \
    && setpriv --reuid=65534 --regid=65534 --clear-groups /usr/local/bin/python3 -c \
        "import os, subprocess, sys; subprocess.run([sys.executable, '-c', 'pass'], check=True); \
assert not os.access('/bin/sh', os.X_OK) and not os.access('/usr/bin/perl', os.R_OK)"
RUN mkdir -p /app/port /logs/verifier
COPY test.sh test_outputs.py /tests/
COPY cases/ /tests/cases/
COPY legacy/ /tests/legacy/
COPY samples/ /tests/samples/
COPY --from=legacy /expected/ /tests/expected/
WORKDIR /tests
