# Final review: tbrain-newspaper-ad-layout

Scope: the frozen snapshot in `final-review-work/` (instruction.md, task.toml, environment/, tests/, solution/, prior/). I did not edit any task file. Running the checker locally created `tests/__pycache__`, which I deleted, so the tree is back to its original 31 files.

## What I checked

- **Earlier findings.** All three are resolved as the adjudication says:
  - makeup-rules.md no longer says "given once". The loader now rejects a name repeated in any object (`tests/check_layout.py:23-29`), so duplicate ids fail.
  - makeup-rules.md:63-64 now says "Any other key, at the top level or inside a placement, is ignored", which matches the checker.
  - instruction.md:1 now describes the planner correctly: booked ads first, then by rate, own section's pages first. That matches `plan_edition.py:25-32`.
- **Grader copy vs agent copy.**
  - `tests/check_layout.py` and `environment/app/tools/check_layout.py` are identical (`diff` shows nothing).
  - The four edition files match byte for byte (`cmp`), and so do the two `targets.json` files.
  - This task has no split inputs, roster or checksums. The grader's editions are whole files identical to the agent's, so the reassembly question does not apply. The only "roster" mention is in prior/adversarial-adjudication.md:3, about a different task.
- **Reference.** Checker results for the four reference layouts: mon 4635, wed 6701, fri 7500, sat 10601. Each is valid and exactly equal to its target in both targets files.
  - Running `pytest tests/test_outputs.py` with `AD_LAYOUTS=solution/layouts` gives 8 passed.
- **Shipped planner.** Its layouts are valid and cost 7114 / 9167 / 10544 / 13571, which is 28-54% over target. That matches task.toml.
  - It leaves out 14/20/24/31 ads and puts 7/14/21/17 ads in the wrong section, which supports the claim in instruction.md.
  - Grader result on the planner layouts: 4 validity tests pass and 4 target tests fail.
- **Edition shape.** The editions have 58-138 ads and 16-32 pages on a 6x42 grid, with 60% page share, a 6-row front strip, 30% wrong-section and 15% left-hand penalties. This matches difficulty_explanation.
- **Rules document vs checker.** Every rule matches, boundaries included:
  - rule 1 (bounds and overlap) at :75-81
  - rule 2 (full-width support) at :84-90
  - rule 3 (front strip, and area as `pct*rows*cols//100`) at :92-99
  - rule 4 (spreads: page 1 alone, then `p//2`) at :101-114
  - rule 5 (booked ads placed) at :116-118
  - cost with per-ad floor division at :120-134
  - file format: `> 2,000,000` bytes rejected, so exactly 2,000,000 is accepted, as "at most" says. NaN and Infinity are rejected. Repeated names are rejected. The depth limit counts the top level as 1. `type(...) is int` excludes booleans and floats. Unknown ids are an error, and extra keys are ignored.
- **Probes I ran against the grader's checker on the mon reference.**
  - Rejected, as they should be: a booked ad removed; the same id twice; `row` repeated inside a placement; `row` as a float; `page` as `true`; an unknown id; page 99; NaN; 65-level nesting; 100000-level nesting (a RecursionError, which the checker catches); a file one byte over 2,000,000; a top-level array; a UTF-8 BOM.
  - Accepted, as they should be: 64-level nesting in an extra key; a file of exactly 2,000,000 bytes; items in reverse order plus extra top-level keys (cost 4635).
  - Scored above target, so the target test fails: the reference with one optional ad dropped (cost 4739).
  - A missing `sat.json` fails both sat tests.
- **Isolation and determinism.**
  - The verifier runs in `environment_mode = "separate"` and uses only `/tests` copies of the checker, editions and targets. It reads layouts as data, so no code from `/app` runs.
  - It uses `python3 -I` and a mktemp working directory.
  - Nothing depends on time, randomness, the network or test order. Each test calls `_cost` itself.
  - Editing the checker, inputs or targets under `/app` cannot change the grade.

## Findings

1. **Advisory: a number longer than 4300 digits crashes the loader instead of giving a LayoutError.**
   - Citation: `tests/check_layout.py:48-53` (same code in `environment/app/tools/check_layout.py:48-53`) and `environment/app/docs/makeup-rules.md:63-66`.
   - Python 3.13 raises a plain `ValueError` ("Exceeds the limit (4300 digits)"). That is not a `JSONDecodeError`, so it is not caught.
   - A file with a 5000-digit integer in an ignored extra key is standard JSON under the 2 MB limit, and the rules say it should be accepted. Instead the checker crashes, and the grader turns that into a failed test.
   - When the long number is in `page`, the file is rejected, which is correct, but with a traceback rather than a rules message.
   - No real solver would do this, and it cannot cause a false pass.
   - Smallest fix: add `ValueError` to the `except` on line 50 of both copies. Also add one clause to the rules, such as "numbers may have at most 4300 digits", or treat such a file as not valid JSON.

2. **Advisory: the rules never say outright that a layout must be an object with a `"placements"` object.**
   - Citation: `environment/app/docs/makeup-rules.md:57-64` vs `tests/check_layout.py:60-61`.
   - The requirement is implied only by the example. A top-level array, or an object without `placements`, is rejected.
   - Smallest fix: add "The file is one object whose `placements` value is an object" before "Each key is the id of a placed ad".

3. **Advisory: the wed and sat targets were raised after the contract review, and no adjudication records it.**
   - Citation: `prior/contract_review.md:54` gives the targets as 4776 / 6500 / 7500 / 9800. `tests/targets.json:2-5` now has 4635 / 6701 / 7500 / 10601.
   - The planner costs are unchanged (7114 / 9167 / 10544 / 13571), which suggests the editions did not change. The current snapshot agrees with itself: the reference sits exactly on the targets.
   - But "the cost of the best layout the desk has found" (instruction.md:1) would normally only go down. A platform reviewer comparing versions may ask why two targets rose.
   - Smallest fix: add one line to the adjudication or build notes explaining the change, for example that the earlier wed and sat values were never reached by a checked layout, or that the editions were regenerated.

4. **Advisory: the adversarial pass predates the loader hardening.**
   - Citation: prior/adversarial-adjudication.md:3.
   - The repeated-name and depth checks were added after the 15+1 adversarial run, so that run did not exercise them.
   - My probes above cover them: repeated names at both levels, the 64/65 depth boundary and very deep nesting all behave as the rules state. No action is needed beyond noting this in the adjudication.

5. **Advisory: I could not confirm the category labels from this snapshot.**
   - Citation: task.toml:8-9 (`category = "Media"`, `subcategory = "Design"`).
   - The newspaper ad make-up domain fits "Media". The work itself is combinatorial optimisation, and "Design" is only a loose fit for it.
   - I could not check either label against the platform's category list from inside this directory. Everything else in the explanation fields matches the files: counts, grid, rules, planner costs, the targets equalling the reference, and the verification method.
   - Smallest fix: confirm that "Media / Design" is on the allowed list. If an optimisation or operations-research subcategory exists under Media, use it instead.

No Blocking or Should-fix issues found. Grading rejects each class of wrong work and accepts valid variants. The reference passes exactly at target. The agent's and grader's inputs are identical, and grading is isolated from `/app`.

## Verdict
accept
