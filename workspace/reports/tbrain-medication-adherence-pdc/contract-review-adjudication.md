# contract_review r1 adjudication (builder / orchestrator)

| # | Finding | Builder | Orchestrator | Action |
|---|---|---|---|---|
| 1 | `period` for an in-measure member: length or length less stay days | accept | uphold | 4.1 defines *period days* (treatment-period days that are not stay days) and the PDC divides by them; README `period` = the days the covered days are divided by |
| 2 | "at least 90 days before the last day" reads as difference >= 90 or span >= 90 | accept | uphold | 2.4 now says "no later than 2 October of the measurement year" |
| 3 | rate of a class that is not reportable; symptom sentence pushes the other way; rounding reach | accept | uphold | symptom narrowed to "our statin class, one of the large ones"; 1.2 now says every PDC and every rate the report gives is rounded half up |
| 4 | members outside the measure: rounding and stay days | partial | narrow | rounding settled by the new 1.2; stays: period days are defined only through the treatment period, so the shipped span step stands (composition sentence); no other change |
| 5 | fills over 100 days (restraint site, not a defect) | accept | uphold | no change |
| w | "79.96" cannot occur within 1.3 | accept | uphold | symptom replaced by "a PDC of two thirds is reported as 66.6" |

Solver-path screen: self_verification_resistance 3 -> continue to skeleton after a clean recheck.
