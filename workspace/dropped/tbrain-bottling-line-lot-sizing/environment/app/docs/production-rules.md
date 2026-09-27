# Production planning rules

These rules decide whether a site's production plan can be run and what it
costs. They are the rules `tools/check_plan.py` applies.

## The site

Each site file in `sites/` (every file there except `targets.json`) is one
bottling site over `days` days, numbered from 0. All numbers are whole numbers.

A line has an `id` and `capacity_minutes`: a list with one entry per day, the
minutes the line can run that day (0 when it is down).

A product has an `id`, a `family` (for information only; it plays no part in
the rules), `initial_stock` (batches on hand before day 0), `holding_cost` and
`backlog_cost` (per batch per day, see below), `demand` (a list with one entry
per day: the batches shipped to customers that day) and `lines`, which maps
each line that can fill the product to three numbers:

- `minutes_per_batch`: line minutes to fill one batch;
- `setup_minutes`: line minutes to change the line over to this product;
- `setup_cost`: the cost of that changeover.

## What a plan must do

A plan is a list of runs. A run fills a whole number of batches of one product
on one line on one day. Then:

1. Every run names a known day, line and product, the product lists that line
   in its `lines`, and the run fills at least one batch.
2. No two runs have the same day, line and product.
3. On each day, for each line, the runs on it take no more than that day's
   `capacity_minutes`. A run takes `setup_minutes` plus `batches` times
   `minutes_per_batch` (the numbers for that product on that line). Every run
   pays its own setup, whatever ran before it; the order of runs within a day
   does not matter.

A plan may leave any demand unfilled; that is costed, not forbidden.

## Stock and cost

For each product, the stock at the end of day `d` is the stock at the end of
day `d - 1` (the `initial_stock` for day 0), plus the batches filled on day `d`
on every line, minus `demand[d]`. Batches filled on a day can ship that same
day. Stock may go below zero: a negative stock is batches owed to customers
(backlog), and later production pays it back first.

A plan costs the sum of:

- `setup_cost` for every run;
- for every product and every day, `holding_cost` times the stock at the end of
  that day when it is above zero, or `backlog_cost` times minus that stock when
  it is below zero.

Nothing else is charged. Costs are whole numbers, and lower is better.

## File format

    {"runs": [{"day": 0, "line": "L1", "product": "COL01", "batches": 12}, ...]}

The file is one JSON object whose `runs` value is a list. Each run is an object
with `day`, `line`, `product` and `batches`: `day` and `batches` are whole
numbers (JSON integers, not strings, floats or booleans), `line` and `product`
are strings. Runs may appear in any order. Any other key, at the top level or
inside a run, is ignored.

The file must be standard JSON in UTF-8 (so no byte-order mark, no `NaN` and no
`Infinity`). It may be at most 2,000,000 bytes long, and no number in it may be
written with more than 4300 digits (counting every digit, including those after
a decimal point or in an exponent). No object in it may give the same name
twice, and objects and arrays may nest at most 64 levels deep, counting the
top-level object as the first level.
