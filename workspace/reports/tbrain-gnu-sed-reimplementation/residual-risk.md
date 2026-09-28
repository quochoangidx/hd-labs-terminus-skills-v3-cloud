# Residual risk (reviewer notes, not for the platform form)

- The manual's own sentence on `\|` (first alternative wins) is overridden by the instruction's leftmost-longest sentence; that sentence must stay.
- `addr1,~N` rests on the literal manual reading (next multiple after addr1).
- Behaviour the manual leaves open (per-file hold and 0,/re/ under -s, T resetting the flag, c on unclosed ranges) is excluded by case filtering; any regeneration must rerun the variant filter.
- Missing-file coverage is a single case.
