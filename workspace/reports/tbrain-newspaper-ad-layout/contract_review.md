## Findings

1. **Should-fix — Duplicate ad IDs are prohibited by the document but not detected by the checker.**  
   **Citation:** `environment/app/docs/makeup-rules.md:61`; `environment/app/tools/check_layout.py:22`; `environment/app/tools/check_layout.py:99`  
   Python’s JSON parser silently keeps the last occurrence of a duplicate object member. A raw layout containing `AD032` twice was accepted with the same cost as the planner layout, despite the requirement that each ID be “given once.”  
   **Smallest fix:** Load layouts with an `object_pairs_hook` that rejects duplicate keys, or remove the unenforced “given once” requirement and explicitly define duplicate-member behavior.

2. **Advisory — Extra keys inside individual placement objects have unspecified behavior.**  
   **Citation:** `environment/app/docs/makeup-rules.md:61`; `environment/app/docs/makeup-rules.md:63`; `environment/app/tools/check_layout.py:25`  
   The document explicitly says extra top-level keys are ignored, but does not say whether `{"page":3,"column":0,"row":21,"note":"x"}` is valid. The checker accepts and ignores `note`.  
   **Smallest fix:** Add “Other keys inside a placement object are ignored,” or reject them in the checker.

3. **Advisory — The instruction’s description of the shipped planner is imprecise.**  
   **Citation:** `instruction.md:1`; `environment/app/planner/plan_edition.py:25`; `environment/app/planner/plan_edition.py:29`  
   The planner does not simply place the biggest earners on the first available page: booked ads precede all optional ads, and requested-section pages are tried before earlier pages elsewhere. This does not affect grading because the source is visible.  
   **Smallest fix:** Describe it as “booked ads first, then by rate, trying requested-section pages first.”

No discrepancy was found for bounds, overlap, full-width support, front-page restrictions, page limits, competitor spreads, booked ads, omission cost, section and handedness penalties, per-ad floor rounding, unknown IDs, or rejection of floats, strings, booleans, and missing placement fields.

The document also resolves the potentially ambiguous geometry points: rows count from the top, pages 2–3, 4–5, etc. face, and an even final page faces nothing. Because each rectangular ad has one uniform bottom row, it cannot rest partly on the page foot and partly on another ad.

## Witnesses

1. **Unsupported ad:** Monday `AD003` at page 2, column 0, row 35 leaves row 41 empty beneath it. The checker rejected it as not resting across its full width.  
   **Citation:** `environment/app/docs/makeup-rules.md:33`; `environment/app/tools/check_layout.py:40`

2. **Overlap:** Monday `AD003` and `AD011`, both at page 2, column 0, row 36, overlap. The checker rejected them.  
   **Citation:** `environment/app/docs/makeup-rules.md:32`; `environment/app/tools/check_layout.py:33`

3. **Front-page strip:** In the valid planner layout, replacing bottom-strip `AD041` with `AD005` at page 1, column 0, row 21 uses only 21 of the allowed 36 cells but extends above the bottom six rows. The checker rejected it specifically for reaching above the strip.  
   **Citation:** `environment/app/docs/makeup-rules.md:36`; `environment/app/tools/check_layout.py:53`

4. **Front-page area limit:** Adding full-width `AD014` at row 30 directly above full-width `AD041` produces 72 ad cells against a limit of 36. The checker rejected it with that calculation.  
   **Citation:** `environment/app/docs/makeup-rules.md:36`; `environment/app/tools/check_layout.py:48`

5. **Competitor spread:** Monday cars ads `AD001` on page 2 and `AD029` on page 3, both resting on their page feet, were rejected because pages 2 and 3 form one spread.  
   **Citation:** `environment/app/docs/makeup-rules.md:11`; `environment/app/docs/makeup-rules.md:39`; `environment/app/tools/check_layout.py:57`

6. **Boolean field:** Changing a valid placement’s `page` to JSON `true` was rejected; the exact-type check correctly distinguishes booleans from integers.  
   **Citation:** `environment/app/docs/makeup-rules.md:61`; `environment/app/tools/check_layout.py:25`

7. **Unknown ID:** Adding a placement for `NOPE` was rejected as an unknown ad.  
   **Citation:** `environment/app/docs/makeup-rules.md:63`; `environment/app/tools/check_layout.py:23`

8. **Extra keys:** Adding an extra top-level key and an extra key inside a placement left the Monday planner cost unchanged at 7114. The top-level result matches the text; the placement-key behavior is the advisory ambiguity above.  
   **Citation:** `environment/app/docs/makeup-rules.md:63`; `environment/app/tools/check_layout.py:16`

9. **Duplicate ID:** A raw JSON object containing the same valid placement ID twice parsed to one placement and remained valid at cost 7114. This is the sole observed text/tool disagreement.  
   **Citation:** `environment/app/docs/makeup-rules.md:61`; `environment/app/tools/check_layout.py:99`

10. **Cost arithmetic:** The Monday planner layout costs 7114. Removing `AD022` increased cost by its full rate, 1805. Removing `AD033`, placed outside its requested section, increased cost by 504: `720 - (720*30//100)`. Removing right-hand `AD006` from even page 8 increased cost by 154: `181 - (181*15//100)`. These agree with separate per-ad floor rounding. Both penalty checks are independent in the checker.  
    **Citation:** `environment/app/docs/makeup-rules.md:45`; `environment/app/tools/check_layout.py:76`

All four shipped planner outputs are valid under the checker. Their costs are 7114, 9167, 10544, and 13571, respectively, so the planner does not itself meet the published targets of 4776, 6500, 7500, and 9800. This is consistent with the task’s optimization premise. Paths, edition names, graded artifacts, unavailable network/installations, and the available Python standard-library environment are consistent. The visible checker, planner, editions, and targets do not provide an apparent shortcut that would bypass constructing qualifying layouts.

## Verdict

accept with fixes