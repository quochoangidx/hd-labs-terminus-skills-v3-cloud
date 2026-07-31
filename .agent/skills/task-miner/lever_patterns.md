# Lever Pattern Catalog — shared, in-repo, read before mining a HARD task

> **⛔ STATUS (2026-07-19) — this catalog predates the category classifier.** The
> L1 conformance-parser stub-fill shape is CATEGORY-DEAD: it predicts
> `software-engineering` = BLOCKED (rule R4 in `category_rules.md`), and the
> classic engines (WHATWG-URL, IDNA, UAX-14/29, HTML5, version-constraint, URI
> template, LOWESS…) are saturation-CLOSED in the ledger
> (`.agent/mined-candidates/platform-passed-portfolio.md`). The L1 runbook below
> remains valid ONLY for remediating already-returned legacy tasks, or for a
> shape that FIRST passes the rules-first category gate. **Every build must run
> the category gate (`category_rules.md`) BEFORE building — never after.**

**Why this file exists.** A *lever* (the technique that makes a task HARD *and* fair)
is the reusable asset. The *resource* a lever is applied to — a conformance suite, a
spec, a repo, a dataset — is a small, SHARED, finite commodity. This catalog lives in
the repo (symlinked to every CLI), **not in anyone's personal memory**, so every
teammate — with memory or without, whatever CLI — describes and dedups tasks the same
way. **Learn the pattern here; pull a FRESH resource from the claim ledger below; never
reach for a resource just because this file names it as an example.**

This is the concrete, sharable form of the rule "LEARN THE PATTERN, NOT THE RESOURCE."
It replaces relying on any individual's memory for that rule.

## How to use

1. Pick a lever by its `intent`.
2. Fill its `resource_slot` with a spec+suite that meets every `necessary` condition and
   hits none of the `disqualifiers`, **and that is NOT already in the Claimed-resource
   ledger** (below) or in `mined-candidates/index.jsonl`.
3. **Claim before building.** Append one line to `mined-candidates/index.jsonl`:
   `{"lever":"<id>","conformance_suite":"<url/name>","spec":"<name+version>","language":"<lang>","gallery_category":"<cat>","task_slug":"<slug>","owner":"<you>","status":"claimed"}`
   and add a row to the ledger below. The dedupe key for this lane is
   `conformance_suite + spec + language` — slug/repo/issue keys do NOT catch these
   collisions.
4. Run the `fairness_gate` before you call it HARD.

For lever **L1**, do not improvise from these fields — follow the **L1 build procedure**
near the end of this file top-to-bottom. It is a complete, memory-free runbook (pivot-check,
messy-spec check, blind probe, fairness audit, disclose-vs-collapse, instruction_check).

## Pattern spec — every entry uses these fields

```
id:                 short kebab name of the lever
intent:             the HARD + fair property it produces (resource-agnostic)
mechanism:          the recipe, written WITHOUT naming any specific resource
necessary:          conditions the resource MUST satisfy
disqualifiers:      resource shapes that collapse the task to EASY
fairness_gate:      how to detect an UNFAIR artifact before shipping
resource_slot:      the VARIABLE — filled per task from a fresh, unclaimed resource
dedupe_cell:        gallery_category × language × lever  (novelty is per-cell)
dedupe_key:         conformance_suite + spec + language  (mirror into index.jsonl)
```

---

## L1 — `conformance-suite-divergent-tail`

> **⛔ CATEGORY-DEAD for fresh builds (2026-07-19):** this stub-fill
> parse/normalize-to-spec shape predicts `software-engineering` = blocked
> (`category_rules.md` R4), and the classic engines are saturation-CLOSED
> (`.agent/mined-candidates/platform-passed-portfolio.md`). Use this runbook
> only to remediate already-returned legacy L1 tasks, or after the shape
> passes the rules-first category gate.

- **intent:** a from-scratch implementation task that a strong agent solves only 0–1/3,
  because independent *full* implementations each miss a DIFFERENT slice of the spec's
  long tail.
- **mechanism:** ship a stub + a pointer to the spec; bake the OFFICIAL
  machine-checkable suite HIDDEN under `tests/`; oracle passes 100%, nop fails on the
  divergent tail. (Answer table in `environment/repo` makes it trivial — see task-clone.)
- **necessary (ALL must hold):**
  - an official, machine-checkable suite exists over the spec;
  - the spec has a genuinely divergent / irregular long tail. The strongest positive
    signal is **REAL-IMPL-AS-SPEC**: ground truth is the accreted quirks of a real
    implementation that nobody DESIGNED (Maven/semver/conda/croniter ordering rules,
    browser-compat WHATWG behavior) — a frontier model cannot re-derive from principles
    what was never principled. A deliberately-designed, precisely-written standard fails
    this even when intricate (see the disqualifiers);
  - NO reference implementation is reachable IN THE ENVIRONMENT — vet EVERY language
    and tool on PATH in the task image, not just the task language's stdlib. Agents
    pivot across languages: if the image ships `python3` (needed by the pytest
    verifier!), a Python stdlib or preinstalled decoder for the spec COUNTS and
    disqualifies the resource. Learned the hard way — see the TOML disqualifier;
  - real independent implementations disagree on the tail — people implement it
    INCONSISTENTLY. (This is the necessary-not-sufficient condition; the suite alone
    is not enough.)
- **disqualifiers (each observed 3/3 EASY — reject the resource):**
  - clean finite rule-set + a provided property table (e.g. a WORD-break-style segmenter);
  - a well-known named algorithm (e.g. byte-BPE);
  - a clean bidirectional codec (bech32 / punycode / structured-fields shape);
  - a clean matching engine (git-pathspec shape);
  - a PRECISELY-SPECIFIED standard, however intricate — including crypto with public
    KATs (rpmvercmp, CLDR plurals with the rules shipped as data, Argon2/RFC 9106 — each
    3/3 EASY, 2026-07-02). Intricacy ≠ difficulty: the tail must be one a frontier model
    implementing FRESH gets wrong, not merely one a popular library flubs (RFC 6570
    falsified this — the `uritemplate` lib is wrong on 6 cases, yet Opus 4.8 and GPT-5.5
    both scored 10/10);
  - FAMOUS/memorizable reference vectors (chess perft node counts — blind 3/3): the
    solver self-verifies against memorized constants. Pick specs whose (input→output)
    vectors are obscure lookup-table data (Unicode sort keys, URL parses), never famous
    numbers.
  - **TOML 1.0.0 — DISQUALIFIED (in-env reference impl).** Task language Go has no TOML
    in std, BUT the image installs `python3` and Python's stdlib `tomllib` is a
    ~99.7%-compliant decoder. Agents pivot to it: in the `tbrain-toml-document-decoder`
    Harbor run, 5/10 agents ran `import tomllib` → 712/714, failing ONLY the 2 UTF-8
    BOM cases. The lone surviving "lever" (BOM) is undisclosed → `Task Instruction
    Sufficiency: ❌ FAIL`. No-win squeeze: hide BOM = unfair-hard (fails
    instruction_check); disclose BOM = tomllib pivot scores 714/714 = collapses to
    EASY. Not salvageable by prose — Python can't be removed (the verifier needs it).
    Retire the resource; the same flaw hits any TOML task in a Python-bearing image.
- **fairness_gate:** if *all* failing runs miss the SAME single narrow test, that is a
  spec-AMBIGUITY, not hardness — disclose/relax it; do not ship as HARD.
- **resource_slot:** `<spec + its official suite + implementation language>` ← FILL FRESH
- **dedupe_cell:** `gallery_category × language × lever`
- **dedupe_key:** `conformance_suite + spec + language`

### Claimed-resource ledger for L1 (DO NOT REUSE — pick something else)

Authoritative machine copy = the `lever:"conformance-suite-divergent-tail"` lines in
`mined-candidates/index.jsonl`. This table is the human-readable mirror; keep both in sync.

| resource (official suite)        | spec              | language   | owner        | status | note |
|----------------------------------|-------------------|------------|--------------|--------|------|
| web-platform-tests urltestdata   | WHATWG URL        | Rust       | nhonho-batch | built  | |
| Unicode IdnaTestV2               | UTS-46 IDNA       | Go         | nhonho-batch | built  | |
| Unicode LineBreakTest            | UAX-14            | C          | nhonho-batch | built  | |
| jsonpath CTS                     | RFC 9535          | TypeScript | nhonho-batch | built  | |
| toml-lang/toml-test              | TOML 1.0.0        | Go         | nhonho-batch | built  | **DISQUALIFIED + COLLISION** — in-env `tomllib` reference (see disqualifiers) makes both this and our tbrain-toml-document-decoder unfair-hard; RETIRE both, do not rebuild TOML under L1 in a Python image |
| html5lib tree-construction       | WHATWG HTML §13   | Rust       | this-workspace | built | near-neighbor of the URL task (same Rust × WHATWG-conformance cell; historically filed under Data-Processing — that classifier label is BLOCKED since 2026-07-11, grandfathered only) |
| html5lib tokenizer               | WHATWG HTML §13   | (team)     | team         | built  | |
| Unicode SENTENCE-break (UAX-29)  | UAX-29 sentence   | (team)     | team         | built  | |
| JSON-Schema-2020-12 suite        | draft 2020-12     | (team)     | team         | built  | unevaluated* + $dynamicRef tail |
| chess perft node-count vectors   | FIDE legal movegen| C++        | this-workspace | REJECTED | **too easy — blind Opus 3/3 (58/58).** Perft node counts are FAMOUS/memorized numbers, so a one-shot solver self-verifies against them and reliably produces a correct legal generator. LESSON: a resource whose reference vectors the solver has MEMORIZED (or can look up) defeats L1 — the solver self-verifies. Pick specs whose (input→output) vectors are NOT memorizable (Unicode sort keys, URL parses), not famous constants. |
| Unicode CollationTest (UCA)      | UTS-10 + DUCET    | C++        | this-workspace | claimed | replaces chess; variable-weighting SHIFTED/NON_IGNORABLE + contractions + implicit weights tail; sort keys are NOT memorizable → solver cannot self-verify |
| css-tokenizer-tests (romainmenke)| CSS Syntax L3     | Go         | this-workspace | claimed | escapes/number/url-token/bad-string recovery tail; no stdlib CSS tokenizer in Python |
| RFC 5545 RRULE vectors           | RFC 5545 RRULE    | Rust       | this-workspace | claimed | BYSETPOS/BYDAY-in-monthly/negative BYMONTHDAY/WKST tail; dateutil not in stdlib |
| Maven ComparableVersion + ComparableVersionTest | Maven ComparableVersion (maven-artifact 3.9.9) | Go | this-workspace | built | **HARD (blind Opus 0/3, ~890/8015 miss)** qualifier-precedence (alpha/beta/milestone/rc/cr/snapshot/sp + unknown-lexical), digit↔char transition, `.X` vs `-X` sub-list, aliases, trailing-null normalization tail; ground truth from real Maven; Python `packaging` is PEP440 not Maven → no pivot. tbrain-maven-version-order |
| node-semver test fixtures        | npm semver ranges | Rust       | this-workspace | built   | **HARD (blind Opus 0/3, 28–133/3131 miss)** prerelease-inclusion + caret/tilde-on-0.x + `-0` valid_range canonicalization tail; no npm-semver in Python (PEP440 differs). tbrain-semver-range-satisfies |
| json5/json5-tests (relabelled)   | JSON5 v1.0.0      | C          | this-workspace | built   | qualifies but BORDERLINE (blind Opus 1/3 fail, U+2028/2029 string line-continuation); ECMAScript IdentifierName keys + number-grammar tail; Python `json` is strict JSON. tbrain-json5-parse |
| rpm tests/rpmvercmp.at + pairwise | RPM version cmp (rpmvercmp) | Rust | this-workspace | REJECTED | **too easy — blind Opus 3/3 (2599/2599).** rpmvercmp is a SMALL clean well-known algorithm; version-ordering is NOT uniformly hard (rpm≠maven/semver, which are hard for their LARGE irregular tails). |
| CLDR plurals.xml + @integer/@decimal samples | UTS-35 Pt5 plural rules | Go | this-workspace | REJECTED | **too easy — blind Opus 3/3 (3170/3170).** Shipping the rules-as-data + spelling out operands (needed for sufficiency) leaves nothing divergent → over-specified standard collapses. |
| RFC 9106 KAT + argon2-cffi corpus | Argon2 v1.3 (i/d/id) | C | this-workspace | REJECTED | **too easy — blind Opus 3/3 (1804/1804).** Precisely-specified crypto standard w/ public KATs; Opus reproduces exactly. Intricacy ≠ difficulty. |
| croniter reference (generated) | cron next-fire-time (croniter dialect) | Go | this-workspace | **built HARD** | **blind Opus 0/3 (broad 6/7-group fail).** Large quirky real-impl surface: DOM/DOW OR-rule, L, d#n, 3 step forms, name-range endpoints, X-X→full-range croniter quirk, year rollover. tbrain-cron-next-fire |
| Ruby Gem::Version/Requirement (host ref) | RubyGems requirement satisfaction | Go | this-workspace | REJECTED | **too easy — blind Opus 2/3.** Gem::Version well-known; RubyGems has NO prerelease-exclusion quirk → surface too small. (RANGE-satisfaction generally hard — see semver — but needs a big quirk set.) |
| portage.versions.vercmp + tests | Gentoo/PMS ebuild vercmp | Go | this-workspace | REJECTED | **too easy — blind Opus 3/3.** leading-zero-fraction rule has an equivalent simple formulation; suffix precedence documented. |
| cyberphone testdata + node/V8 (ES6) | RFC 8785 JSON Canonicalization | Go | this-workspace | REJECTED | **too easy — blind Opus 3/3.** ES6 Number::toString + UTF-16 key sort + minimal escaping all documented; Opus reproduces. |
| RFC 3986 sec 5.4 + port | RFC 3986 URI reference resolution | C | this-workspace | REJECTED | **too easy — blind Opus 2/2.** sec 5.3 is well-documented pseudocode; structural urljoin-divergence doesn't help (solvers implement from knowledge). |
| conda VersionOrder (host ref) + test_version | Conda version ordering | C | this-workspace | **built HARD** | **blind Opus 1/3** (2/3 fail on `_`-separator ambiguity, dev/post sentinels, string<int, fill-0 phase). Weirder than rpm/gentoo. tbrain-conda-version-order |
| uritemplate-test suite + uritemplate lib | RFC 6570 URI Template L1-4 | Rust | this-workspace | built — difficulty FALSIFIED | Original blind Opus 0/3, but a 2026-07-02 re-probe of the same spec scored Opus 4.8 AND GPT-5.5 both 100% (10/10) = TRIVIAL — a clean, memorized templating spec. LESSON: "a popular lib fails N cases" is NOT evidence a frontier model fails; the model implements FRESH from the spec, it does not inherit the lib's bugs. Never re-pick RFC 6570 (any new task would also duplicate this one). tbrain-uri-template-expand |
| mustache/spec (non-lambda)       | Mustache manual   | Go         | this-workspace | REJECTED | **too easy — blind Opus 3/3 (136/136).** Core mustache (standalone-whitespace + partial re-indentation) is a clean spec Opus reproduces; verifiable-divergent modules (lambdas) aren't data-checkable. LESSON: templating / clean-rule specs collapse like segmenters — prefer IRREGULAR version-ordering / canonicalization tails. Replaced by maven-version-order. |
| editorconfig-core-test + editorconfig-core-py 0.17.1 | EditorConfig format | Go | this-workspace | claimed | glob (brace/numeric-range/**/[]-classes/escapes) + multi-file cascade (root, last-match-wins, section merge) + key-lowercase/unset tail; core-test suite exists BECAUSE cores diverge; no editorconfig in any stdlib. tbrain-editorconfig-resolve |
| soupsieve 2.x (CSS Selectors L4) | W3C Selectors L4 matching+specificity | Rust | this-workspace | claimed | pre-parsed DOM input (not html parsing); nth-child(An+B of S)/:not/:is/:where/:has/attr-ops+case-flags/combinators/specificity tail; no selector engine in Rust/C/py stdlib. tbrain-css-selector-match |
| publicsuffix.org tests.txt + publicsuffixlist | PSL algorithm (eTLD+1, ICANN/PRIVATE) | C | this-workspace | claimed | wildcard `*.`/exception `!`/default-`*`/domain==suffix-null/IDN-punycode/ICANN-vs-PRIVATE tail; .dat provided as input; no PSL in any stdlib. tbrain-public-suffix-domain |
| hjson/hjson-js test/assets | Hjson format | Go | this-workspace | REJECTED 2026-07-06 | **too easy — blind Opus 2/2 OFFLINE pass (96/96).** Opus reproduces the hjson-go decoder from memory even with no network; well-known format = memorized reference. Quoteless-string tail is not divergent-enough. |
| google/cel-spec tests/simple/testdata | CEL language | Go | this-workspace | **built HARD** 2026-07-06 | **blind Opus 0/2 offline (from-scratch interpreter misses 100+/1138).** Large evaluator, no in-env CEL; oracle delegates to VENDORED cel-go under solution/ (stub+env have no CEL, offline GOPROXY=off → solver must implement from scratch). tbrain-cel-eval |
| systemd-analyze calendar (systemd.time OnCalendar) | systemd calendar events | Go | this-workspace | **built MEDIUM** 2026-07-06 | blind Opus 1/3 offline (2 miss sub-second `.000000` truncation). systemd absent from Go image. systemd 252 has NO `~` last-day. tbrain-systemd-oncalendar-next |
| libxml2 XPath 1.0 (differential) | W3C XPath 1.0 | C | this-workspace | **built HARD** 2026-07-06 | HARD: matching libxml2's internal `xmlXPathFormatNumber`/`xmlXPathStringEvalNumber` is not reproducible offline from memory. (Probe was xmllint-CONTAMINATED — dev-box has xmllint, grader does not; solvers reverse-engineered it and still one build-failed.) tbrain-xpath1-eval |
| cargo feature resolution (differential vs cargo) | Cargo feature unification | Go | this-workspace | REJECTED 2026-07-06 | **too easy — blind Opus 2/2 OFFLINE (143/143).** dep:/weak/unification rules are DOCUMENTED; Opus reproduces from memory. Ground-truth via `cargo tree -e normal -f '{p}|{f}'` (NOT `cargo metadata` — it over-reports optional deps). |
| udunits2 (differential) | UDUNITS-2 unit grammar+conversion | C | this-workspace | **built HARD** 2026-07-06 | blind Opus 0/2 offline (miss `%`=0.01 dimensionless + others). Ground truth = real udunits2 in container. NB: M_PI compile-trap (see offline-probe memory). tbrain-udunits-convert |
| sacrebleu (differential) | SacreBLEU BLEU spec | Rust | this-workspace | **built HARD** 2026-07-06 | blind Opus 0/2 offline (both miss ~9 13a-tokenizer fuzz cases from-memory). sacrebleu absent from image. tbrain-sacrebleu-score |
| GNU diffutils `diff -u` (differential) | unified-diff format | Go | this-workspace | REJECTED 2026-07-06 (borderline) | **Opus 2/3 offline = EASY-leaning.** Myers + GNU unified format is well-known; strong solvers reproduce GNU's middle-snake/shift-boundaries. Removed /usr/bin/diff for pivot-safety but algorithm still memorized. |
| RFC 9112 strict framing (hand-authored) | HTTP/1.1 message framing | Go | this-workspace | **built HARD** 2026-07-06 | blind Opus 0/2 offline (miss Host-rules/TE-structure/http-2.0/leading-zero-CL). 22/80 cases diverge from Go's lenient `net/http` → no stdlib pivot. tbrain-http-smuggle-detect |
| PostgreSQL 16 array_in (differential) | PG array text repr | Go | this-workspace | **built HARD** 2026-07-06 | blind Opus 0/2 offline (miss PG16 hex/octal/binary int literals + empty/adjacent-quote rejection). Ground truth = real postgres:16 `array_to_json(...::text[])`. tbrain-postgres-array-parse |
| GNU cpp / gcc -E -P (differential) | C preprocessor §6.10.3 | Go | this-workspace | **built HARD** 2026-07-06 | blind Opus 0/2 offline (miss func-spanning-lines + `#`-stringize-vaargs). Blue-paint/hide-set + prescan is the tail. No cpp in Go image. tbrain-cpp-macro-expand |

### Fresh-resource ideas for L1 — ⛔ HISTORICAL / DEAD (kept as a forbidden-zone map)

**Do NOT mine from this table (2026-07-19; category note updated 2026-07-30).**
The software-engineering category has reopened, but these L1 parse/normalize
stub-fill entries remain closed by saturation, originality, and repeated
difficulty collapse; robots.txt is an AGENTS.md §6 dead-end outright
("hardening a memorized public library is futile"). The table survives only as
a forbidden-zone map for dedupe; fresh mining follows the fresh-only doctrine
(task-miner SKILL.md) and the saturation ledger
(`.agent/mined-candidates/platform-passed-portfolio.md`).
Original guidance, for legacy-remediation context only: probe each ≥3× blind
before trusting difficulty. (Former entries RFC 3986 resolution, ICU/CLDR
plural rules, JSON5, and CSS
Syntax L3 have moved into the ledger above with verdicts — check the ledger FIRST;
several "obvious" ideas probed EASY.)

| family | official suite / ground truth | pivot-check verdict (verify FIRST) |
|---|---|---|
| YAML 1.2 | yaml-test-suite | STRONG — the suite exists BECAUSE parsers diverge (anchors, merge keys, block scalars, the Norway problem); PyYAML is not stdlib |
| CommonMark | spec.txt (~650 examples) | STRONG but probe-first — babelmark proves impls diverge (emphasis delimiter runs, HTML blocks, loose lists); no stdlib markdown anywhere; risk: famous reference impls may be memorized |
| PCRE2 dialect subset | pcre2 testdata | STRONG — Python `re` ≠ PCRE2 exactly on the tail (possessive quantifiers, atomic groups, `\K`); MUST scope-cap the subset or the verifier hangs |
| robots.txt REP | google/robotstxt suite | CAUTION — stdlib `urllib.robotparser` exists; measure how much of Google's suite it passes before claiming |
| CLDR date/number skeletons | CLDR test data | GOOD — ground truth is ICU, unreachable in-env; data-driven, not memorizable |
| RFC 5322 address parsing | — | CAUTION, likely DISQUALIFIED — Python stdlib `email` parses addresses fairly completely; measure the pivot before claiming |
| UAX-31 identifiers · UTS-51 emoji ZWJ · WHATWG Encoding index tables · IRI/IDNA round-trips | Unicode / WHATWG | unvetted pointers |

Auto-disqualified by ALWAYS-ON-PATH references — do not bother probing: anything
defined by `dpkg --compare-versions` (dpkg ships in every Debian-family image), `git`
behavior (wildmatch / gitignore / gitattributes — git is a required agent tool), shell
globbing / word-splitting (`bash` is required), POSIX TZ strings (Python `time.tzset`
is a near-complete reference).

(Legacy context only — superseded by the fresh-only doctrine:) pick one NOT in
the ledger, in a language NOT already paired with it, confirm
independent impls diverge on the tail, and claim before building.

### Widen the language axis (dedupe-cell relief)

The dedupe cell is `gallery_category × language × lever`. With only Rust/Go/C/C++/TS in
play the cells exhaust fast and teammates collide on the same pairings — the language
axis is the cheapest place to create novelty. Beyond the canonical-base languages, any
apt-installable toolchain on the canonical Debian/Ubuntu base runs offline: Lua, PHP,
Perl, OCaml, Haskell (ghc), Erlang/Elixir, Common Lisp (sbcl), SWI-Prolog, R; Fortran
rides the canonical gcc image (gfortran included). See the language-widening bullet in
task-clone's Docker Rules for the sanctioned-base mechanics. Two caveats:

- **The pivot-check (step 2) applies to the TASK language too.** Choosing a language
  ships its stdlib into the image, and batteries-included stdlibs carry reference
  implementations: Ruby `URI`, PHP `parse_url`/intl-IDN, Perl core modules count exactly
  like `tomllib`. Vet the pairing's stdlib before claiming.
- **Niche earns the Hard bonus only while frontier agents still WRITE the language
  competently.** A language the agent cannot produce at all yields Agent-Timeout-Gate
  blockers and 0/N flags, not difficulty — the hardness must stay in the spec tail, the
  language just removes memorized-library crutches.

**Expansion policy (2026-07-02): the palette above is ENOUGH — usage, not breadth, is
the bottleneck.** Every task built so far pairs only Rust/Go/C/C++/TS; force new
batches to draw from the UNUSED apt-lane languages (OCaml, Haskell, Lua, R,
Erlang/Elixir, …) before anyone proposes a new toolchain. Add new languages LAZILY —
only when a concrete candidate demands one, and only from these pre-vetted three:
**C#/.NET** (pinned dotnet on the Debian base, with the non-canonical justification),
**Kotlin/Scala** (ride the canonical temurin base + a pinned compiler zip), and **SQL
via a real DB engine** (the gallery's #2 language and the under-served
`db_interaction` subtype — one such task opens new cells on BOTH axes at once).
BANNED: pre-1.0 / fast-churn languages (Zig, Nim, Crystal, V) — frontier models emit
version-skewed code there, which produces Agent-Timeout-Gate and 0/N tooling failures:
unfair-hard, never real difficulty.

## L1 — build procedure (follow top-to-bottom; a newcomer with ZERO team memory can ship a fair-HARD task from this alone)

1. **Pick a FRESH resource** that meets every `necessary`, hits no `disqualifier`, is NOT
   in the claimed-resource ledger, and ideally in a language not yet paired with it.
2. **Pivot-check (env-wide reference impl).** Confirm NO spec-compliant implementation is
   reachable in the task image, in ANY language on PATH — not just the task language's
   stdlib. `python3` is ALWAYS present (the pytest verifier needs it), so check Python's
   stdlib first. Quick verdicts: `tomllib` = TOML reference → **DISQUALIFY**;
   `urllib.parse` ≠ WHATWG-URL → ok; `encodings.idna` = IDNA2003 ≠ UTS-46 → ok;
   `html.parser` ≠ html5lib → ok; no stdlib JSONPath / line-break → ok. If a reference is
   reachable, reject the resource (it will be trivially pivotable or unfair-hard).
3. **Messy-spec check.** The spec must have a genuinely irregular / divergent long tail
   that real implementers get INCONSISTENTLY wrong. Reject clean finite rule-sets, named
   algorithms, and clean bidirectional codecs — those probe EASY even *with* an official suite.
4. **Claim it** in `mined-candidates/index.jsonl` (dedupe_key = `conformance_suite + spec + language`).
5. **Skeleton probe gate — probe BEFORE building the full oracle/verifier.** As soon as
   you have `instruction.md` + a buildable `environment/` + the stub + a ROUGH check
   command (a thrown-together differential or a handful of hand-checked cases — the
   real oracle and hidden suite do not exist yet), run the skeleton probe
   (`task-local-solve-probe`, Skeleton mode), N≥3. 3/3 pass → DROP or redesign the
   lever now; do NOT spend the oracle/verifier/Docker build on a candidate the
   collapse law already killed. 0–2/3 with semantic failures → proceed to step 6.
   Setup/instruction failures → fix the skeleton and re-probe. This gate exists
   because the old ordering (full build first, probe last) burned the entire build
   cost on candidates that then probed 3/3 EASY.
6. **Build.** Ship a stub (reads input, emits nothing/minimal). Put the official suite
   HIDDEN under `tests/`; oracle = a full correct impl that passes 100%; nop/stub fails.
   NEVER commit the answer table (input→expected) into `environment/repo` — grep for it
   before shipping (see task-clone). Read binary suite files (`.dat`, `LineBreakTest`) in
   BINARY mode; a stray `\r` silently corrupts cases.
   **Design the corpus so difficulty is the UNION of distributed misses, never the
   INTERSECTION.** Valid hardness = many INDEPENDENT quirk families where each solver
   misses a DIFFERENT slice; full-pass probability ≈ the product of per-family pass
   rates (10 families × ~70% each ≈ 3% ⇒ HARD, with a fair-MEDIUM floor since partial
   solutions still score). Target each family at ~40–80% expected per-run pass rate; a
   case you predict fewer than ~35% of runs will pass is a statistical 0/N candidate
   at N=10. **Soft-representative rule:** every feature cluster keeps ≥1 "soft" case
   that a majority of runs pass — never a hard-cases-only corpus (soft cases are the
   coverage that keeps the 0/N flag from firing, and they satisfy anti-hardcoding
   minimum-coverage guards). **Soft size cap:** a curated corpus of ~≤100 cases is
   the right default for a normal task; a large corpus (300+) is justified only when
   the wall is genuinely broad AND the per-case pass-table pre-audit below has run. A case EVERY fresh implementation will miss (insider quirk,
   undisclosed convention, data-table-only knowledge) is intersection-of-misses = a
   guaranteed 0/N flag — disclose it in one prose sentence or drop it BEFORE shipping.
   Structure the verifier per-case (parametrized) or as graded bands whose top band the
   best realistic run can actually reach; never ONE monolithic all-N-cases-must-pass
   function, where a single universal blind spot turns the whole test 0/N, and never a
   group-aggregate test sitting on top of per-case tests (structurally 0/N forever).
   Cheap pre-audit: after the blind probe (step 7), score the probe solvers' diffs
   per-case against the corpus — any case NO probe run passes is a correlated blind
   spot to disclose/prune now (see task-local-solve-probe, Coverage pre-audit).
7. **Probe difficulty AND fairness — do BOTH before trusting the task:**
   - Run ≥3 BLIND solvers (fresh agent, no `solution/`, no `tests/`). HARD ≈ 0–1/3 solve.
   - Do NOT let a solver paste the spec source (blows up context, distorts the probe).
   - Sanity gate: oracle must PASS and nop/stub must FAIL, or the harness is broken —
     that is not a difficulty signal (see the missing-tmux / verifier-did-not-run traps).
8. **Fairness audit — a green `✅ HARD` verdict is NECESSARY-NOT-SUFFICIENT; read the
   per-test failure distribution, not just the pass rate.** A task can report
   `✅ HARD / ✅ Solvable / oracle 100% / agents 0/5` and STILL be an invalid, fake-hard
   task — the disqualified TOML decoder did exactly that: its "hardness" was pure artifact
   (binary all-or-nothing over 714 corpus tests + one under-specified BOM blind spot +
   in-env `tomllib`), and it FAILED `Task Instruction Sufficiency` outright. Trust the
   audit below, not the verdict:
   - A test that **ALL runs fail** (a *universal blind spot*, e.g. TOML's UTF-8 BOM) is an
     UNDER-SPECIFICATION, not hardness; hidden, it fails `Task Instruction Sufficiency`
     (instruction↔test asymmetry). You may disclose it in the instruction to restore
     symmetry — **but ONLY if** (a) partial-fail *surviving levers* still keep it hard AND
     (b) no in-env reference exists. If disclosing it lets the obvious pivot score 100%
     (TOML + `tomllib`), the resource is DISQUALIFIED — retire it, there is no prose fix.
   - Tests that **~half the runs fail** are genuine surviving levers → keep them; predicted
     post-disclosure pass ≈ product of their pass rates (predict HARD without re-probing).
   - Binary all-or-nothing scoring is legitimate here (each impl misses a DIFFERENT tail
     slice) but means one universal blind spot dominates the score — which is exactly why
     this audit is mandatory.
   - **The platform submit-time flag `❌ Some tests not passed by any agent run` is
     BLOCKING, not advisory — the task gets RETURNED (user-confirmed 2026-07-02); every
     verifier test must be passed by ≥1 of the ~10 agent runs.** Full remediation
     decision tree (infra look-alikes → classify each 0/N test → delete redundant group
     test / parametrize per-case / prune / disclose / ship reference data → margin-prune
     the ≤2/N tail → difficulty-retention guards → offline validation) lives in
     `.agent/skills/task-revise-flag-remediation/SKILL.md` — follow it, don't
     improvise. The two hard NEVERs: never delete the per-case parametrized suite or
     collapse the corpus to clear the flag (flips the task EASY), and never prune when
     the 0/N cases ARE the lever (undisclosed reference-class divergence → disclose
     instead). The flag is stochastic across re-runs — re-run to confirm both the
     failure and the fix.
9. **instruction_check pre-flight — run the binary preflight in
   `terminus-regular-task-authoring` (Prompt Rules) BEFORE the first platform check.**
   Prose only: objective + I/O protocol + the authoritative spec/suite reference; no
   `##` headers, no lookup tables, no bullet rule-lists, no algorithm narration, no
   "pay attention" hints, ≤ ~300 words. Traps beyond the basics, each burned once:
   - NEVER invent a custom byte-exact output serialization — a self-invented format
     ALWAYS trips the checker and makes its verdict oscillate table↔prose across
     re-runs (there is no wording that describes a bespoke byte format and still reads
     as prose). Emit natural JSON and make the VERIFIER semantic instead: compare
     ordered pairs, IEEE-754 bit-compare for floats. If dropping the format drops the
     difficulty, re-add hardness in the INPUT DOMAIN (a harder tail), never in the
     output encoding.
   - Naming a standard ALGORITHM (PAVA, Dijkstra, …) and narrating its steps reads as a
     "design document" even in section-free prose. Frame objective-only: goal + output
     property + I/O. Referencing an external tool/standard as ground truth ("must match
     `git check-ignore`") is fine and encouraged.
   - The check FLIP-FLOPS across re-runs. If the items it flags are test-pinned
     literals/values, removing them breaks `behavior_in_tests` (which IS blocking) —
     keep them and SHIP the non-blocking ⚠️; do not iterate wording. If green is
     required anyway: move the disclosure into an in-env reference file
     (`/app/examples.json` — oracle-verified pairs DISJOINT from the hidden corpus,
     COPY'd into the image before `git add -A`) plus a one-line declarative pointer in
     the instruction — clears instruction_check while keeping sufficiency/symmetry
     (semver, 2026-07-02).
10. Ship.

---

## L2 — `synthetic-interval-invariant-ledger`

- **⚠️ STATUS (2026-07-04): SATURATED — cooldown. Do NOT default to this lever.** The
  portfolio already holds 10+ instances that converge in shape AND name
  (`index.jsonl`: broadcast-airtime-, coldchain-excursion-, energy-reservoir-,
  infusion-dose-, metered-billing-, oxygen-deficit-, service-supervision-,
  thermal-duty-`ledger`, plus leader-lease / duty-cycle / settlement /
  interval-arith). Empirical ceiling = **MEDIUM**: pure interval/gap/overlap logic
  probed 3/3 EASY; even a fully-disclosed clamp+carry+reset work-budget variant
  stayed 3/3 blind EASY; iterative frontier agents solve ledger-family tasks
  reliably. Use L2 only as an occasional MEDIUM filler (non-Python) when the batch
  portfolio needs one AND the invariant family is genuinely new; for HARD go
  L1/L3/L4. The domain-port lane below is **CLOSED** — porting a proven invariant
  into an 11th skin adds a near-duplicate, not a task.
- **Anti-anchoring naming rule (mandatory, applies to EVERY lever):** name the task
  after the DOMAIN PROBLEM (what a real team's ticket would say), never after the
  lever mechanism. There is NO fixed banned-word list — the test is RELATIVE to the
  current portfolio: before claiming, grep `mined-candidates/index.jsonl` + the
  gallery snapshot for the slug's final noun and its overall shape; if a similar
  name already appears ≥2 times, pick a different name AND a different domain skin.
  Two questions catch most collisions: (a) does the slug describe the
  pattern/mechanism rather than the domain (whatever the currently over-used word
  is — at the time of writing it happened to be `-ledger`)? (b) would a reviewer
  scanning the task list see a family resemblance with existing names? Vary the
  name grammar across a batch too (not every slug needs the same noun-noun-noun
  shape). The built-instance names in this file are a DO-NOT-REUSE list, not
  templates.
- **intent:** a Lane-A MEDIUM task with an **INFINITE resource pool** — no shared
  suite/spec to collide on, so no claim contention. Hardness comes from designing a
  non-obvious invariant over interval/continuous-time state, not from knowing a spec.
- **mechanism:** invent a small business domain whose state is a set of time- or
  interval-scoped facts; require a query/aggregation whose correct answer hinges on
  interval-arithmetic invariants — overlap resolution, half-open boundaries,
  retroactive amendments/reversals, tie-breaking, zero-length intervals. Verifier =
  **boundary-biased differential** against an oracle port over generated scenarios
  (adjacent endpoints, touching intervals, reversal-of-reversal), never a small curated
  test list. ~~Domain-port lane~~ (CLOSED — see STATUS: re-skinning the same logic
  now produces near-duplicates; every new L2 must bring a NEW invariant family).
  Built instances (DO-NOT-REUSE skins): leader-lease-ledger, duty-cycle-ledger,
  interval-arith-evaluator, plus the 8 `-ledger` tasks listed in STATUS.
- **necessary:** the invariant is non-obvious once the symptom is named (probe it);
  the instruction states ONLY the business contract, never the algorithm; the
  differential generator is boundary-biased.
- **disqualifiers (each observed TRIVIAL/EASY):** the instruction narrates the
  algorithm or a placeholder comment lists the todo (over-specified batches 2026-06-30
  / 07-01); a tiny curated verifier with no differential; an invariant that collapses
  to a textbook sort+sweep; **ambiguity-only difficulty** — if disclosing every
  contract ambiguity fully-fairs the task to 3/3 (settlement-ledger), there was no
  independent trap; require ≥1 discriminating boundary family that survives full
  disclosure.
- **fairness_gate:** after all ambiguities are disclosed, at least one boundary family
  still fails ~half of blind runs.
- **resource_slot:** `<domain skin × invariant family>` — synthetic, generate fresh.
- **dedupe_cell / dedupe_key:** `invariant_family × gallery_category` (ports of the
  same invariant into different domains are fine across categories, not within one).

## L3 — `differential-vs-in-env-authority`

- **intent:** fair-by-construction HARD where the reference is reachable **on
  purpose** — hardness is an engineering constraint, not hidden knowledge, so there is
  no disclose-vs-collapse trap at all.
- **mechanism:** require an implementation under a structural/algorithmic constraint
  (e.g. a Brzozowski-derivative regex engine) in a task language that LACKS the
  authority; ground truth = an authority the pytest VERIFIER calls directly
  (`re.fullmatch` itself) over a large differential corpus. The lever is an algorithmic
  trap inside the constraint — e.g. nullable-loop termination for `(a*)*`-shaped
  patterns. Built instance: tbrain-regex-derivative-matcher (oracle 1.0 / nop 0.0,
  7500 differential pairs).
- **necessary:** the task language must not ship the authority (implement in Rust/Go/C,
  authority lives verifier-side in Python); the constraint must be behaviorally
  enforced (its violation shows up as wrong output/hang, not as a white-box source
  check); the generator MUST cap inputs (nesting depth, bounded-only atoms, short
  texts) — otherwise the authority itself backtracks catastrophically and hangs the
  verifier.
- **disqualifiers:** a constraint agents can ignore while still matching the authority;
  an authority whose behavior the model has memorized end-to-end on the capped domain.
- **fairness_gate:** blind runs must fail on the algorithmic trap (wrong/hang on the
  trap family), not on corpus breadth.
- **dedupe_key:** `authority + constraint`.

## L4 — `multi-vector-security-hardening`

- **intent:** historical confirmed-HARD security task (0/3 blind Opus — mathjs
  #3656). Category `security` reopened on Jul 30, 2026; the pattern remains a
  historical difficulty/design record and may be mined only when it is fresh,
  novel, fair, and structurally distinct under the current gates.
- **mechanism:** take a sandbox/escaping/auth surface with N exploit vectors of graded
  subtlety; the instruction states the security objective + every legitimate behavior
  to preserve (this satisfies behavior_in_task_description symmetry and is
  difficulty-safe — hardness lives in the implementation, not the prompt); verifier =
  public behavioral tests: each exploit input must fail, each legit use must keep
  working.
- **necessary:** EVERY vector test must DISCRIMINATE — stock code fails it, patched
  passes. Docker-probe stock-vs-patched before adopting any reviewer-suggested vector:
  many are pre-blocked (= security theater duds that pass on both). Safe generic wins:
  `assert threw` and a broadened leak signal.
- **disqualifiers:** single-vector or vague "harden this" tasks; vectors needing
  network/live targets; a fix that is one obvious guard (fix-shape filter still
  applies).
- **fairness_gate:** blind failures must be MISSED-VECTOR failures, not
  cannot-reproduce/tooling failures.
- **dedupe_key:** `surface + vector_set`.

---

*Add new levers below as new `L#` sections using the same field template. When a lever's
resource universe is small (like L1), always maintain its claimed-resource ledger so the
team dedups on the RESOURCE, not just the task slug. This file + the procedure above are
the single source of truth — no personal/team memory should be required to follow them.*
