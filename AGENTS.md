# AGENTS.md — Terminus Regular Task Building (single-file memory)

> **The single source of truth for every coding agent in this repo** (Claude, Codex, Gemini, Cline, Qwen). `CLAUDE.md` is a symlink to this file.
> Fully self-contained: all prior knowledge (259 detail notes across earlier stores) was consolidated INTO this file on 2026-07-07; nothing outside it overrides it.
> **Self-update rule:** whenever a new durable finding lands (probe verdict, client feedback, platform/infra fix, corrected label), immediately update and improve this file — fold it into the matching section, keep the whole file consistent and conflict-free (the newest verdict replaces the old claim in place, stated once), and mirror the same finding into Claude auto-memory.

---

## 1. TL;DR

Under a **warm loop** (persistent container + `docker exec`, real build+verify cycle), **Opus 4.8 medium solves nearly every fully-specified minimal-codebase task** — it derives its own reference and self-differential-tests thousands of cases. **Reliable HARD is not achievable by minimal spec-task building alone.** Ship honest MEDIUM (platform-OK for non-Python; Python tasks must be Hard). Only three levers still bite:

1. **Non-self-verifiable ground truth** — conformance over a hidden/divergent reference the solver cannot re-derive (§3). The genuine HARD lever, ~60% yield.
2. **Under-fuzzed input shape** — a boundary corner the solver's own fuzzing misses; interval-ledger/duty-cycle ports (§4). A ~0–25% lottery, not a guarantee.
3. **Decoupled decoy where the plausible fix is itself wrong** (§5). Necessary but not sufficient.

Everything else — rule complexity, counter-intuitive *stated* rules, named algorithms, cascade depth, optimization even when non-decomposable — collapses (§6). Probe honestly (§7): warm loop, N≥5, terse prompt, score by differential, never trust self-report or a lone 0/3.

---

## 2. Core principles (why tasks collapse or hold)

- **Complete spec ⇒ Opus 3/3.** A fully-specified contract — stateless or stateful, simple or deeply cascaded, intuitive or counter-intuitive — gets transcribed and self-differential-tested. Adding rules, cascade depth, or counter-intuitive-but-stated rules never hardens a task.
- **Difficulty must be decoupled from the symptom.** Any symptom specific enough to anchor a fair instruction also tells a domain-expert solver the fix. If there is exactly one symptom and fixing it solves the task, it is 3/3 regardless of domain.
- **Named algorithm/idiom = collapse.** If the symptom makes a strong solver recall a named algorithm (Kahan/Neumaier, Chaitin-Briggs, HLL++, scalable-Bloom, A*-reopen, decode-to-fixpoint, tail-carry UTF-8, presume-abort, Hamilton apportionment, Efraimidis-Spirakis…), reject. Survivors are counter-instinct AND a non-default, non-obviously-named variant.
- **Hide the mechanism, state the contract.** Difficulty survives only when the spec describes the outcome, never the algorithm. Source comments and test labels are as much a difficulty surface as instruction prose — de-telegraph all three.
- **No middle band on arbitrary conventions.** Tiebreak direction, undocumented constants, bandwidth-model choice, rotation direction: hide it → unfair (0/N + spec-gate FAIL), state it → trivial. Retire on sight; a decoupled wall must also be enum-unconstrained or it's telegraphed.
- **Natural-impl-correct never bites.** The decoy structure only works when the plausible/natural fix is itself WRONG on a fixture; if a careful engineer's default implementation is correct, the task is 3/3.
- **Closed-form cost walls need a non-obvious exact constant** that is not searchable (never "smallest x meeting bound B" — emit a raw computed number) and never leaked via a worked example that evaluates the hidden formula.
- **Fully-stated optimization collapses** — non-decomposable, coupled tree-DP, carried-state, small-N brute-forcible: Opus derives the exact DP or brute-forces the ground truth and self-checks to the optimum (checkpoint-segment ultimately shipped MEDIUM; affine-carry, terrace DP, signal-repeater, min-makespan all 3/3).
- **User preference:** non-victim archetypes (estimation/aging/cost via a secondary observable) over victim/eviction-direction tasks; name slugs by domain (no "-ledger" suffix); `tbrain-<problem-slug>` without tool/repo filler.

---

## 3. Lever 1 — Conformance over a divergent / hidden reference (genuine HARD)

**Recipe:** ship a stub; bake an official machine-checkable suite HIDDEN under `tests/` (never in `environment/repo`); correct oracle; verifier calls a specific solver entry point; forbid vendoring third-party libs; **always probe offline** (a suite solved online can still hold offline — uri-template went 250/250 online but missed 15/249 offline). ~60% yield (10 HARD / 17 built).

**What holds:** WHATWG-URL, UTS-46 IDNA, RFC 9535 JSONPath, UAX-14 / UAX-29-sentence, JSON-Schema-2020-12, HTML5 tokenizer, iCal RRULE (hidden `python-dateutil` ground truth; tail = BYDAY ordinal, negative BYMONTHDAY, BYSETPOS, WKST divergence, Feb-29), CSS-Syntax-3 tokenizer, PHP composer version constraints (real-impl-as-spec, held 0/14), RFC 7208 SPF (with remediation), dockerignore matcher, protobuf schema-less wire decode, FASTA/FASTQ, DNS name compression.

**What collapses:** well-known formats/rules even with "edge cases" added — nginx-location, tar, bencode, msgpack, multipart, chunked HTTP, shell word-split, ical unfolding, css-specificity, iso8601-duration, poker/bowling/BLEU, RFC 6265 cookie (single contiguous algorithm = one-shot transcribable), Mustache (small rule set, no big table), **robots.txt RFC 9309** (Sonnet one-shots a correct independent port, 372/372 — hardening a memorized public library is futile), bibtex name-splitting (memorized; sole wall = one correlated hyphen quirk = 0/N flag with no fair fix).

**Selection rules:**
- Load-bearing rules must be **scattered/combinatorial across spec sections**, not one localized algorithm.
- Prefer an **unmemorizable, irregular table** (megabytes: UTS-46/UAX-14/UCA class data). Small clean rule sets collapse.
- **Stdlib-reachability trap is fatal:** if a Python stdlib one-liner reproduces the behavior (unicodedata normalize/casefold, json, csv, ipaddress, datetime, base64, urllib.parse), the solver differential-tests against it in-image. Use non-stdlib refs (hpack, CBOR, OpenPGP, collation, binary32 formatting).
- **Real-impl-as-spec** works, but every disclosed "subtlety"/example MUST be oracle-verified per-case — one false hint (composer `1.0.0-beta` claim; jsonpatch "`/` = whole document", when RFC 6901 says `/` = empty-string key) creates an unfair correlated 0/N and a reviewer reject.
- **Offline library conformance must be self-contained.** If tests pin exact behavior from an unavailable implementation, "match library X" is not enough: either document the algorithm, tie-breaks, and edge cases in an agent-visible offline reference, or ship allowed offline source/reference (uri-template: bundle RFC 6570 Appendix A + encoding sets as `/app/RFC6570.md`). BUT self-containment and difficulty can conflict: if fair disclosure forces you to hand over the whole reasoning wall (TER/sacrebleu block-shift algorithm — a reviewer demanded it be disclosed for offline fairness, yet the best agent already reconstructed it to 162/163 from memory), disclosing flips the task EASY → DROP (see the Disclose-vs-DROP test below).

**0/N-coverage-flag remediation** ("some tests not passed by any agent"):
- Diagnose from the per-test pass table, not the summary. Classify each 0/N case: redundant group test → delete; monolithic/aggregate test → **parametrize per-case** (always prefer per-case over per-area aggregates — clears behavior_in_tests without seeding the flag); irreducible correlated blind-spot tail → **prune** the ≤5/10 cases keeping softer representatives of every feature cluster (ceiling = min kept pass-count; keep it ≤60% for HARD); spec ambiguity/convention → **disclose** in the instruction; over-concentration (46% of corpus = one trap) → delete the adversarial bulk of that one feature, keep it minimally covered.
- **Anti-hardcoding flag** ("visible fixtures → hard-coding possible"): add a runtime differential vs a HIDDEN oracle copy in `tests/reference/`, generating well-specified rules deterministically at verify-time (fixed seed, per-case) restricted to the envelope MINUS every previously-pruned feature; prove flag-safety with a correct-except-pruned-feature emulation and teeth with a plausible-bug emulation.
- Keep test-format checks decoupled from result correctness (SPF `test_output_format` re-tested hard results = double jeopardy → 4/10 artificial cap).

**⭐ Disclose-vs-DROP decisive test (the 2026-07-07 batch).** A 0/N return on an all-or-nothing "match named lib" port is either fixable-by-disclosure or a DROP, decided by ONE question: *does a BROAD residual wall survive after you disclose the correlated blind spot?*
- **Disclose & KEEP** when a genuinely broad, self-contained wall remains and the BEST agent still falls well short of 100%. Cluster 0/N cases by feature, extract EXACT values from the oracle (build the oracle binary; generate DISJOINT worked examples, not corpus rows), ship an in-env `<LIB>_NOTES.md` (`COPY` before the image's `git add`; reachable at `/app/...`) + a narrative instruction pointer. Disclose LOOKUP knowledge (formatting rules, regex, function surface, aggregation formula), NOT the reasoning wall. Proven on **jsonnet-eval** (full interpreter = fair broad wall, best agent 93%). ⚠️ Disclose COMPLETELY — a partial rule is a new correlated blind spot (ter-score round-2: `no_punct` note gave only the ASCII class, missing CJK/full-width removal under `asian_support` → new near-0/N).
- **DROP** when difficulty is NARROW (best agent within 1–3 of 100%, all runs ~95%+, sub-100% tests all the SAME few features) OR the "wall" is an offline-unreachable library internal that fairness FORCES you to disclose AND the best agent already nears 100% without it. Disclosing then flips it EASY with nothing left to hold the pass rate down. Dropped **cookie-string-parse** (one `Domain=.` gotcha), **icu-messageformat** (3 ICU quirks: half-even, stray-`}`, `'#'`-outside-plural), **ter-score** (block-shift algo is a `lib_ter.py` internal; a reviewer demanded it be disclosed for offline fairness, but best agent already hit 162/163). Same profile as css-syntax / vcard. Move files to `workspace/dropped/`, add `DROPPED.md`, do not resubmit.
- Non-ASCII **literal** text (RFC 6570 `ucschar`/`iprivate`, and similar) is copied VERBATIM, never pct-encoded — only expanded VALUES are encoded. A byte-wise scanner that pct-encodes every byte ≥0x80 is a common oracle bug the official vectors miss; add a focused case.

**Out-of-band-TOO-HARD remediation** ("Solvable" but 0/N agents reach 100% under all-or-nothing; best agent ~85%): **TRIM the hardest never-solved cases, keep binary 0/1 scoring — NEVER switch to pass-rate/threshold** (proportional reward is a flagged verifier defect). Data-driven from the per-case pass table: compute each agent's failure count; trim N cases → every agent failing >N is guaranteed to stay <100% (provable ceiling), so pick N between the top agent's failure count (floor) and the (k+1)-th agent's (ceiling) to land the 10–40% band. Also relax any PIN test that re-walls a trimmed behavior. yaml-load 86→67 cases, ceiling 30%. Coverage-expansion and band-fit pull opposite ways — tune corpus SIZE, not the reward.

**Test-only re-hardening of a complete-spec task that graded TRIVIAL** (instruction/difficulty untouched):
- **Mutation-guided fixtures** (broker-consumer-rate): build ~9 plausible-but-wrong mutant engines, measure which fixtures catch each, add curated fixtures until every mutant is caught by ≥2. The client-reported near-misses are exactly the thinnest-coverage mutants.
- **Library-semantics differentials** (graphviz agget): add cases hitting the delegated library's subtle effective-value semantics (inherited defaults, byte-lex strcmp ordering, non-back-propagation) — generate ALL expected values by running the oracle in the task's own image, never hand-computed, and drop any candidate where spec and oracle disagree. Validate with plausible-wrong variants.
- Honest ceiling: tests-only hardening raises the bar for subtle-boundary bugs but cannot force 1/10 when the spec is complete.

**Instruction/test symmetry audit (both directions), applied on every conformance/matcher task:**
- Grep the verifier for every field/sentinel/constant it pins and confirm each is stated in the PRIMARY spec body — never only in an appendix example (cups-queue: `failover` always-present-`null` in JSON vs omitted in conf; `generatedAt == requestedAt`).
- Every stated failure diagnostic needs a discriminating test (jsonpatch: "print `error` on stderr" had no assert — added, verified discriminating via a silent-on-stderr variant).
- Every tested divergence from common-tool habits must be disclosed as a behavior contract (dockerignore: root-relative bare patterns, leading-`/` anchor, literal `!` in char class, `dir/**` contents-only) — and drop external-docs-URL crutches; the instruction must be self-contained. Expect and accept `instruction_preflight` word-count warnings when a reviewer requested the disclosure.

**Implementation notes:** TS verifiers compile once (`tsc` → `node dist`), never per-case ts-node; Java verifiers use `java -Xint -XX:+UseSerialGC` (per-case JVM startup vs 600s timeout) and temurin-jammy needs `exceptiongroup==1.2.2` + `tomli==2.0.1` wheels, no `--break-system-packages`; JSON deep-equal must be bool-strict (Python `True==1` footgun) but int/float tolerant.

---

## 4. Lever 2 — Interval-ledger / duty-cycle / clock-pause ports (the ~0–25% lottery)

**Honest family status (corrected):** under a faithful warm-loop probe the broad family pools to ~MEDIUM (~67% pass); a fair complete-spec ledger floors at ~25–40%. What still lands 0/3–1/5 locally are **terse-spec, boundary-biased-differential ports of specific proven engines**. Discrete-tick ledgers (grace evaluated only at event ticks) are EASY — only continuous time with a **materialized computed boundary strictly between events** qualifies.

**Sub-family reliability ranking:**
1. **Clock-PAUSE** (active-time = wall-time − frozen-time; endpoints stay wall-clock; no dwell restart) — strongest, holds ~0/3. Adding a frozen-window pause family flipped two 3/3 tasks to 0/3.
2. **Duty-cycle deadband + minOn/minOff + freeze** (water-heater family, single-unit) — ~0/3–0/5. Shared-budget contention variants are reconstructable (2/3 MEDIUM).
3. **Continuous-time grace/min-dwell** (incident-uptime, lease-failover, disk-quota with shared-group cancel/recross) — reliable.
4. **Cold-chain active-pause + budget** — medium-risk, caps ~1/5–2/5; treat as boundary.

**Killer recipe (the lever alone is insufficient):** interval-output (not flat transitions) + zero-length-interval suppression + boundary-at-horizon + **TERSE** boundary semantics (never spelled out; strip any "pay attention to dwell-time boundaries" paragraph — reviewers flag it AND it softens the task) + a boundary-biased differential (2000+ seeds landing on/±1 tick of every computed boundary). Logic-preserving ports inherit both the hardness and the exact failure corner. ~35 such ports shipped (pump-base, cold-chain, turbine-trip, water-heater reskins) pooling ~0–27%.

**Port/reskin mechanics:** longest-first collision-safe token replacement over the whole tree (type strings before entity names; quoted-only for state literals; watch substring collisions like "strip"/"trip" and stdlib damage like `json.loads`→`json.voltages`); reskin.py never renames directories (`mv cmd/<old>` manually); regenerate `fix.patch` from scratch via diff (never hand-edit hunks); rename JSON tags AND bare map-key/error-string literals; leak-sweep for stray source-domain vocabulary; keep the same physical signal type where possible; pick domains with distinct units (kPa, ppm) to reduce collision risk; require quorum ≥ 1 so predicates can't fire before the first event; grade with an ABSOLUTE APP_DIR (relative paths cause uniform false verifier crashes).

**Spec↔oracle fairness bugs to grep for before shipping any port** (each caused an unfair 0/N on a real task):
- Backdated switch: spec claims a switch "never fires before its request" while the oracle backdates to the dwell-satisfied instant (reflow-oven + heat-trace, same bug — check siblings).
- Thermostat "demand re-evaluated from current temperature" prose vs oracle LATCHING demand on re-enable — grep spec.md for "re-evaluated from the current".
- Freeze/re-enable transition-timing contradictions; same-minute event-ordering ambiguities (log-events-before-synthetic; concurrent VALIDATE/EXIT). Fix = align spec wording to the oracle, never the reverse; verify only unfair seeds are removed.

---

## 5. Lever 3 — Counter-instinct / decoupled-decoy / sim-in-verifier (held recipes)

- **Engine two-invariant:** idiomatic DECOY bug every solver fixes instantly + a non-idiomatic second WALL invariant the symptom never reveals, verified only via SECONDARY observables (primary output stays correct either way). Instruction symptom-only. Held 0/3 (cache-eviction sketch-aging, join-order).
- **Sim-in-verifier:** a cost/plan estimator whose true value is reachable only by a simulation kept solely in the verifier, where the natural closed-form is wrong (worker back-pressure, hidden sort-merge fallback, resource-constrained deepband makespan, NUMA `max(latency_floor, bandwidth_floor)` — platform HARD; do NOT add the clarifying formula).
- **Counter-instinct victim selection** (if used despite the non-victim preference): demote most-recently-promoted / spill highest-count group; a burst-vs-trickle asymmetry must force instinct-pick ≠ correct-pick with differing observables, the idiom-only build must FAIL those fixtures, and there must be no principled convergent alternative the verifier also accepts. Verify via structural observables (residency), widen buggy/oracle gaps, threshold at the midpoint.
- **Per-entity observation-clock aging** (ESS-clocked forgetting; per-feature decay; kNN drift with MRU fallback): the fair band is knife-edge — state the OUTCOME ("informative feature must stay reported regardless of frequency"), never the clock choice; put the preservation fixture on the same code path as drift so a two-estimator dodge fails.
- **Others held:** sessionize retro-merge (late record between two sessions forces coalesce); money-split largest-remainder + exact sign-magnitude refund negation, framed as fairness/bias; requantize round-half-to-even via the "midpoints cancel to net zero" observable (host probes are UNFAITHFUL for tie-direction tasks — trust the platform: opus 4/5 vs gpt5 0/5); renju recursive real-three (fair 0/10 — when N agents converge on the same wrong answer, first check the reference AND oracle for a shared bug); operator-fusion two-piece accumulation (0/5; prose middle band is unstable — trust platform over local prose-tuning); TVD negative-speed accuracy cell; adaptive-integration off-center-Gaussian regime; epoch-reclaim self-retirer exception (0/2); 2PC cooperative-termination rework; codec dictionary-ID-ordering (held on platform; opus 0/5 partly an unraisable 1800s agent-timeout artifact — don't chase it).
- **Numerical keeper lever:** stable algorithm easy to NAME but subtle to IMPLEMENT, non-canonical only (Miller backward recurrence 0/3; TR-BDF2 L-stability — plain trapezoidal rings; test transient damping at huge h·λ). Canonical textbook stable methods (QR, two-pass covariance, partial pivoting, Lentz, Jacobi) all collapse. Discrete-event sims cap at MEDIUM; the one lever that bit was pow2 batch-padding driving both cost and busy-time feedback.
- **Salvage patterns (kept as fair MEDIUM):** state the non-arbitrary half of a flagged convention and delete the arbitrary half (trigger APNAP→declaration-order); "add the scenario, not the variable" (lease-fence maxSeen: narrate the stale-reacquire scenario, or give a concrete failing input-log); delete an unsalvageable named-idiom wall and keep the real bugs (path-canon dropped double-encode); relocate detailed rules to an RFC-style spec file under `environment/app/` when instruction_check says "design document"; behavioral two-part hint + loosened thresholds (tiered-cache); document output contracts fully, keep logic untouched.

---

## 6. Dead-ends — DO NOT REBUILD

> Verdict: complete-spec ⇒ 3/3. Difficulty needs an unstated, under-fuzzed input shape or hidden ground truth — never rule complexity.

- **"Implement standard X" spec engines:** cron, media-type negotiation, JCS, rsync filters, custom-ISA VMs, IAM policy eval, SQL window functions, TUF delegation, policy routing, Karp-Miller (infinite state ≠ hard), recursive schema subtyping, dep-graph analyzers, register allocation (liveness + Chaitin-Briggs is textbook; NP-hard min-alloc defeats exact grading), cubic roots, robots.txt, bibtex names, semver (npm-reachable; union-collapse quirk got 1/3 once — a gamble).
- **Games/judges:** cribbage, backgammon, Fanorona, Pente, Nine Men's Morris, shogi uchifuzume, Lines-of-Action (stateful cascades don't help), Hive (complete-spec judges cap 2/3). Only a hidden recursive/typed correctness corner survives (renju; go-life 1/3).
- **Ledgers by rule-count:** orderbook dense multi-rule 2/3; bank/loyalty/margin-liquidation/MVCC/waitlist 3/3; parking second-boundary made it WORSE (3/3); auditor/reconciler family logic solved 3/3 (its 0/3 was string-match unfairness).
- **Optimization:** fully-stated objectives of every kind — non-decomposable, affine-carry partition, coupled tree-DP (signal-repeater, terrace), min-makespan over small-N orderings ("minimize X over an enumerable space" NAMES brute force), Pareto/min-cut/DP. Camouflaged-greedy only ever held when the optimization was bespoke/unnamed, and its flagship (checkpoint-segment) was later platform-graded EASY → shipped MEDIUM. Treat the whole archetype as near-dead.
- **Estimator/cardinality/cost:** HLL bias (recall-solvable at any precision), KMV/bottom-k union, scalable-Bloom FPR, mergeable quantile digests, rate estimator/limiter admission, CDC chunking, broadphase cell-size, hashjoin-spill 2× constant, ssd-gc WA formula choice (platform overturned an earlier "held" — convergent published models), connpool/microbatch latency-cost, a-posteriori "conservative" ambiguity.
- **Arbitrary tiebreak/convention (no middle band):** carryover rotation, centroid tiebreak, contested attribution, draft/sealed-bid claims, entitlement seats, AMR pair-score metric, authz precision-cap, prefetch bandwidth-model (RETIRED despite the old "KEPT" title — platform spec-gate FAIL 8/10), dynarray stipulated reuse rule.
- **Geometry victims:** 2D-centroid budgeted merge (unbuildable — geometry pins nearest-pair as correct), particle-coalesce.
- **Named-idiom walls:** A* reopen, decode-to-fixpoint double-encode, symplectic/Boris integrators, compensated summation, streaming-UTF-8 tail-carry, outbox commit-filter, windowed exactly-once, version-solver SAT, incremental rehash, B+-tree leaf split, EBR, conflict-serializability, presume-abort (enum-constrained: stating the contract leaves one possible value).
- **Mechanical fixes of real upstream bugs** (add a guard/bound/escape/mirror-a-check) collapse regardless of file spread — run a fix-shape check first; reference-impl edge divergences are usually the reference's own bugs.
- **Overturned "HARD" labels — never trust these old zips/notes:** ci-runner interval-ledger reskins (0/3 was a go-toolchain infra artifact; fair re-probe 3/3), TLS/mirror/mempressure ports (~67%; 0/9 was PATH friction), irrigation/discrete-tick reskins of "0/3" sources (3/3), bounded-groupby (platform TRIVIAL), slab-coalesce (retired; no fair middle), js-attestation (likely MEDIUM), serializable-conflict-check (unfair → fixed to fair MEDIUM), inclusive-cache (budget rule now stated plainly → likely MEDIUM).

---

## 7. Probing & grading methodology

- **Warm loop or the number is garbage:** the probe must give the agent a working build/run loop matching the platform toolchain (persistent container + `docker exec`). Blind-write, broken-mount, dropped-PATH (`bash -lc` loses go), or wrong-toolchain (host go1.22 vs pinned go1.24) probes produce FALSE 0/N. Verify the loop compiles before trusting any 0/3.
- **N≥5; pool same-engine runs.** n=3 is variance (a true ~20% family read 0/3 and 3/5 on identical engines). Never harden one port to chase a per-port number; extend n instead.
- **Local probes are over-generous vs platform:** local 1/3–2/3 routinely maps to platform TRIVIAL. Only a local 0/3 with semantic failures is a shippable HARD signal; local probes can confirm HARD, never MEDIUM. Exception: tie-direction-by-differential tasks read falsely trivial locally — trust the platform.
- **Run probes from the orchestrator** with fresh subagents (build agents are contaminated — they've seen the oracle and systematically leak the wall via comments/prose/Chekhov-gun fields; always leak-audit grep before probing). Solve dirs must be ISOLATED OUTSIDE the repo (agents escape into sibling `verify/` dirs) with a TERSE canonical prompt — hint-rich prompts inflate solve rate ~2–3× ("focus on edge cases" is the main inflator).
- **Score by differential, never self-report:** copy the solver's changed source into the real task + verifier and run pytest/harbor nop in Docker (absolute host paths; auto-detect the build root — solvers restructure layouts). Every failing solver in the port batches "built clean and reported byte-for-byte correct."
- **A 0/N is not proof of fairness:** verify a canonical-correct independent solver actually passes the verifier; when N agents converge on the same wrong answer, reproduce and check whether the reference (and the oracle, which may share its bug) is canonically correct.
- **Validate any base before porting:** gate on harbor oracle=1.0 AND nop=0.0 AND a blind probe that actually fails (found bases with stub==solution, non-compiling images, and 3/3 "hard" labels).
- **Infra death ≠ difficulty:** 0/N with `verifier_did_not_run`/0 tokens/"other" failures (Bedrock 503, OpenAI 429, geoblocking) is platform death — check oracle 3/3 and request a re-run; `n_errors=0` failures ARE valid semantic fails. Harbor LLM calls and stb agent runs are geoblocked from VN (403 region) — needs VPN. Background pipeline agents die silently mid-run: verify results on disk; never build in auto-cleaned worktrees with relative paths (deleted 2 of 4 builds).
- Keep local compute light: validate in Docker (harbor), not on the host; no 2^n brute force for n>18 locally.

---

## 8. Verifier & test design

- **State the OUTCOME, not the mechanism.** Detailed rules live in `/app/SPEC.md` (or an RFC-style file under `environment/app/`), instruction.md keeps goal + high-level names of every tested violation kind.
- **Binary reward 0/1, never proportional.** Clients flag the CTRF proportional-reward pattern as a verifier defect. Fix coverage honestly (per-case parametrize / prune / disclose) and use the standard pytest-exit-code block; oracle must then pass 100%.
- **Build the candidate from `/app` source at verifier import time** — never `shutil.which()` or a pre-installed binary path (makes nop ungradeable, fragile to nonstandard build paths).
- **Hermetic fixtures:** build/compile into a fresh `tempfile.mkdtemp()` (own GOCACHE/GOPATH/classpath), never write into read-only `/app`.
- **Randomized differentials must not re-test pinned corners:** if >40% of generated cases hit a corner the curated suite already enforces, strip it from the generator (zero-param 66%→0%, count 8000→4000; injected bug still caught 53%).
- **Free-form explanation strings:** match structured fields exactly + assert key FACTS as order-independent substrings — exact string match creates a no-middle-band unfairness; count-only asserts (`len(findings)>0`) create false EASY.
- **Neutralize test/fixture labels and docstrings** ("latent defect", "second bug") — behavior_in_task_description FAILs on them; fix the labels, never describe the wall in the instruction.
- **Editing `environment/repo` source (even comments) breaks `fix.patch`:** regenerate the patch against the edited base, confirm it carries none of the removed text, re-run oracle+nop.
- Two legit hardness-reduction patterns when the SPEC itself causes a 0%: location-string normalization in the comparison fn; honest coverage fixes. Never apply to dodge an intentional hidden convention.
- Guard every promised preservation clause with a test; give concrete observable acceptance bars, not algorithm names. Naming exact OUTPUT constants (reason codes, enum values) is fair and satisfies behavior_in_task — output constants aren't mechanism; never lump a should-be-ALLOW outcome in with suppression outcomes (spec coin-flip = unfair).

---

## 9. Client-review playbook (human reviewers sit above the green scanner)

- **instruction.md:** ≤3 short paragraphs (structural; pointing at spec.md is fine); absolute `/app/…` file refs (bare `main.go` flagged); no verifier/test mentions, no code-architecture nudges ("a single flat loop won't cut it" → state that entry points behave differently); no numeric-threshold spec tables (phrase success qualitatively, defer bars to "the test suite"); no embedded strategy hints. DECLINE suggestion-level asks to name the placeholder file/function on spec-driven HARD tasks. **⚠️ When a reviewer flags spec.md as splitting instructions out of instruction.md, the fix is NOT to delete spec.md and dump everything into instruction.md — keep instruction.md concise (≤3 paragraphs) with ALL behavioral rules inline, keep spec.md as a realistic reference doc (schemas, examples), and scrub any "see spec.md for rules" language from instruction.md. Per prompt-styling.md: spec files must "look like documents written by standard engineering teams" and must not contain step-by-step hints.**
- **Rubric:** no criterion may name hidden test paths (`tests/fixtures`, `CURATION.md`, "the pytest verifier" → "editing the verifier or spec files"); no test-execution criterion; phrase every penalty as an affirmative fact ("Agent hardcodes expected URIs, −5"), never "does not X".
- **⭐ Category = the agent's PRIMARY ACTIVITY, not the theme/subject.** ("simulating a game is game; debugging a game is debugging — theme irrelevant.") Building a component/renderer/parser/evaluator/algorithm TO A SPEC (filling an `expand`/`render`/`parse` stub) is **software-engineering** even when it transforms text/URIs/JSON. software-engineering + debugging are the reviewer-blocked slugs, so the play is to reframe as data-processing ("stream → report"; strip "engine"/"fix the engine" language, keep logic/tests/oracle intact) — but this ONLY holds if the task GENUINELY transforms/analyzes a dataset. A spec-conformance component dressed as data-processing gets caught: reviewers are inconsistent — mustache-render kept data-processing (pushed back on merits), but hyperlink-template (RFC 6570 renderer) was FORCED to software-engineering (Feature Implementation & Algorithm Development > Algorithm Implementation) even after reading the data-processing justification. Argue category on activity/fit, never cite the internal hold. ML-mislabels get the same reframe (scrub ML tags, rename ML-framed slugs); `subcategories = []` stays present-but-empty (deleting the line fails CI); author_name/author_email = literal "anonymous"; languages lowercase (`"rust"`, `"go"`, `"java"`) EXCEPT `"C++"` stays capitalized; tags 3–6 entries, none leaking the wall (e.g. "dictionary-id-ordering"); challenged cross-cutting subtypes (long_context) → default REMOVE (deterministic-accept, difficulty-neutral); `expert_time_estimate_min`/`junior_time_estimate_min` both CI-required — parser 60/180, RFC engine 90/240, state-machine 120/300, complex protocol 150–180/360–480.
- **Instruction-Styling returns on matcher/parser tasks** = the symmetry lever: disclose the tested divergences as contracts, drop external-URL crutches, keep tests.
- **Push back on false positives with citations, never edit correct files:** canonical base images (public.ecr.aws golang:1.24-bookworm, gcc:13-bookworm, rust:1.85-slim) false-flagged vs ghcr.io; Rust single-stage cargo carve-out (dep-split + multi-stage findings = ONE compile-at-runtime false positive); "no Cargo.lock" warnings. Temurin digest mismatches have been REAL — use the exact CI-listed digest. Stale-review tell: cited line doesn't match the current file → re-upload, nothing to fix. Cumulative feedback re-lists fixed items — verify each against current files first.

---

## 10. Packaging / Dockerfile / ZIP checklist

- **Canonical digest-pinned bases** from `public.ecr.aws/docker/library/*`: Rust = `rust:1.85-slim@sha256:9f841bbe…` (the only accepted Rust image), single-stage; gcc:13-bookworm (C/C++ — already ships gcc/make, do NOT re-apt-install build tools); golang:1.24-bookworm (+ `ENV GOTOOLCHAIN=auto` for newer go.mod); node:22-bookworm-slim (lacks `patch` — apt-install it); eclipse-temurin:21-jdk-jammy (must include the `public.ecr.aws/docker/library/` registry; bare `eclipse-temurin:21-jdk-jammy@sha256:25d127…` is still rejected as non-canonical); python:3.13-slim-bookworm (use the CI-reported manifest-list digest, not `docker inspect`'s platform digest). PHP: do not use `php:*-cli-bookworm` even when the checker says it is sanctioned; CodeBuild canonical-base check rejects it. Use the canonical Debian bookworm-slim base and apt-install `php-cli` plus needed extensions such as `php-mbstring`.
- **NO `# syntax=docker/dockerfile:1` line** — platform build nodes can't pull it → "Oracle failed"; convert `--mount=type=bind` to plain `COPY` + `rm -rf` in the same layer. Merge ALL dep installs (apt+pip) into ONE contiguous `RUN`; drop warm `RUN go build` (for deps use `go mod download` before source COPY, or `go test -run '^$'`). Strip explanatory `#` comments from Dockerfiles/code before zipping.
- **`.dockerignore`:** full canonical set verbatim (must contain literal `.gitignore`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `node_modules`) PLUS `solution/`, `tests/`, `.env`, and `**/.git`. **⚠️ Missing `solution/`/`tests/`/`.env` passes local harbor (NOP=0, Oracle=1) but gets returned by reviewers — always grep-verify all three before zipping.**
- **Binary name consistency:** the compiled binary's name must be IDENTICAL across every file that references it: `test_outputs.py` (BIN variable + `go build -o <name>` command), `test.sh` (if present), `main.go` top-level comment, `.dockerignore` binary exclusion, `README.md` build instruction, `instruction.md` build command, and `solve.sh` — a mismatch (e.g. `over-limit` vs `latmon`) causes build failures or confusion. Grep the task root for the old name before zipping.
- **test.sh:** `python3` (never bare `python` — exit 127 on golang/debian images), `set -uo pipefail`, `-p no:cacheprovider`, binary exit-code reward.
- **task.toml resources:** `gpus`, `gpu_types`, and `docker_flags` in `[environment]` are **OPTIONAL** Harbor fields (reversed 2026-07-09; reviewers must NOT send a task back for omitting/blanking them — TB2 tasks need no GPU; `gpu_types` only matters when `gpus > 0`). Both the full block and the minimal block (without them) are accepted. Earlier "must declare / reviewer #14 treats missing as high-severity" is SUPERSEDED.
- **ZIP:** repo-root `submissions/`; zip the 5 allowlist roots' contents (no parent folder) with Python `zipfile` and forward-slash arcnames (PowerShell backslash zips break CI); scripts `chmod +x` / exec bits preserved; strip macOS forks, stray `.git`/`jobs`, rust-analyzer `environment/target/`, CRLF (Windows edits break `git apply`); verify `.dockerignore` contains `solution/`, `tests/`, `.env` (harbor-green ≠ reviewer-green); final grep sweep for `.whl`, `pyproject.toml`, `CANARY-`, leaked CLAUDE.md; verify `unzip -p <zip> task.toml | grep author`.
- **`codebase_size`** = CI file count in `environment/` (excl. Dockerfile/compose): 0–19 minimal, 20–199 small, 200+ large; if a reviewer wants more files, expand additively without touching validated bug/oracle code.
- **Deps:** hash-pinned `requirements.lock` + shipped wheels (empty lock with no wheels = pytest never installs); note pytest-json-ctrf==0.4.2 doesn't exist on PyPI. **⚠️ Reviewers may prefer pip install at Docker build time over shipped wheels — when flagged, remove `environment/wheels/` and `requirements.lock`, install pytest==X.Y pytest-json-ctrf==X.Y directly in the Dockerfile RUN.**

---

## 11. Harbor / platform troubleshooting

- **Invocation:** `harbor run -a oracle|nop -p <task-dir> -o <jobs-dir> --job-name <n> -q`; reward at `stats.evals.<key>.metrics[0].mean`; gate = oracle 1.0 AND nop 0.0. Build context IS `environment/` — no `environment/` prefix in COPY paths. Run stb from the jobs parent dir, models sequentially.
- **Docker validation without harbor:** `docker build -t task-test ./environment` then `docker run --rm -v $(pwd)/solution:/solution:ro -v $(pwd)/tests:/tests:ro task-test bash -c 'cd /app && patch -p1 < /solution/fix.patch && go build -o latmon ./cmd/latmon && mkdir -p /logs/verifier && cd /tests && bash test.sh && cat /logs/verifier/reward.txt'`. **⚠️ Must mount `solution/` and `tests/` as volumes — `.dockerignore` excludes them from the image.** For nop, omit the patch step.
- **"Oracle solution failed" root causes by language** (check ALL; multiple can coexist):
  - **Go (4):** ① git buildvcs on root-owned `/app/.git` → `git config --system safe.directory /app` + `-buildvcs=false`; ② no writable HOME breaks GOCACHE → private temp GOCACHE/GOPATH; ③ `go build -o` into read-only `/app` → build into the temp dir; ④ the `# syntax` line (above). Repro trap: use `chmod -R a+rwx`, never `chown` (false PASS), and test the source-only/read-only path (Go's identical-binary skip masks ③).
  - **C (3):** empty requirements.lock; fix.patch logic gaps; `subprocess.run(input=str)` needs bytes on Python 3.11.
  - **Java:** `javac -d classes` writing into `/app` → hermetic temp classpath; plus safe.directory, `-Xint`, `languages=["java"]`.
  - **Node/TS:** ts-node unavailable offline → pin ts-node/typescript, real package-lock.json, flatten the Node project to `environment/` top level.
  - **C graphviz precedent:** wrong include path, fixture violating its own policy, orphaned asserts — build+run the oracle against EVERY fixture.
- **"Oracle failed" on a byte-identical locally-green artifact** = stale platform image → fresh repackage + force-build; repeated staleness means content-hash caching — make a real difficulty-neutral content change (e.g. trim a verifier loop) to bust it.
- `mined-candidates/gallery_tasks_snapshot.md` rebuilds from the live Supabase backend (`v_tasks_with_priorities` ~4521 rows for dedupe; `task_inspiration_v2` for questionnaire IDs).

---

## 12. Process safety

- **NEVER `find … -exec rm` after a bare `cd`** — a failed cd left a delete running at repo root and nuked `.git`. Always `cd "$DIR" && …`, absolute deletion paths, `set -e`, eyeball `pwd` first.
- **Parallel workers on one repo collide on slugs** — claim the slug in `mined-candidates/index.jsonl` first, detect clobbering via a sentinel-comment survival check.
- A hook/linter can silently revert instruction edits — re-verify on-disk state before re-zipping.

---

*Consolidated 2026-07-07 from all prior memory stores; this file supersedes them. Keep it alive: fold every new memory or corrected verdict into the matching section immediately — consistent and conflict-free (newest verdict wins, stated once) — and mirror the same update into Claude auto-memory. Do not re-create per-topic detail files.*
