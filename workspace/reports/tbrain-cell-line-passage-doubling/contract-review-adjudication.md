# contract_review r1 adjudication (builder column) — tbrain-cell-line-passage-doubling

| # | Finding | Builder | Action (redesign 1/1) |
|---|---|---|---|
| F1 | empty-bank PDL reads 15/20/null; silence read as covering only 2.6 | accept | 2.6 removed; 2.5 defines "in use"; 6.2 rules only on "a bank in use"; instruction silence is one general value-level sentence ("Where the SOP has no rule for a figure that one of the package's steps works out, that step keeps working it out as it does today, from the figures the SOP does define"), naming no case |
| F2 | partial-viability fallback tempting | accept (polish) | general sentence keeps the whole figure the step works out; no text naming the case |
| F3 | child of a failed harvest also falls back | accept (intended) | no text change; 2.4 unchanged |
| F4 | integer type of passage / vials_left | accept | SOP 1.1 and 7.1 state JSON integers; instruction says "as a JSON integer" |
| svr 2 | T1 explicit via 2.6 and 2.3 aside | accept | 2.6 and the 2.3 aside removed; T1 bound now only by the 2.3 definition of a valid count |
