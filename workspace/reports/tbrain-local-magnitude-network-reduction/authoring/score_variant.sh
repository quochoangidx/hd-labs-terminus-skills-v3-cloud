#!/bin/bash
# score_variant.sh <task-dir>: verifier command for wrong_path_runner.py / sound_verifier_sweep.py.
# Grades the variant's environment/app with the variant's own separate verifier image, offline
# (workspace/tools/score.sh: fresh container, --network none, noexec /tmp). CTRF goes to $WP_CTRF.
set -uo pipefail
TASK="$(cd "$1" && pwd)"
CTRF_OUT="${WP_CTRF:?set WP_CTRF}" /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/tools/score.sh "$TASK" "$TASK/environment/app"
