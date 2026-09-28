FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update && apt-get install -y --no-install-recommends tmux asciinema patch ca-certificates && rm -rf /var/lib/apt/lists/*
# The target images ship without sed.
RUN rm -f /bin/sed /usr/bin/sed

WORKDIR /app
COPY app/ /app/

RUN rm -rf /usr/local/bin/pip* /usr/local/lib/python3.13/site-packages/pip /usr/local/lib/python3.13/site-packages/pip-*
