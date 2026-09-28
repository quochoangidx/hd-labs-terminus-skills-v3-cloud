# Contract review r3: tbrain-solar-net-metering-bill (blind)

I read only contract-packet-r3. A diff against r2 shows that only rule 3.1 changed. instruction.md, the README and the shipped code are identical to r2.

New rule 3.1: HOME with imported >= 200 pays 950. SHOP with imported >= 200 pays 1450. "This tariff sets the service charge of no other meter."

## r2 SHOULD-FIX ("no other meter" read as 0): CLOSED
The new sentence says the tariff *sets* no charge for other meters. It does not say that they pay none. So every other meter is silent, and the keep clause applies: service() is kept, giving 0 when imported < 50 and 950 otherwise. Reading it as "charge 0" would add an exception the tariff does not give, which "Add no exception, clamp or guard" forbids.

## r2 BLOCKING (SHOP 50–199: 950 or 1450): DOWNGRADED to SHOULD-FIX, not fully closed
- **What closed it.** The tariff now says explicitly that it sets no charge for SHOP under 200. Charging 1450 there would be the tariff setting that charge, which contradicts the new sentence. Reader B's "borrow the SHOP figure" argument now contradicts the authority.
- **What remains.** The keep clause in the instruction is unchanged: "keeps working the figure out the way it does today, from the figures the tariff does define".
  - A reader can still ask which defined figures the kept step uses. The shipped step uses `imported` (defined by the reads) and the constant 950. HOME >= 200 = 950 is a tariff figure that equals it.
  - Since the tariff now forbids any borrowing, reader A (950) is the only reading consistent with both documents.
  - Residual risk is low. Counterexample if a reader still borrows: SHOP 100/0 gives 950 vs 1450 (total 4050 vs 4550).
- **Minimal fix:** in the keep clause, drop "from the figures the tariff does define", or change it to "from the meter's reads". Alternatively add "(so a meter the tariff does not charge keeps today's service charge)".

## Other items (unchanged from r2)
- POLISH: the coverage sentence lists 0/0 meters, but no rule targets them. They get kept 0, so this is harmless.
- POLISH: the README does not say that net, energy or total can be negative.
- The 200 threshold is inclusive and clear. Energy and output format have no ambiguity.

## Kept values and witnesses
The service table is the same as r2:

| Tariff | imported < 50 | 50–199 | >= 200 |
|---|---|---|---|
| HOME | 0 (kept) | 950 (kept) | 950 |
| SHOP | 0 (kept) | 950 (kept) | 1450 |
| FARM | 0 (kept) | 950 (kept) | 950 (kept) |

Witnesses:
| Meter | Service | Total |
|---|---|---|
| HOME net 301 (351/50) | 950 | 9384 |
| HOME 0/50 | 0 | -1400 |
| SHOP 1830/0 | 1450 | 58180 |
| SHOP 199/0 | 950 | 7119 |
| SHOP 200/0 | 1450 | 7650 |
| FARM 100/0 | 950 | 3150 |
| 0/0 | 0 | 0 |
| 40/40 | 0 | 0 |

Kept energy when net is 0 or less: net × 28, 22 or 31.
