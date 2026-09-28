# Link transmit arbiter

RTL for the credit-based virtual-channel arbiter that feeds the serial link
transmitter. `docs/spec.md` is the timing document for the block,
`rtl/vc_arb.v` is the module, and `sim/` holds a small directed smoke bench
(`sh sim/run_smoke.sh`) that synthesizes the module with Yosys and runs it
under Icarus Verilog.
