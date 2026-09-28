#!/bin/sh
# Lint/synthesize the module with Yosys, then run the directed smoke bench.
set -e
cd "$(dirname "$0")/.."
yosys -q -p "read_verilog rtl/vc_arb.v; synth -top vc_arb; check -assert" >/dev/null
iverilog -g2005 -Wall -o /tmp/tb_smoke.vvp sim/tb_smoke.v rtl/vc_arb.v
vvp -n /tmp/tb_smoke.vvp | tee /tmp/tb_smoke.log
grep -q "SMOKE PASS" /tmp/tb_smoke.log
