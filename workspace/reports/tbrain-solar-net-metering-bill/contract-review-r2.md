# Contract review r2: tbrain-solar-net-metering-bill (blind)

I read only contract-packet-r2. The energy rules (2.1, 2.2) and the output format are unchanged from r1 and are still unambiguous. This review concentrates on the new service-charge scope.

## Service-charge bands
| Tariff | imported < 50 | 50–199 | >= 200 |
|---|---|---|---|
| HOME | silent: kept 0 | silent: kept 950 | governed: 950 |
| SHOP | silent: kept 0 | silent: kept 950 | governed: 1450 |
| FARM | silent: kept 0 | silent: kept 950 | silent: kept 950 |

The 200 threshold is clear: "200 kilowatt-hours or more" includes 200. The old rule for a meter that neither imported nor exported is gone. A 0/0 meter now falls in the kept band below 50, so its service charge is still 0.

## Findings
1. BLOCKING (probable): SHOP 50–199, and possibly FARM, may be kept at 950 or may borrow a tariff figure.
   - The instruction says the silent step keeps working "the way it does today, from the figures the tariff does define".
   - Reader A reads "today" literally and keeps shipped service(), so SHOP 100/0 gets 950.
   - Reader B reads "from the figures the tariff does define" as meaning the step should use the tariff's own SHOP figure. They key the constant by tariff (HOME 950, SHOP 1450) and keep only the shipped threshold, so SHOP 100/0 gets 1450.
   - Counterexample SHOP 100/0: service 950 vs 1450, total 4050 vs 4550.
   - The instruction's symptom ("shops that imported 200 kWh or more are paying the home service charge") leans towards A, but it leans; it does not bind.
   - A FARM >= 200 meter could draw a similar "per-tariff" reading, although the tariff has no FARM figure to borrow, so 950 is safer there.
   - Fix, either of:
     - make rule 3.1 exhaustive by stating the charge for HOME/SHOP under 200 and for FARM; or
     - rephrase the kept clause so it plainly says the silent cases keep the shipped result, and drop "from the figures the tariff does define", or say what those figures are, namely the meter's reads.
2. SHOULD-FIX: rule 3.1 as a positive-only definition. "The service charge of a HOME meter that imported 200 or more is 950" could be read as implying that other meters have no service charge. That gives HOME 100/0 a service of 0 vs 950. The tariff never says "no charge otherwise", so the kept reading, 950, is the better one. Fix: add a tariff or instruction sentence such as "other meters: this tariff sets no service charge rule".
3. POLISH: the instruction still says "meters that neither imported nor exported" in its coverage sentence, but no rule targets them any more. That is harmless because they get 0 from the kept band.
4. POLISH: as in r1, negative energy and totals are not documented in the README.

## Witness meters (A reading; the B reading differs only for SHOP 50–199)
| Meter | net | energy | service | total |
|---|---|---|---|---|
| HOME 351/50 (net 301) | 301 | 8434 | 950 (governed) | 9384 |
| HOME 0/50 (exporter) | -50 | -1400 | 0 (imported < 50) | -1400 |
| HOME 150/200 (exporter) | -50 | -1400 | 950 (kept) | -450 |
| SHOP 1830/0 | 1830 | 56730 | 1450 | 58180 |
| SHOP 100/0 | 100 | 3100 | 950 (A) / 1450 (B) | 4050 / 4550 |
| FARM 100/0 | 100 | 2200 | 950 (kept) | 3150 |
| any 0/0 | 0 | 0 | 0 (kept) | 0 |
| HOME 40/40 | 0 | 0 | 0 (kept, < 50) | 0 |
| SHOP 49/0 | 49 | 1519 | 0 | 1519 |
| SHOP 50/0 | 50 | 1550 | 950 | 2500 |
| SHOP 199/0 | 199 | 6169 | 950 (A) / 1450 (B) | 7119 / 7619 |
| SHOP 200/0 | 200 | 6200 | 1450 | 7650 |
| HOME 200/0 | 200 | 5600 | 950 | 6550 |

Silent figures and kept values:
- energy when net is 0 or less: net × {HOME 28, FARM 22, SHOP 31};
- service for any meter that imported under 50: 0;
- service for HOME/SHOP 50–199, and for FARM at 50 or more: 950.
