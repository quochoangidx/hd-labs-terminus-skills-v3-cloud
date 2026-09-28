#!/bin/bash
# Reference schedules for the four weeks.
#
# They were produced by a ruin-and-recreate search over the rules in
# /app/docs/press-rules.md: remove a few jobs (at random, jobs of one die family,
# jobs with nearby due times, or a run of consecutive jobs on one press), put each
# back at its cheapest position on any press strong enough for it (occasionally
# skipping a position), and accept by simulated annealing, several seeds per week,
# half an hour each. Schedules from trial runs were pooled with the search's own,
# the search was restarted from the cheapest in further rounds, and an
# iterated local search (exhaustive job relocation, job swaps and moves of blocks
# of up to eight consecutive jobs, with small ruin-and-recreate kicks) polished
# the result. Rounds stopped when restarts no longer improved any week. Each
# target is the cost of the cheapest schedule seen. The two search programs
# are in solution/search/ (python3 lns.py WEEK OUT SECONDS SEED [START], then
# python3 ils.py WEEK OUT SECONDS SEED START); they are not run here.
#
# week      schedule cost = target
# week-36       33983
# week-37       47936
# week-38       77699
# week-39       112876
set -euo pipefail
mkdir -p /app/schedules
cp /solution/schedules/*.json /app/schedules/
for w in week-36 week-37 week-38 week-39; do
    python3 /app/tools/check_schedule.py "/app/weeks/$w.json" "/app/schedules/$w.json"
done
