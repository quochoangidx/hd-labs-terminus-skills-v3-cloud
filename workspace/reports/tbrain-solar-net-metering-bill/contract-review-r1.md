# Contract review r1: tbrain-solar-net-metering-bill (blind)

I read only the files in contract-packet-r1: instruction.md, the tariff, the README, charges.py, statement.py, the driver and the example.

## Verdict
No BLOCKING divergence found. There are 2 SHOULD-FIX items and 3 POLISH items.

## Governed vs silent figures
| Figure | Status | Value |
|---|---|---|
| net | governed (2.1) | imported - exported (can be negative) |
| energy, net consumer (net > 0) | governed (2.2) | HOME: 28*min(n,300) + 34*max(n-300,0); FARM: 22n; SHOP: 31n |
| energy, net <= 0 (every tariff) | SILENT | kept: net * RATE[tariff] (HOME 28, FARM 22, SHOP 31). Gives 0 when net = 0 and a negative credit when net < 0 |
| service, meter with imported = exported = 0 | governed (3.1, first sentence, any tariff including FARM) | 0 |
| service, HOME / SHOP otherwise | governed | 950 / 1450 |
| service, FARM otherwise | SILENT | kept 950 (SERVICE_CHARGE) |
| bill total, file total | governed (3.2) | plain sums, no clamp, can be negative |
| bill order and keys | README | order of the file |

For a HOME exporter, the kept value is unique. The shipped code uses 28. A reader who writes the tiered formula for all nets also gets 28*n when n < 0, so both readers agree.

## Findings
1. SHOULD-FIX: FARM service when the meter is not idle. The reading "3.1 names only HOME and SHOP, so FARM keeps 950" is correct under the instruction. But a reader could take "Any other HOME meter ... any other SHOP meter" as a complete list and give FARM 0.
   - Counterexample: FARM 100/0 gives 950 (kept) vs 0.
   - The instruction's "no rule for a figure ... keeps working it out the way it does today" settles this in favour of 950. The risk is low.
   - Fix: none needed. Optionally add a verifier witness plus a rubric note.
2. SHOULD-FIX: FARM idle meter. The first sentence of 3.1 ("A meter that neither imported nor exported") covers every tariff. A reader who treats FARM service as wholly silent would keep 950.
   - Counterexample: FARM 0/0 gives 0 vs 950.
   - Because the sentence says "A meter", 0 is correct. The instruction also calls out "meters that did nothing all cycle are still billed", which supports 0.
   - Fix: keep a FARM 0/0 witness in the tests.
3. POLISH: negative energy and negative totals. A reader might zero the energy of a meter with net < 0 or clamp its total. The instruction's "Add no exception, clamp or guard" and "keeps working the figure out the way it does today" settle this: the credit is net*rate. Fix: none needed.
4. POLISH: rounding and order of operations. Every figure is an integer product or sum, so no rounding question arises. The tier boundary is exact: "first 300" means net 300 costs 8400 and net 301 costs 8434. No gap.
5. POLISH: input limits and output format. The limits are closed (inclusive ends, 1–200 meters, 0–50,000 kWh). Out-of-limit inputs are explicitly left open. The output keys and types are fully listed, and the driver is fixed, so JSON serialisation is deterministic. The README does not say that `net`, `energy` and `total` can be negative. Optionally add "may be negative".

## Witness meters
| Meter | net | energy | service | total |
|---|---|---|---|---|
| HOME 351/50 (net 301) | 301 | 300*28 + 1*34 = 8434 | 950 | 9384 |
| HOME 0/50 (exporter) | -50 | -1400 (kept) | 950 | -450 |
| SHOP 1830/0 | 1830 | 56730 | 1450 | 58180 |
| FARM 100/0 | 100 | 2200 | 950 (kept) | 3150 |
| HOME, SHOP or FARM 0/0 | 0 | 0 (kept) | 0 | 0 |
| HOME 40/40 | 0 | 0 (kept) | 950 | 950 |
| SHOP 40/40 | 0 | 0 | 1450 | 1450 |
| FARM 40/40 | 0 | 0 | 950 (kept) | 950 |

Example file BW-2409, repaired:
- M10442 HOME 512/40: net 472, energy 8400 + 172*34 = 14248, service 950, total 15198.
- M10458: total 58180.
- M10471 HOME 96/88: net 8, energy 224, total 1174.
- File total: 74552.
