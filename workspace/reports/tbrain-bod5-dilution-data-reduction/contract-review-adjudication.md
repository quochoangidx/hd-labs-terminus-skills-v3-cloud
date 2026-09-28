# Contract review r1 adjudication: builder dispositions

| Finding | Orchestrator | Builder | Change |
|---|---|---|---|
| F1 T1 two readings (pooled vs mean over all) | uphold (blocking) | accept | T1 replaced. SOP 2.5 defines *reference controls* (usable controls, or every control when none is usable) and 3.2 takes the mean seed rate of them. One value; the no-usable case is now governed. Keeping today's pooled figure is the new trap's natural miss. |
| F2 G on rounded vs unrounded | uphold (blocking) | accept | 7.2: "A check value that, before rounding, is below 175 or above 225"; 1.2: every figure is worked out from unrounded figures. |
| F3 RPD with a bound | uphold (should-fix) | accept | The instruction's silence sentence now reads "the package's present calculation for it stays exactly as it is, applied to the quantities the SOP does define". The one present-code value is the parent-denominator RPD on the section 5 values. |
| F4 RPD inputs rounded? | uphold (should-fix) | accept | 1.2: "Every figure is worked out from unrounded figures; a value is rounded only as it is written to the report." |
| F5 "most sample" includes spent | polish | accept | 5.3 now says "bottle holding the most sample, spent or not". |
| F6-F8 | none | no change | |

Receipts were rerun on the redesigned snapshot (panel_precheck design-only d9d30ac0...): fuzz, departure-trap checks, instruction preflight, canonical smoke, and scorer validation on :skeleton2.
