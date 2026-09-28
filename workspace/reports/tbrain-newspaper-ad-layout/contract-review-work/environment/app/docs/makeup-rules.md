# Ad make-up rules

These rules decide whether an edition's ad layout can go to press and what it
costs. They are the rules `tools/check_layout.py` applies.

## The edition

Each file in `editions/` is one edition. It has `pages` pages, numbered from 1.
Every page is a grid of `columns` columns (numbered from 0, left to right) and
`rows` rows (numbered from 0 at the top; row `rows - 1` is the foot of the page).
Odd-numbered pages are right-hand pages. Page 1 stands alone; otherwise pages
`2k` and `2k + 1` face each other as one spread (so 2 faces 3, 4 faces 5, and
an even last page faces nothing).

`sections` gives, for each section name, its first and last page (inclusive).

An ad has an `id`, a `width` in columns and a `depth` in rows, a `rate` (what
the paper earns when it runs), `booked` (true when it has to run in this
edition), a `section` it asked for (or `null`), `right_hand` (true when it asked
for a right-hand page) and a `competitor_group` (or `null`). `advertiser` is for
the desk's information and plays no part in the rules.

The edition also gives `front_page_ad_rows`, `max_ad_share_percent`,
`wrong_section_percent` and `left_hand_percent`.

## What a layout must do

A layout places some of the ads. Each placed ad sits on one page, with its top
left cell at a `column` and `row`, and covers `width` columns and `depth` rows
from there. Then:

1. Every placed ad lies inside its page, and no two ads on a page share a cell.
2. Every placed ad rests on the foot of the page or on ads: either its bottom row
   is the page's last row, or every cell directly below its bottom row, across
   its whole width, is covered by some ad.
3. On page 1, ads cover only the bottom `front_page_ad_rows` rows, so at most
   `front_page_ad_rows * columns` cells. On every other page, ads cover at most
   `max_ad_share_percent * rows * columns // 100` cells (whole-number division).
4. Two ads of the same `competitor_group` are never on the same page or on the
   two pages of one spread.
5. Every `booked` ad is placed. Other ads may be left out.

## Cost

A layout costs the sum of:

- the `rate` of every ad left out;
- for every placed ad that asked for a section and is on a page outside it,
  `rate * wrong_section_percent // 100`;
- for every placed ad that asked for a right-hand page and is on an even page,
  `rate * left_hand_percent // 100`.

(`//` is whole-number division, rounding down, taken separately for each ad.)
Both of the last two can apply to the same ad. Costs are whole numbers, and
lower is better.

## File format

    {"placements": {"AD001": {"page": 3, "column": 0, "row": 21}, ...}}

Each key is the id of a placed ad, given once; `page`, `column` and `row` are
whole numbers (JSON integers, not strings or booleans). Ads not listed are left
out. Unknown ad ids are an error. Any other top-level key is ignored.
