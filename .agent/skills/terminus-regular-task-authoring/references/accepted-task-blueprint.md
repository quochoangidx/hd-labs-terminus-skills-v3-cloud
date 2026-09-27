# Accepted-task blueprint

What six platform-accepted Terminus 3 tasks have in common, where their measured
difficulty actually came from, and what every one of their returns was for. Use
it when designing a seeded-departure task, when writing its verifier, and before
the first upload. [Contract closure](contract-closure.md) explains *why* each
rule holds; this file states *what the accepted shape is* and the pre-upload sweep
that would have avoided each return.

> **Reference only — never a template to copy (user decision, 2026-09-26).**
> These tasks are evidence for *why* designs hold or fail. A new task must not
> resemble any of them. Do not reuse their domain setting (utility tariff
> rebilling, FAO-56 irrigation scheduling, mechanical royalty statements,
> moving-average inventory close, IFTA fuel tax, genomic coordinate conventions),
> their authority documents or rule numbering, their departures, their trap
> mechanisms as instances (a signed correction in a list named after the rule's
> term, a credit line that is not an "adjustment", a late movement past a
> cut-off, alt == ref padding), their fixtures or data shapes, or their
> instruction, silence-clause or rubric wording. Take only the abstract
> properties: why a trap bites, the 0/8 screen, verifier hygiene and the
> sweep ladder. The templates in §3 are a checklist of *parts* a clause needs;
> write the sentences fresh for each task and its domain. All six are
> registered in `mined-candidates/index.jsonl` as `accepted_reference`, so the
> miner's dedupe rejects a candidate in the same setting, and a twist or reskin
> of one of them is not novelty. The same holds for the teammate's accepted
> tasks named in §4 (feedlot ration billing, construction pay-application
> retainage, engine LLP life tracking, retail inventory method, groundwater
> allocation, ULD demurrage). Vary the structure too: a new batch should not
> keep reproducing the same instruction shape, package size, departure count
> and trap pairing, since sameness across submissions is itself a
> `template_detection` and novelty risk.

Evidence (2026-09-26 audit of the accepted ZIPs, every platform revise report,
and the build ledgers): `tbrain-utility-rebill-true-up`,
`tbrain-crop-water-balance-irrigation-schedule`,
`tbrain-mechanical-royalty-statement`, `tbrain-moving-average-inventory-close`,
`tbrain-ifta-quarterly-fuel-tax-return`, `tbrain-genomic-coordinate-conventions`,
plus a teammate's batch 3–7 memory (about 30 further candidates, 3 more
accepted). Platform numbers are 8-run difficulty checks (4 × GPT-5.6, 4 × Opus 5).
Local numbers are two-solver probes and are signals, never tiers.

---

## 1. The corpus

| Task | Category / sub | Lang | Package | Departures | Counted traps that survived | Platform difficulty | Returns before acceptance |
|---|---|---|---|---|---|---|---|
| utility-rebill-true-up | Operations / Claims | Go | 5 files, 218 LOC | 9 | 7 small edge keeps (dials outside 1–8, a period of no days, reversed reads, …); credit-line trap dropped | v4 0/8 "unsolvable" (credit trap); final unmeasured, projected CORE 4/8 | category gate; panel 38 → 17 → 11 → 5; 0/8 |
| crop-water-balance | Science / Earth | Java | 13 files, 361 LOC | 9 | tailwater in the runoff test; gauge correction's day | **ADVANCED 3/8** (Opus 0/4, GPT 3/4) | panel 4; panel 1; human review (model in tests); panel 2 |
| mechanical-royalty | Media / Music | Python | 11 modules, 308 LOC | 9 | repayment inside recoupment; take-back trap dropped | v2 0/8 "unsolvable" (take-back); **CORE 4/8** (GPT 4/4, Opus 0/4) | panel 3; 0/8; human review (model in tests) |
| moving-average-close | Operations / Supply chain | Java | 7 files, 443 LOC | 6 | late supplier return and late unpriced goods past the cut-off; credit-note trap dropped | v4 0/8 "unsolvable" (credit note); late traps passed by 2/8 | panel 51 → 12 → 5 → 1; 0/8; gate `test_instruction_alignment` |
| ifta-fuel-tax-return | Operations / Compliance | TypeScript | 8 files, 353 LOC | 7 | a non-member mileage correction kept out of total miles | not in the archive (declared core) | panel 3 → 1 (first slot task, transformer metering, retired after 21 findings) |
| genomic-coordinate | Science / Biology | Python | 11 modules, 265 LOC | 9 | an event row whose alt equals the reference base keeps the padded record | not in the archive (declared core) | panel 20 → 12 → 6 → 1 → 1 → 1 |

What the numbers say:

- **Every accepted task is a small synthetic package (200–450 LOC) repaired against
  one in-environment numbered authority (85–171 lines).** Upstream-repo size and
  file count played no part.
- **All measured difficulty came from restraint traps. Departures are table
  stakes.** In every platform run that was recorded (32 runs over four uploads),
  every run repaired every departure, including departures that contradict what a
  domain expert remembers (FAO-56 limits, statutory royalty rules, IFTA folk
  practice). Plan the tier on traps, never on departure count or domain niche.
- **Returns were overwhelmingly Sound Verifier coverage.** Coherent Contract,
  Protected Ground Truth and Deterministic Execution were almost always clean,
  because the contract was written first and reviewed blind. The verifier's
  coverage of its own promise envelope is what kept leaking, one class per round.
- **Three of six went through a 0/8 "unsolvable" return.** Each time one trap was
  missed by all eight runs. Each was answered by dropping that trap, never by
  disclosing it, and the remaining traps carried the tier.
- **Two of six were returned by human review for an end-to-end model in `tests/`**
  after a clean platform run. The other four shipped with `tests/model.py` and got
  through by reviewer sampling. Do not rely on sampling (§4.3).

## 2. Anatomy of the accepted shape

### 2.1 Authority document

- One numbered file (`RULEBOOK.md`, `field-water-manual.md`, `costing-policy.md`,
  `fuel-tax-manual.md`, …): `N.M` rules, flat prose, no pseudo-code. The preamble
  says the book governs where the package disagrees, and that rule numbers do not
  move between editions.
- **Units and rounding first.** One global rounding sentence ("nearest whole
  unit, an exact half goes up … nothing is rounded where no rule says so"); later
  rules only say "rounded to the cent".
- **Every range stated, with ceilings and floors** ("This book provides for …",
  rule 1.4 in rebill: reads ±1e9 kWh, rates ≤1e6, money ≤1e9 cents, periods ≤366
  days). Ceilings are chosen so every product the reference forms fits the
  implementation type (rebill: `monthly × days < 2^53`, so a float customer charge
  is provably exact and stays untouched).
- **Definitions as domain-word terms with a threshold** ("a charge of one cent or
  more", "a depth of a tenth of a millimetre or more", "one mile or more"). The
  book never mentions a sign. That is what makes a silent subtype silent.
- **Rules written as membership, not as exhaustive lists** ("The day's rain is
  tested against the intake limit. An irrigation is not." — never "only rain").
- **Deliberate departures from domain memory are flagged inline** ("FAO-56 limits p
  to 0.1–0.8; the district's range is narrower"). Fair, credible, and it adds no
  measured difficulty.
- A **direct-call rule** only when helpers are graded (rebill 9.1: "the exported
  functions implement these rules when called directly"). Otherwise grade through
  the entry point.

### 2.2 README

The data contract only: build/run command, input layout and columns, and the
**encoding** of silent subtypes in neutral words ("`depth` is signed: a
correction the observer keys in is below nought"). No rule, no dependency
statement, no error disposition that is not graded (§5, return classes C1–C2).

### 2.3 instruction.md: three or four paragraphs, no headings, 300–600 words

1. **Goal.** User-visible symptoms in the customer's words (four symptoms for nine
   departures; never list the departures), the package and authority paths, and
   the **universal-range clause**: "each of its rules holds for every value in the
   range the book provides for, not only for the cases its examples happen to
   show." Then the frozen surface, stated as the literal harness action ("schedules
   will be made by compiling our own copy of the runner together with your
   package's sources"), never as an unenforced "don't change signatures".
2. **Silence clause, three tiers plus a composition sentence** (template in §3).
3. **Coverage envelope**: the run shapes graded ("many fields on shared gauges,
   seasons that start on any day of a month, several log entries on one day, …, and
   the kinds of input named above"), then **every numeric range and structural
   guarantee** of graded inputs ("every date falls in 2000–2099, field numbers are
   unique, …, no gauge has more than 20 entries on one day"). Every phrase here is a
   promise the panel will try to break (§5).

Echo the subcategory gloss when the fit depends on it: rebill's "customer billing
claims" answered a `category_and_tags` return that read Claims as insurance only.

### 2.4 Verifier

| Element | Accepted form |
|---|---|
| Layout | `tests/test.sh`, digest-pinned `tests/Dockerfile`, one `test_outputs.py`, small helpers (`runs.py`, `jobset.py`), `tests/shipped/` (pristine package plus driver), `tests/expected/` (sealed expectations plus a SHA manifest) |
| Names | One named function per rule: `test_rule_5_2_p_landing_on_a_limit`; one per trap, named for the kept behaviour: `test_tailwater_keeps_its_shipped_place_in_the_runoff_test`. No `parametrize` (CTRF collapses it). The platform's crux analysis reads these names |
| Expectations | Written by `solution/model.py` (re-derived from the authority, never importing the package; silent branches mirror the shipped statement with a "Shipped step" comment) into `tests/expected/`, each bound to its input digest in `manifest.json`. At grading time a test regenerates or loads the input, checks its digest, and compares. No model and no generator run inside `tests/` (§4.3) |
| Silent side | A shipped differential: the pristine package compiled or installed under **its own uid, mode 0700**, run as that uid; the test asserts candidate == shipped on exactly the column the kept step decides, after neutralising any other departure that would confound the comparison (crop feeds readings pre-moved a day) |
| Driver | The verifier runs its own copy of the fixed driver **and** a test byte-compares the submitted driver with `tests/shipped/tools/`. Run it at the documented path and command; the byte check must also run after candidate code (last test or in `test.sh` after pytest) |
| Privilege | `test.sh` writes reward 0 first, `install -d -m 700 /logs/verifier`, `chmod 700 /tests`, `chmod -R a+rX /app`; candidate builds and runs as a sandbox uid via `setpriv --reuid --regid --clear-groups --no-new-privs`, new session, `PATH=""`, `killpg` on timeout; shells and interpreters `chmod 750` in the verifier image; a test proves the sandbox uid cannot read `/tests`, the expectations, the shipped copy or `/logs/verifier`, with a world-readable control |
| Comparison | Whole outputs, recursively type-strict (`type(g) is type(e)`: `2500.0 ≠ 2500`); report-wide identities (TOTAL = Σ rows, row order, layout) inside the shared run helper so every test enforces them; only the orders the authority states |
| Limits predicate | Every graded job, named fixtures included, passes an executable form of the instruction's limits sentence (`_keeps_the_limits`, `within_limits`) and declares which trap inputs it carries; sweeps are trap-free by construction |
| Sweeps | Seeded from a constant in the sealed test code (never from candidate bytes), drawn to tens of times any plausible buffer, whole-range, trap-free |

Sizes that closed the panel: 24–39 tests, 60–3,100 direct calls or 20–70 graded
runs, suites running in seconds.

### 2.5 Oracle and explanations

- `solution/fix.patch` with one hunk per rule and `solve.sh` headed by a
  **Rule | File | Change** table, a "(no change)" row for code already right under
  the book, and a Strategy paragraph restating the silence policy. Every added
  rounding or range branch falls back to the shipped expression outside the book's
  range.
- `difficulty_explanation`: the persona (rates analyst, cost accountant,
  irrigation adviser), each departure with the real-world slip it mirrors, then a
  "harder half" paragraph that **names each natural over-repair in code-level
  terms** ("takes the whole turnout log out of the water tested against the intake
  limit"). The platform's crux-alignment judges matched agent diffs to it verbatim
  and passed on every run. No pass rates.
- `solution_explanation`: the numeric proof behind any deliberately unchanged
  function (`m·N < 2^53`).
- `verification_explanation`: the named edge fixtures, every size ceiling crossed,
  the wrong paths rejected, and "no draw uses an input the instruction leaves
  open". Update it on every tests-only revision; the quality gate compares its
  counts with the files.
- Set `difficulty` to the measured tier after a measurement (crop core →
  advanced). Before one, say in the submission note that it is a placeholder.

### 2.6 Rubric

12–16 lines, `Agent <concrete behaviour>, ±N`: one +2 per departure group, +3 per
counted trap kept, +1 for the frozen surface, −3 per **named natural over-repair**,
−5 for editing the authority or hardcoding. Regenerate it whenever a trap is
dropped or flipped: royalty's reviewer had to fix two stale lines by hand, and
rebill's and moving-average's submission notes still rewarded a dropped trap.

## 3. Silence clause: the parts it needs

(The block below shows the parts in order. Write every sentence fresh in the new
task's own domain language; do not reuse this wording or any accepted task's.)

```
Only fix what the <book> governs. Where it says nothing, what the package does
today is the answer, so add no guard, clamp, error or tidy-up for inputs the
<book> doesn't provide for: <silent input 1 in the customer's words>, and
<silent input 2>. For such an input, keeping the step the code takes for it today
takes precedence over the rest of this paragraph; every other step it passes
through still follows the <book>. Some inputs are left entirely open, and the
package may do whatever it likes with them: <figures past the ceiling rule>,
<inputs the frozen types cannot answer>, <books that break structural rules>,
whether handed to the driver or to a function directly.
```

Rules for filling it:

- **Tier 1 — governed.** Everything inside the stated ranges and definitions.
- **Tier 2 — silent, keep shipped.** A closed list in domain words, never by sign,
  module, site or rule number. Bind it only to inputs where the reference's own
  edits leave the shipped output unchanged; otherwise Correct Reference fires
  (rebill: duplicate effective days, the empty-code sentinel, negative limits).
- **Tier 3 — left entirely open, never graded.** Figures past a ceiling, questions
  the frozen types cannot answer (rebill's net-only `Bill.Adjustments`), anything
  a dropped trap used to cover. Name each by value and grep every range sentence
  and entry point when you add one ("whether it sits in a tariff book or is handed
  to a function directly").
- **Draw the governed/silent line with the authority's defined terms**, never an
  unnamed "step". Escrow v7 went 0/8 on three tests until one sentence said the two
  inputs "are not payments or disbursements as the book defines them".
- Never write "anything else outside the range" (royalty v1 finding 3, ltl v4). End
  the clause, or the envelope, with "every job keeps within the ranges the README
  gives".

## 4. Where the difficulty comes from

### 4.1 A trap that held on the platform

| Property | Evidence |
|---|---|
| **Sits inside an aggregate a departure forces the solver to rebuild or newly write**, not at the definition site | crop T1 (`surface = rain + brought` rebuilt for rule 6.2; all 4 Opus wrote `max(0, rain − intake)`); royalty T1 (`brought_forward + sum(advances)` rebuilt); IFTA T2 (total miles broadened, 6/6 local misses). Solvers keep a silent step wherever a definition applies directly |
| **Bare representation, two hops**: a sign or value in one homogeneous unlabelled list whose field name is the rule's own term; excluded only by a domain-word definition | genomic alt == ref (case may differ, needs §2.2 to see equality); overtime, metering, escrow 0/2. Labelled type codes and README-labelled encodings are one hop and caught nobody (genomic T2/T3, hplc 2/2 twice) |
| **The kept step is one routing decision** (which side of a cut-off, which bucket, in or out) with no kept arithmetic | moving-average late returns (2/8 passed), genomic padded record. Traps that keep arithmetic need a scope sentence that gives them away |
| **Keeping it requires adding code** the "no guard, clamp, tidy-up" wording discourages | royalty's fix adds `amount < 1` inside the rebuilt sum; Opus read "keep today's step" as "don't special-case it" 8/8, GPT read it by effect 8/8 |
| **The kept step follows from a chain of definitions** the solver can apply | moving-average 1.1/1.2 define receipt and issue narrowly and cut-off 2.1 speaks only of those: accepted at 2/8. The credit note had only today's code behind it: 0/8 |
| **An edge whose natural rewrite looks like the rule itself**, in a function already being edited, with the book bounding the rule's range | rebill `10^d` for every dial count, `to − 1` for every period (Opus 3/4 and 4/4 missed) |

### 4.2 Portfolio rules for traps

1. **At least two independent traps**: different lists, files, subtypes and
   instruction phrases, so no single sentence disarms both. Crop's two traps split
   the runs (4/8 and 3/8 failed) and measured ADVANCED with no unsolvable risk.
   Royalty lost one trap to a 0/8 and sat on the 4/8 CORE boundary with the other.
2. **Mix kinds.** GPT-5.6 fell for definition hops (rebill credit lines); Opus 5
   fell for "apply the formula everywhere" edges and for "keep means don't
   special-case". A mixed portfolio is what lands mid-band. Pairing one exclusion
   trap with one inclusion trap decorrelates the two reading policies (teammate
   batch 7: pay-application split one solver per trap).
3. **Isolate each trap in its own named test.** Never put a trap input into shared
   fixtures, whole-run tests or sweeps. Rebill's credit lines sat in seven tests, so
   one shared over-repair turned all seven to 0/8.
4. **Name the class, never the trap or the rule it escapes.** The one trap rebill's
   instruction named explicitly (limits over 60 days) caught 0/8 runs. Naming the
   silent *inputs* in domain words is fine (crop named both and still bit 5/8).
5. **Do not count shared-helper coupling, departure count or niche domain rules as
   difficulty.** Genomic went 2/2 on coupling alone; 12 non-trap designs went 30/30.

### 4.3 The 0/8 "unsolvable" screen (run before upload)

A test that no run passes returns the task even at FRONTIER. Every one of these
produced one:

| Cause | Case | Screen |
|---|---|---|
| A **positive enumeration** in the authority plausibly governs the silent entry | royalty take-back: 8.2 "Royalty on physical units carries a reserve" | Trace each trap's destination aggregate through every sentence that could govern it ("X carries", "Y counts toward"); if one could, drop or reroute the trap |
| **No definitional chain**: the kept step is a bare quirk of today's code | moving-average credit note after the write-down | Ask: which definitions make the kept step derivable? None → drop |
| **Strong contrary expert instinct** ("a reversal lowers the total") | health-plan accumulators, VOC rolling usage, commission tiers | Only genuinely arguable exclusions split |
| **An unnamed "step"** shared by governed and silent inputs | escrow v7, three tests 0/8 | Draw the line with defined terms (§3) |
| **One trap feeds several tests** | rebill credit lines, seven tests | Isolate (§4.2 rule 3) |

**A unanimous local miss predicts 0/N.** Royalty's 4/4 local misses on the
take-back became 8/8 platform misses; IFTA's 6/6 was a flagged risk. Treat a trap
that every local solver misses as a contract defect to resolve before upload, not
as difficulty. The healthy local shape is split misses across two or more traps,
judged trap by trap: a split pair total does not excuse one trap that every run
missed, and a trap whose inputs also sit in broad or generated tests is better
isolated when cheap (`task-batch` execution-profiles step 7).
Local probes do not predict per-model splits or the tier: royalty's local
Opus 5.5 kept the repayment trap 4/4 while platform Opus 5 failed it 8/8, and a
local 1/2 on a one-trap shape went BASE 7/8 on the platform (midi, retired).

**Drop, do not disclose.** When a trap is 0/8, rewrite the authority so the case
becomes governed (royalty 6.3 "an adjustment … and a sum it takes back") or move
it to tier 3, keep the test as a governed-rule test or delete it, and record
`removed_obligations`. Disclosing the rule kills the trap and adds nothing. Then
scrub every place the class appears: instruction, README, visible sample, named
fixtures, generators, model comments, `solve.sh` header, explanations, rubric and
submission note (moving-average's fifth return was a leftover −7 invoice in one
hand-built fixture).

## 5. Pre-first-upload Sound Verifier sweep

The panel works through a fixed ladder, one class per round, and a PASS does not
prove the next class is covered (crop's v4 gaps were latent from v1). Genomic spent
six rounds and rebill four discovering these one at a time. Run the whole ladder as
mutants of the Oracle before the first upload, and again before every resubmission:
each mutant must score reward 0 on its own named test.

| # | Class | What to grade | Mutants that must fail |
|---|---|---|---|
| C1 | Every visible sentence is a promise | Each README/instruction statement (defaults, "may", error disposition, dependency, interface, plumbing rule the shipped code already obeys) gets a graded input a plausible slip gets wrong, or is deleted with `removed_obligations` | moving-average v0: 21 findings from an untested exit-2 promise; genomic #1: 20 plumbing rules; "no third-party dependencies" read as a prohibition |
| C2 | Numbers without ceilings | A ceiling **and** floor for every number, count, span and list, chosen so products fit the type; larger figures tier 3 | rebill 11 overflow/precision findings; moving-average 21 |
| C3 | Every bound reached | A graded job **at** each inclusive end, in each position a range applies to, and at the top of every sum of ranged fields; calendar ends (31st, 31 Dec, 29 Feb) in *named* fixtures (the panel reads generators statically). Lower ends too, not only ceilings: a stated minimum count ("at least two different concentrations"), the smallest legal magnitude of an "above nought" value (a slope of 2e-12), the lowest end of every range. Derived extremes the ranges imply together (largest amount = largest reading × largest dilution; readings far past the top standard). Each run kind's own copy of a shared range (a spike's dilution, not only a sample's). Close every open end before sweeping ("above nought" → "from 0.0001"; "at least ten times the loq" → "… to 10^4"): an open end cannot be reached, so a floor or cap slips past every fixture. List every range and the extremes the sealed fixtures reach in one script and clear every gap in one batch | `min(midDays, 60)`, a 512-day loop cap, a 4,096-row reader (crop v1); trace-metal v9: amount capped at 10^6, standard `is_counts` floored at 1024, three-level guard, slope floor 1e-9, spike dilution capped at 250 all scored 1 |
| C4 | Floors and zeros | Empty for every list including the outermost; zero for every amount, term and opening balance, jointly; the value in range but outside a definition (0 when the definition says "one cent or more") | raise-on-zero (royalty v1, moving-average v3), `receipts[0]` (uld), `reduce()` without initial value |
| C5 | Counts and cardinalities | Every list past 1,024, total rows past 65,536; distinct keys, rows per key and values per role at their bounds (not just list length over a realistic key pool) | 64-slot member table (IFTA v3), `islice(rows, 100)` (genomic), 32-line/1000-movement/3-invoice buffers (moving-average) |
| C6 | Parameters and field lengths | Numeric parameters past 512/2048/4096 on inputs where a cap changes the output; variable-length fields past 8/64/1024 | `min(flank, 512)`, alleles `[:8]` (genomic v3–v4), 76-char codes (rebill) |
| C7 | Integer width | Per-entity accumulators and totals past 2^31; one-sided bounds past their mirror | `int` accumulators, `| 0` totals, int32 day numbers |
| C8 | Signs, rounding and exact thresholds | Every sign-changing derived value on both sides of 0 in every consumer; an exact half on both signs **and** a non-half ≥1 unit below 0; a near-half for float paths. A float value compared against a limit: never promise "exactly on the limit" for arbitrary decimal inputs (0.1 + 0.2 ≠ 0.3 flips the flag). Either state a margin in the authority ("never within 10^-5 of a limit") plus a magnitude bound keeping float error far below it, and fixture a power-of-two hair each side, or keep on-limit cases only on exactly representable inputs the contract itself restricts to | half-away-from-zero, `Math.trunc(x + 0.5)`; trace-metal v9 Correct Reference Major: on-limit decimal blanks flipped J/ND |
| C9 | Categorical domain | Codes and IDs sampled from the whole stated syntax, familiar values in the wrong role, leading zeros, case variants | `rates[0]` membership, hard-coded IFTA list, whitelist validator (IFTA v2) |
| C10 | Parameters never constant | Every job field varied over ≥2 values (closing day, file names, schedule codes); at least two fixture sets sharing identifiers | hard-coded closing date, lookups over the graded fixture (rebill: one tariff book) |
| C11 | Accumulators the repair separates | Two entries of each separated subtype in one bucket, plus a case where every downstream rule it feeds changes the output | `put(day, depth)`, `tailwater = depth` (crop v4) |
| C12 | Silent inputs | One graded input per plausible guard (`< 0`, `== 0`, empty, "only after predecessor X"), at any position, without its natural predecessor, crossing every attribution rule | escrow v3 guards, LLP clamp mutants |
| C13 | Envelope cross-product | Every combination of named envelope axes, not each value once | 5-minute logs never paired with 30-minute demand (metering v1) |
| C14 | Rules computed in two consumers | Each operation decisive in each consumer | P and D in genomic's reverse duplicate key |
| C15 | Stated orders | Assert every order the authority states, and only those | `sort_keys=True` (royalty v1), over-strict order is itself a Major |
| C16 | Frozen surface | Reflection or typed-var assignment against the shipped signatures, not "it compiles" | `type Day int64`, `CustomerCharge` returning `int`, `List` → `Collection` |
| C17 | Harness | Submitted driver byte-identical, checked after candidate code; no case label in argv/cwd (prefix-less `mkdtemp`, content-digest names); visible sample never graded; documented cwd and command | midi v1, genomic `mkdtemp(prefix=name)`, moving-average v0 PGT Major, uld cwd |
| C18 | No solver in tests | Model and generators in `solution/`; sealed readable expectations with a SHA manifest; candidate-uid read test | crop v3 and royalty v3 human review; escrow v5 named the generator too |

Loop signal: a second return naming another corner of the same class means sweep
the whole class (floor, ceiling, position, sign) or narrow the promise. Never add
only the one fixture named. Every "stop promising" drop in this corpus was
effective at once; every one-fixture "make true" exposed the next ring.

## 6. Process that worked

- **Contract before verifier, reviewed blind.** It is why four of five axes were
  clean in almost every report.
- **Reproduce every finding as a mutant on the returned snapshot before fixing it,
  and close it on the new one.** Three genomic findings did not reproduce; they
  were disputed with a receipt and a witness was added anyway.
- **Keep the agent-facing contract byte-identical through verifier-only
  revisions** (instruction, `environment/`, `solution/`), so the measured tier or
  local signal still applies. When expectations are resealed, prove every sealed
  expectation equals the previous live model, so the difficulty result carries.
- **Draw new fixture entries after all existing seeded draws** (or from a separate
  RNG stream), so saved expectations do not move and the diff stays reviewable.
- **Re-run every earlier wrong path each round** (genomic 19 → 46; moving-average
  20+; IFTA 32).
- **Read the blocking stage of every return first** (task-revise-flag-remediation
  *Grading flow*): a panel return is repaired; a 0/8 return is a trap to drop; a
  BASE result means proposing a replacement task; a human-review return is one
  targeted fix.
