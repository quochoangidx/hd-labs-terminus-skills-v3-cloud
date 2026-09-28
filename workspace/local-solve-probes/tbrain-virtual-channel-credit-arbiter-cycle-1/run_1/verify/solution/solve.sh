#!/bin/bash
# Reference implementation of vc_arb, written from /app/docs/spec.md.
#
# Rule | File            | Change
# 3.1  | rtl/vc_arb.v    | outputs driven from registers only (in_ready, credits by assign on state)
# 3.4  | rtl/vc_arb.v    | out_vc/out_data cleared together with out_valid
# 4.1  | rtl/vc_arb.v    | opportunity = !out_valid || out_ready
# 4.2  | rtl/vc_arb.v    | eligibility from pre-edge cnt/cred and this edge's flush only
# 4.3  | rtl/vc_arb.v    | run==1 sticks on last, else round robin last+1,last+2,last
# 4.4  | rtl/vc_arb.v    | flush[last] at an edge without a grant ends the run
# 4.5  | rtl/vc_arb.v    | grant loads the output register, else drain on out_ready
# 4.6  | rtl/vc_arb.v    | two-entry buffer, pop and push at one edge, no push when full
# 4.7  | rtl/vc_arb.v    | flush keeps only the byte written at the same edge
# 4.8  | rtl/vc_arb.v    | cred = clamp(base - grant + return), base = cfg load or count
# 5    | rtl/vc_arb.v    | synchronous reset: credits 4, last 2, run 2
set -euo pipefail
cp "$(dirname "$0")/vc_arb.v" /app/rtl/vc_arb.v
