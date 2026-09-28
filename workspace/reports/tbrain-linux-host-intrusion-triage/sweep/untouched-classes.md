# Sweep classes not exercised by a mutant, and why
- C1 each visible promise has a graded family (one test per guide rule plus broad and case-1); no untested promise remains.
- C6/C9 field lengths and categorical codes: account/host names come from a fixed generator pool; the contract makes no length or syntax promise to sweep.
- C7 integer width: all values are epoch seconds in Python ints; no fixed-width accumulator exists.
- C8 signs/rounding: whole seconds only; signs of offsets are covered by C2 offset mutants and local_time_as_utc.
- C10 constant parameters: every family varies hosts, accounts, offsets, years and seeds.
- C14 session end inclusivity: the guide makes no promise about events exactly on a session boundary and the generator never places one there (dropped mutant c14-sudo-window-exclusive-end).
- C15 stated orders: only set semantics are stated; alt-sets-reversed scores 1.
- C16 frozen surface: none (from-scratch analyzer; only the documented CLI).
- C17/C18 harness and no-solver-in-tests: covered by harness-bypass, test_candidate_cannot_read_verifier_files, independence_check and preflight static gates.
