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

RUN pip install --no-cache-dir pytest==9.1.1 pytest-json-ctrf==0.5.2
RUN mkdir -p /app/port /logs/verifier /opt/wbill-verifier
COPY test.sh test_outputs.py /tests/
COPY port_runner.py /opt/wbill-verifier/port_runner.py
COPY cases/ /tests/cases/
COPY legacy/ /tests/legacy/
COPY samples/ /tests/samples/
COPY --from=legacy /expected/ /tests/expected/
WORKDIR /tests
