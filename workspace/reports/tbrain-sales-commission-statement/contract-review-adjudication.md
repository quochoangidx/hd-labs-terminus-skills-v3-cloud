# Contract review r1: adjudication (builder I)

| Finding | Builder | Orchestrator | Repair |
|---|---|---|---|
| F1: the reach clause "only the ones the plan itself sets may move" lets the 120-day window reach courtesy credits | accept | UPHOLD | The instruction now reads "an input of that calculation moves only where the plan states that figure for that same item". Plan 5.1 now opens "The clawback window of a reversal is 120 days." The window is stated for the defined subject only. The silence clause names no case. |
| F2: README "`bonus`: the new-logo bonus" misdirects | accept | UPHOLD | The README now reads "`bonus`: the total of the first-order bonus lines, in cents". Plan 1.4's domain description is unchanged. |
| F3: do the thresholds apply to the value or to the share? | accept | UPHOLD | 2.3 now reads "a credit note whose amount credited is 50,000 cents or more, whatever the rep's split". 2.4 now reads "a first order whose value is 250,000 cents or more, whatever the rep's split". The model and the Oracle already test the full amount and value; the fuzz rerun agrees. |
| F4: 1.6 contradicts 1.5 and the example | accept | uphold | 1.6 now limits the 45-day window to orders in the rep's order list and to the day a credit note is raised. It adds that a credit note's order may have been booked earlier, as 1.5 allows. `limit_problems` in the model already checked it this way. |
| F5: 5.2/6.2 "reach" the line but not its amount | challenge | no change | Kept on purpose: these rules close the exclusion reading without giving a value, the same as the delivered supplier-rebate task. |
| Solver-path screen svr 2 | noted | advisory | The skeleton pair decides. |

Reruns after the repair, on image `tbrain-sales-commission-statement:skeleton1`, `sha256:cf9461f9576542ca93fe2343c12b4b9dad33ba2905436ea28c5ef38b69260e0b`:

| Check | Result | Receipt |
|---|---|---|
| Model-versus-Oracle fuzz, seeds 20260928 and 7 | pass | `receipts/fuzz-model-vs-oracle-seed*.json` |
| Departure and trap checks | pass | `receipts/departure-trap-checks.json` |
| Scorer validation | Oracle and the alternative solved; shipped fails all ten families; each trap wrong path fails only its own trap | `receipts/skeleton-score-validation.txt` |
| `instruction_preflight` | pass (504 words) | `receipts/instruction-preflight.txt` |
| `panel_precheck --design-only` | pass, snapshot 6a9c626e | `receipts/panel-precheck-design-only.json` |

The package source and `solution/` are unchanged.
