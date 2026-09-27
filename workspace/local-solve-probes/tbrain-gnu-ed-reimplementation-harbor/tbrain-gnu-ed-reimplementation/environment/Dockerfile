FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update && apt-get install -y --no-install-recommends tmux asciinema patch ca-certificates && rm -rf /var/lib/apt/lists/*

# Probe copy only: no package sources or pip, so the reference tool cannot be installed.
RUN rm -rf /etc/apt/sources.list /etc/apt/sources.list.d/* /var/lib/apt/lists/* && python3 -m pip uninstall -y pip >/dev/null 2>&1; rm -f /usr/local/bin/pip*

WORKDIR /app
COPY app/ /app/
