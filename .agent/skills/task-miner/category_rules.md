# Category Rules — real-CI-calibrated, rules-first category prediction

All nine Regular-task categories reopened for net-new submissions on Jul 30,
2026, and the platform loosened the `category_classifier` check. The declared
category must still match the primary activity. The classifier remains
unavailable locally from VN, and blind fresh-subagent votes have been
miscalibrated against historical real-CI verdicts in both directions (see the
labeled dataset below). Therefore:

**Protocol — rules first, probe only as fallback:**

1. Run the rules below against the task's classifier-visible shape
   (instruction verbs, I/O surface, rubric wording, repo furniture). They are
   deterministic and free.
2. A fired prediction rule is authoritative evidence for the corresponding
   category. If it conflicts with the declared label, relabel or reshape based
   on the genuine primary activity; do not drop merely because that category
   was blocked historically.
3. A fired rule matching the declared category needs at most one confirmatory
   probe run. A probe disagreeing with a strong real-CI-calibrated rule is a
   review signal, not an automatic blocker.
4. **No rule fires** → fall back to the blind category probe: 2 runs, add a
   3rd ONLY on a 1–1 split (user-set probe default), per `task-clone`
   Quality Preflight.
5. When multiple category rules fire, choose the category describing the
   dominant work surface and document the tie-break evidence. Exact-reference
   conformance (R1) normally predicts software-engineering regardless of a
   game, ML, or ops-themed narrative.
6. Every new real-CI or reviewer category verdict gets appended to the dataset
   below, and any rule it contradicts gets amended immediately (AGENTS.md
   self-update rule).

For every shortlisted task, persist the decision as
`workspace/reports/<slug>/category-screen.json` with `status`, `task_slug`,
`declared_category`, `predicted_category`, `rules_fired`, and classifier-visible
`evidence`. When `rules_fired` is empty, include a passing `fallback_probe`
record. A prose conclusion or declared `task.toml` label is not gate evidence;
`scripts/batch-handover.py` rejects missing or malformed records.

## Primary category-prediction rules

- **R1 — exact-reference-conformance ⇒ software-engineering, theme
  irrelevant.** The instruction's core ask is "reproduce / match / detect
  exactly as tool-or-library X's output" (or the corpus is visibly a named
  implementation's vectors). Security/WAF/email theme does not move it:
  libinjection SWE 0.92, DKIM SWE 0.9+, p0f SYN fingerprint SWE 0.92, all
  after security framing or blind probes said security.
- **R2 — dataset→report ⇒ data-processing (or DP/ML split).** Records,
  qrels, logs, or a dataset in; an aggregated report/metric table out. Eval/IR
  framing is thin cover (trec_eval split DP 0.55 / ML 0.55, SWE second). ML
  calibration tasks can still fire this rule when the visible surface is a
  generic `data/` archive plus batch JSONL routing/prediction output
  (rail-switch-icing-route: DP 0.85).
- **R3 — repair shape ⇒ debugging.** Find-the-bug, make-the-failing-test-pass,
  "the tool misbehaves — fix it" framing.
- **R4 — stub-fill compute-to-spec ⇒ software-engineering.** Dominant verbs
  implement/parse/render/normalize/cmp/"extend the starter" over a provided
  stub; exact-spec transformation of text/URIs/JSON (idna, referrer,
  license-classify 0.72/0.70 despite compliance framing). ML-themed Python
  package work can still fire this rule when the visible ask says "Add/Make"
  fit/predict commands, and ops-themed Python package work can still fire it
  when the visible ask says to "implement" a `plan` command; the subject does
  not rescue a command-stub shape.
- **R5 — manifests/lockfiles as the OBJECT ⇒
  build-and-dependency-management.** Package
  coordinates, dependency graphs, version constraints, and build outputs are
  what the agent manipulates; verbs resolve/install/build/package. The old purl
  CI result remains classification evidence.
- **R6 — policy-verdict framing ⇒ security.** This
  applies only when no named reference tool anchors the ask (else R1):
  allow/deny/authorize, CORS, open-redirect, firewall, and token-scope work all
  classify as security.
- **R7 — continuous model + precision contract ⇒ scientific-computing.**
  Physical units, numerical tolerances, and a
  continuous-time/space model pull this category even when no method is
  prescribed.

## Direct-match category rules

- **R8 — game rules as the object ⇒ games.** Simulate/adjudicate/move-legality/
  scoring over deterministic state transitions.
- **R9 — ML activity, not ML subject ⇒ machine-learning.** Loader/eval-loop/
  training/tokenizer work with seeds and fixtures. An ML-themed algorithm
  implemented to spec is R4 (route-state-decode, sacrebleu: scrub ML tags).
  For calibration tasks, surface the primary activity as supervised fitting
  from a labeled calibration archive to a model artifact, not as repairing a
  Python package or transforming generic data rows to an output file.
- **R10 — operate an environment ⇒ system-administration.** Service health,
  configuration, permissions, users, processes, logs, or state restoration are
  the object of the task; the agent operates a system rather than implementing
  an algorithm or a build/dependency resolver.

## ⚠️ Historical enforcement caveat

Enforcement is date-gated (data-processing block 2026-07-10+,
`template_detection` 2026-07-13+, originality flags 2026-07-19, and
build-and-dependency-management/security/scientific-computing blocks
2026-07-24+). All nine categories reopened on Jul 30 and the classifier was
loosened. Historical blocked verdicts still show how the classifier mapped
task shapes at the time, but they no longer make a category unavailable. The
91-task
platform-passed portfolio (`.agent/mined-candidates/platform-passed-portfolio.md`)
contains many parse/normalize shapes (whatwg-url, html5-tokenizer,
css-syntax-tokenize, 8 URL-canonicalize reskins) that passed BEFORE
enforcement — they remain useful novelty and classification evidence, not
proof of current difficulty or originality. New real-CI verdicts should be
recorded with their policy date because classifier behavior may have changed.

## Labeled dataset (task, blind-probe prediction, real verdict)

| Task | Blind probe said | Real CI / reviewer said | Rule |
|---|---|---|---|
| tbrain-libinjection-detect-verdict | security (2×) | SWE 0.92 blocked | R1 |
| DKIM canonicalization series | security (2×) | SWE 0.9+ blocked | R1 |
| tbrain-p0f-syn-fingerprint | — | SWE 0.92 blocked under p0f-reference framing | R1 |
| purl canon series | SWE 0.9 | build-and-dependency-management 1.0 (historical block; reopened Jul 30) | R5 |
| tbrain-trec-eval-score | DP 0.55 / ML 0.55 | dataset→report blocked archetype | R2 |
| license-classify | SWE 0.72/0.70 | blocked (classify shape) | R4 |
| tbrain-satellite-wheel-safe-mode | — | SWE 0.9 blocked under "Add/Make Python package fit/predict" framing; ML calibration reframe pending real-CI rerun | R4/R9 |
| tbrain-rail-switch-icing-route | — | DP 0.85 blocked under generic `/app/data` archive + route JSONL output; supervised calibration `/app/calibration` + `predict` reframe pending real-CI rerun | R2/R9 |
| tbrain-maintenance-window-evacuation | — | SWE 0.9 blocked under both "Python package... Implement `plan`" ops framing and light ML label-prediction `plan` reframe; full fit/model-artifact reframe pending real-CI rerun | R4/R9 |
| tbrain-orbit-contact-window | — | SWE while instruction prescribed method; sci-comp after reframe (historical; now blocked) | R7 |
| SPF / cors / open-redirect / firewall / token-scope | security (2× each) | historical security passes; category reopened Jul 30 | R6 |
| pager-line-break / console-wrap-break / route-state-decode-go | — | historical scientific-computing passes; category reopened Jul 30 | R7 |
| quartz-cron | — | category-dead shape; honest reshape probed 3/3 EASY → drop | R4 |
| repair-shape fresh-5 batch | — | debugging-category + EASY | R3 |

Keep this table current: it is the calibration set that makes the rules
authoritative. If a future real-CI verdict contradicts a rule, the rule — not
the verdict — is what changes.
