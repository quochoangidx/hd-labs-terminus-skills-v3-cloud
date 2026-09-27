# Contract review r1: tbrain-mobile-data-overage-billing

Scope: I read only the contract packet (instruction.md and environment/).

## Verdict
No BLOCKING divergence found. Every figure is either governed by MD-2 or settled by the instruction's "keeps working the figure out the way it does today" and "Add no exception, clamp or guard" sentences. There is 1 SHOULD-FIX and there are 3 POLISH items.

## Governed figures
- `used` = sum over sessions of ceil(kB/1024) (2.1). Empty sessions give 0.
- `allowance`: BASIC 2048, PLUS 10240 (2.2).
- `over` for a line whose usage is more than its allowance = used - allowance (2.3).
- `charge` for a line over its allowance = rate*min(over,1024) + max(over-1024,0) (3.1).
- `total` = sum of the line charges (3.2).

## Silent figures and their kept values
| Figure | Kept value today | Uniquely derivable? |
|---|---|---|
| FLEX allowance | 5120 (`ALLOWANCE_MB`, a constant) | Yes |
| `over` for a line not over its allowance (used <= allowance) | used - allowance, which is zero or negative (no clamp) | Yes. 2.3 gives the same expression. |
| `charge` for a line not over its allowance | over * rate, which is zero or negative | Yes. The tiered formula above also gives over*rate when over <= 0, so a natural rewrite agrees. |
| `account` echo, line order | as given | Yes |

## Findings
### SHOULD-FIX 1: negative over and charge for under-allowance lines are counter-intuitive
Some readers take 2.3 ("A line whose usage is more than its allowance ... Its overage is ...") together with the common-sense idea of billing and conclude that a line under its allowance has overage 0 and charge 0.

Counterexample: a BASIC line with sessions [204800] at rate 9.
- Instruction-faithful output: used 200, over -1848, charge -16632.
- Clamping reader: over 0, charge 0.

The instruction's "Add no exception, clamp or guard" and "keeps working the figure out the way it does today" settle this, so it is not BLOCKING. Solvers will still often get it wrong, and a grader could see that as a trap.

Minimal fix (pick one): add one sentence to the instruction, e.g. "a figure the tariff leaves open keeps today's value even when it is zero or negative". Otherwise accept this as the intended difficulty and make sure the tests cover it explicitly.

### POLISH 1: the FLEX allowance is inferable only from code
MD-2 2.2 says "Every line has an allowance" but names only BASIC and PLUS. The kept value 5120 is unique, so there is no divergence.

### POLISH 2: the charge boundary at 1,024 MB
"first 1,024 megabytes ... after those" is unambiguous: over=1024 gives 1024*rate, and over=1025 gives 1024*rate+1. No action needed. Tests should include both.

### POLISH 3: output format
The driver is frozen and uses `json.dump` with default separators, and keys are compared as parsed JSON. No gap. The input limits (1.2) are closed: a session is at least 1 kB, so there is no zero-kB rounding question. Ids and plans are closed sets, and duplicates are open.

Checked and not divergent: order of operations (only integer ceil per session, then sums, so there is no float or rounding choice); "exactly on" the allowance (0 under both readings); the rate=1 tier (the same either way).

## Witness lines
| # | Case | plan | sessions (kB) | rate | used | allowance | over | charge |
|---|---|---|---|---|---|---|---|---|
| 1 | BASIC far over | BASIC | [2000000, 2000000, 2000000] (1954 MB each) | 9 | 5862 | 2048 | 3814 | 1024*9 + 2790 = 12006 |
| 2 | PLUS (example) | PLUS | 5 x 2097152 + [1024000] | 4 | 11240 | 10240 | 1000 | 4000 |
| 3 | FLEX | FLEX | [2000000, 2000000, 2000000, 1] | 7 | 5863 | 5120 | 743 | 5201 |
| 4 | no sessions | BASIC | [] | 9 | 0 | 2048 | -2048 | -18432 |
| 5 | inside allowance | BASIC | [204800] | 9 | 200 | 2048 | -1848 | -16632 |
| 6 | exactly 1024 over | BASIC | [3145728] | 5 | 3072 | 2048 | 1024 | 5120 |

Extra: line 6 with one more 1-kB session gives used 3073, over 1025, charge 5121.

The example file's first line ([1048576, 1572864, 500], rate 9) gives used 2561, allowance 2048, over 513, charge 4617. The example total is 4617 + 4000 - 16632 = -8015.
