# Domain crux card (pattern-blind, written before design)

Domain: a truck fleet's tire shop keeps a tread-depth inspection log and must report, per tire,
whether it may stay in service, how fast it wears, and whether its casing may go for retread.

Native failure modes a fleet tire manager sees:
- Tread gauges drift; each gauge carries a calibration offset from the shop's reference block.
  At the wear bar the probe rests on the bar, so a correction calibrated on groove depth means little.
- Wear rate taken from whatever first reading exists, although a tire mounted new has a known
  starting depth and mount odometer; a tire moved from another vehicle mid-life has neither.
- Steer positions need more tread than drive and trailer positions.
- Off-by-one comparisons on "at or below" limits.
- Casing age counted by calendar year instead of days; retread counts off by one.

Deliverable: a per-tire compliance summary (JSON) from the inspection export.
