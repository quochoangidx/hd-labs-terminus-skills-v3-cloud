# Contract review r1: builder dispositions (orchestrator: UPHOLD F1, redesign once)

| Finding | Builder | Action |
|---|---|---|
| F1 mixed crowded+sparse sample ungoverned, "keep today" gives several values (W9 3.0E1/1.5E1, W10 <1.0E2/<1.0E1) | accept | Dropped the silent case. SOP 2.6 now defines a sparse sample as one with neither a countable nor a crowded plate, and 4.4 gives every sample with a crowded plate and no countable plate a greater-than at the last dilution holding a crowded plate. Every sample class is governed, with one value each; shipped `estimate()` routing becomes part of departure D6. |
| F2 2.7 "a tenth of that one" read as a plain rule | accept (trap weak) | T1 is kept as the exclusion trap but no longer carries the design alone. New T2 (inclusion): 2.8 counted plates = plates of counted dilutions that are not crowded; shipped `in_count` (<= 250, lacks a lower bound, looks like a bug beside 20-300) is correct in shape; the rule-shaped rewrite "countable plates of the counted dilutions" drops sparse/empty plates. Both traps live in the one pooled sum D1/D2/D3/D8 force the solver to rewrite. |
| F3-F5 polish | accept | no change needed |
| svr 2 | partial | self-score after redesign 3 (see solver-path-screen.json); skeleton pair decides |

Receipts rerun on snapshot 726cdf98... : fuzz (2 seeds, pass), departure-trap-checks (pass), panel-precheck design-only (pass), instruction preflight (OK), skeleton2 scorer validation (oracle solved; shipped fails all; T1nat_listnext/T1nat_nextcountable fail only T1; T2nat_countable_only fails only T2). Image :skeleton2 sha256:4a1bbfdca4ae08969d2bb8c181e3aa188c36b63231d19bfbb8f64f20674d77fe.
