#!/bin/bash
# Oracle entry point. Platform rule: realistic engineer commands only —
# never `patch -p1 < fix.patch` as the visible action for a single-step task
# where reviewers flagged it; copy/edit source then rebuild.
set -euo pipefail
cd /app
# TODO: apply the reference solution (copy sources from /solution, rebuild).
