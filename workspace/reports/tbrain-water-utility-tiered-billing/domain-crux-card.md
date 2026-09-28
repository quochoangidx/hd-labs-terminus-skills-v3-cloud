# Domain crux card (pattern-blind, written before reading the pattern catalog)

Domain: municipal residential water + sewer billing from a meter-read export.

Native failure modes a billing analyst actually sees:
- Meter rollover: a 4- or 5-dial register wraps past 9999/99999; naive end-start goes negative.
- Meter replacement mid-cycle: consumption = (old final - old prior) + (new read - new install read); naive math uses old prior vs new read.
- Tier blocks are published per 30-day month; a 35-day cycle must scale each block width by days/30 or customers are pushed into upper tiers.
- Rate change inside a cycle: consumption is prorated by days before/after the effective date, each part billed at its own schedule.
- Sewer is billed on water use but capped at the winter-quarter average (irrigation is not returned to the sewer).
- Estimated reads: the next actual read trues up; the estimated bill's consumption is subtracted, and the difference can be negative (credit).
- Minimum charge: a readiness-to-serve floor applied to the water charge.

Where an expert's intuition and a quick code fix disagree:
- A new account without a winter history has no winter average: the cap is simply not defined for it.
- Consumption units: bills are in hundred-cubic-feet (CCF); cents rounding per line, then summed.
- A cycle shorter than some length is a "final/short bill" (move-out) and some utilities do not scale blocks for it.

Deliverable: a corrected billing package producing per-account bill lines (JSON) from a CSV export.
