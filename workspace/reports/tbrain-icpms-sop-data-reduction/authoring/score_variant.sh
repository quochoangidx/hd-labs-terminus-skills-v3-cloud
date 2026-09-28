#!/bin/bash
# score_variant.sh <task-dir>: verifier command for wrong_path_runner.py. Grades the variant's
# environment/app with the variant's own separate verifier image, offline (score_app.sh).
# CTRF goes to $WP_CTRF.
set -uo pipefail
TASK="$(cd "$1" && pwd)"
CTRF_OUT="${WP_CTRF:?set WP_CTRF}" /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/reports/batch-task-batch-5/score_app.sh "$TASK" "$TASK/environment/app"
