# Lever Pattern Catalog — shared, in-repo, read before mining a HARD task

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

- **intent:** a from-scratch implementation task that a strong agent solves only 0–1/3,
  because independent *full* implementations each miss a DIFFERENT slice of the spec's
  long tail.
- **mechanism:** ship a stub + a pointer to the spec; bake the OFFICIAL
  machine-checkable suite HIDDEN under `tests/`; oracle passes 100%, nop fails on the
  divergent tail. (Answer table in `environment/repo` makes it trivial — see task-clone.)
- **necessary (ALL must hold):**
  - an official, machine-checkable suite exists over the spec;
  - the spec has a genuinely divergent / irregular long tail;
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
  - a clean matching engine (git-pathspec shape).
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
| html5lib tree-construction       | WHATWG HTML §13   | Rust       | this-workspace | built | near-neighbor of the URL task (same Rust × Data-Processing × WHATWG cell) |
| html5lib tokenizer               | WHATWG HTML §13   | (team)     | team         | built  | |
| Unicode SENTENCE-break (UAX-29)  | UAX-29 sentence   | (team)     | team         | built  | |
| JSON-Schema-2020-12 suite        | draft 2020-12     | (team)     | team         | built  | unevaluated* + $dynamicRef tail |
| chess perft node-count vectors   | FIDE legal movegen| C++        | this-workspace | REJECTED | **too easy — blind Opus 3/3 (58/58).** Perft node counts are FAMOUS/memorized numbers, so a one-shot solver self-verifies against them and reliably produces a correct legal generator. LESSON: a resource whose reference vectors the solver has MEMORIZED (or can look up) defeats L1 — the solver self-verifies. Pick specs whose (input→output) vectors are NOT memorizable (Unicode sort keys, URL parses), not famous constants. |
| Unicode CollationTest (UCA)      | UTS-10 + DUCET    | C++        | this-workspace | claimed | replaces chess; variable-weighting SHIFTED/NON_IGNORABLE + contractions + implicit weights tail; sort keys are NOT memorizable → solver cannot self-verify |
| css-tokenizer-tests (romainmenke)| CSS Syntax L3     | Go         | this-workspace | claimed | escapes/number/url-token/bad-string recovery tail; no stdlib CSS tokenizer in Python |
| RFC 5545 RRULE vectors           | RFC 5545 RRULE    | Rust       | this-workspace | claimed | BYSETPOS/BYDAY-in-monthly/negative BYMONTHDAY/WKST tail; dateutil not in stdlib |

### Fresh-resource ideas for L1 (unclaimed — verify `necessary`/`disqualifiers` first)

These are pointers, not endorsements — probe each ≥3× blind before trusting the difficulty:
UAX-31 identifier syntax, UTS-51 emoji ZWJ sequences, RFC 3986 URI reference resolution
(distinct from WHATWG-URL), RFC 5322 address parsing, RFC 8259 vs JSON5, ICU/CLDR plural
rules, WHATWG Encoding (single-byte + multibyte index tables), CSS Syntax Level 3
tokenizer (csswg test suite), IRI/IDNA round-trips. Pick one NOT in the ledger, in a
language NOT already paired with it, and confirm independent impls diverge on the tail.

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
5. **Build.** Ship a stub (reads input, emits nothing/minimal). Put the official suite
   HIDDEN under `tests/`; oracle = a full correct impl that passes 100%; nop/stub fails.
   NEVER commit the answer table (input→expected) into `environment/repo` — grep for it
   before shipping (see task-clone). Read binary suite files (`.dat`, `LineBreakTest`) in
   BINARY mode; a stray `\r` silently corrupts cases.
6. **Probe difficulty AND fairness — do BOTH before trusting the task:**
   - Run ≥3 BLIND solvers (fresh agent, no `solution/`, no `tests/`). HARD ≈ 0–1/3 solve.
   - Do NOT let a solver paste the spec source (blows up context, distorts the probe).
   - Sanity gate: oracle must PASS and nop/stub must FAIL, or the harness is broken —
     that is not a difficulty signal (see the missing-tmux / verifier-did-not-run traps).
7. **Fairness audit — a green `✅ HARD` verdict is NECESSARY-NOT-SUFFICIENT; read the
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
8. **instruction_check pre-flight.** Write the instruction as PROSE: objective + I/O
   protocol + the authoritative spec/suite reference. No `##` headers, no lookup tables,
   no algorithm narration, no "pay attention" hints — those trip the checker.
9. Ship.

---

*Add new levers below as new `L#` sections using the same field template. When a lever's
resource universe is small (like L1), always maintain its claimed-resource ledger so the
team dedups on the RESOURCE, not just the task slug. This file + the procedure above are
the single source of truth — no personal/team memory should be required to follow them.*
