# Platform-passed portfolio (user-provided 2026-07-19)

91 tasks confirmed PASSED on the platform. Two hard caveats before using this
list for anything:

- **Passed ≠ replicable today.** Enforcement is date-gated: the
  data-processing category block (2026-07-10+), `template_detection`
  (2026-07-13+), and originality/anti-port flags (2026-07-19) all postdate
  most of these submissions. Many normalize/parse shapes below (whatwg-url,
  html5-tokenizer, css-syntax, the URL-canonicalize reskins) would fire
  category BLOCK rules or template/originality checks if submitted now.
  This list is a dedupe/saturation ledger, NOT a license to rebuild the shapes.
- **Passed ≠ hard.** Non-Python MEDIUM is platform-OK; known-MEDIUM engines
  (robotstxt, toml, mustache, bc-calculator) are in the list.

## Saturated port families (≥5 variants shipped = engine CLOSED, fresh-only doctrine)

| Family / engine | Count | Members |
|---|---|---|
| UAX-14 line break / wrap | 10 | uax14-linebreak, pager-line-break, console-wrap-break, typeset-line-break, ereader-pagination-break, terminal-reflow-break, editor-soft-wrap, label-wrap-break, caption-wrap-break, email-quote-wrap |
| UAX-29 sentence segmentation | 8 | uax29-sentence-break, prose-sentence-segment, subtitle-cue-split, tts-sentence-chunk, transcript-sentence-split, comment-sentence-segment, corpus-sentence-boundary, chatlog-sentence-split |
| WHATWG URL canonicalize | 8 | whatwg-url-parser, address-url-canonicalize, bookmark-url-canonicalize, share-url-normalize, feed-url-canonicalize, canonical-link-build, referer-url-normalize, cdn-url-canonicalize |
| Version constraint/admission | 8 | composer-version-constraint, conan-version-ranges, pep440-specifier-match, conda-match-spec, index-version-filter, artifact-version-admit, ci-dependency-gate, deploy-version-pick |
| Viterbi constrained decode | 7 | viterbi-constrained-decode, keystroke-path-decode-java, symbol-stream-decode-ts, phoneme-path-decode-ruby, txn-state-decode-php, npc-intent-decode-lua, route-state-decode-go |
| RFC 6570 URI template | 6 | uri-template-expand, webhook-url-template-ts, link-template-expand-c, service-uri-template-cpp, request-uri-template-php, api-route-template-rust |
| LOWESS smoothing | 5 | lowess-smooth, telemetry-scatter-smooth, airquality-trend-smooth, tick-price-smooth, conversion-trend-smooth |

53 of the 91 passes come from these 7 engines — the accepted portfolio's
volume was port-series volume, which the fresh-only doctrine has since closed
(alongside DKIM at 8, dropped). Every family above is originality-saturated:
reject any new variant at dedupe, regardless of language or reskin domain.

## Sub-threshold families (<5 — still count members before any user-requested port)

- CSS engines (4, distinct engines): css-selector-match, css-syntax-tokenize,
  css-color4-parse, css-component-value-parse
- Postgres value parsers (3): pg-hstore-parse, pg-tsquery-parse,
  pg-interval-parse
- Grapheme/display width (2): grapheme-display-width,
  boardingpass-columns-kotlin

## Singles

jsonpath-rfc9535, idna-uts46, json-schema-validate, html5-tokenizer,
toml-decode, mustache-render, xml-wellformed, email-address-syntax,
commonmark-render, yaml-load, bc-calculator, robotstxt-match, gherkin-ast,
uca-collation-key, bcp47-canonicalize, urlpattern-match, kdl-document-parse,
spf-record-eval, dockerfile-parse, hocon-config-resolve, jmespath-query,
xpath1-eval, nginx-config-parse, hcl2-config-parse, cpp-macro-expand,
tagpath-decode-cpp, jq-filter, utm-mgrs-convert, purl-canonicalize,
rank-nonparametric-test

## Category-calibration signal (feeds task-miner/category_rules.md)

- spf-record-eval passed → supports R6 (policy-verdict-without-named-tool →
  security).
- pager-line-break, console-wrap-break, route-state-decode-go passed AFTER
  explicit sci-computing reshapes → supports R7 (continuous model, no method
  steps).
- The many parse/normalize passes (whatwg-url, html5-tokenizer,
  css-syntax-tokenize, URL-canonicalize reskins) are GRANDFATHERED, not
  counter-evidence to BLOCK rules R1/R4 — see the date-gating caveat above.
