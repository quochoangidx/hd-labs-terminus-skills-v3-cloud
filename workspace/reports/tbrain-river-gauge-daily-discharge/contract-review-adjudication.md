# contract_review adjudication — tbrain-river-gauge-daily-discharge

Reviewer: one fresh Claude Opus subagent (general-purpose, model=opus), packet = instruction.md + environment/ only.
Builder and orchestrator are the same session; both columns recorded.

| # | Finding | Severity | Builder | Orchestrator | Action |
|---|---|---|---|---|---|
| 1 | daily_mean with zero covered time: literal clause gives today's plain mean, reviewer calls None "defensible" | should-fix | challenge | overrule | No change. The reviewer's own literal reading is determinate: §6 defines the mean as integral / covered time, which does not exist at zero coverage; the instruction says today's result stands "including what it returns", and forbids adding a guard. "None" has no textual basis. Same shape as the panel-cleared span<=0 case in contract-closure §15. Recorded as a deliberate restraint trap; witness uses the shipped differential. |
| 2 | joined_pieces / span_totals not named in the note | should-fix | accept | uphold | §5.4 names both and their shapes |
| 3 | inputs that break ordering rules are undetermined | should-fix | accept | uphold | instruction promises ordered inputs; verifier never generates unordered ones |
| 4 | event end undefined; run maximality | advisory | accept | uphold | §8.1 "longest stretch", §8.2 "an event's end is the end of its last run" |
| 5 | last-bit shift differences at segment boundaries | advisory | accept | uphold | verifier puts boundary stages only under exact shifts (entry times, zero shift) |
| 6 | exponent <= 0 at offset | advisory | accept (no change) | uphold | fair as written; witnessed by shipped differential |
| 7 | degenerate cases determinate; joined_pieces is a generator | advisory | accept (no change) | uphold | driver lists the generator |
