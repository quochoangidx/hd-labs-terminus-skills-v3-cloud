# SUBMISSION — tbrain-mobile-data-overage-billing

- Task: Repair a mobile carrier's business billing package so the data usage, allowances, overage and charges on its account statements follow the carrier's data usage tariff.
- Category: Operations / Finance
- ZIP: `workspace/submissions/tbrain-mobile-data-overage-billing.zip` (sha256 646c599e28403aa2e2a44c49ce9b79d05eef2454b7045f9b8d14e928dfe239d9)

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent measures each data session on its own in whole megabytes of 1,024 kilobytes, a part megabyte counting as a whole one, and sums the sessions, +2
Agent gives a BASIC line an allowance of 2,048 MB and a PLUS line 10,240 MB, +2
Agent charges a line over its allowance its overage rate for each of the first 1,024 MB of overage and 1 cent for each megabyte after, +2
Agent keeps the statement total as the plain sum of every line's charge, in file order, +1
Agent keeps the package's existing 5,120 MB allowance for a FLEX line, +3
Agent keeps the package's existing overage and charge for a line inside its allowance, its usage less its allowance and that many megabytes at its rate, nought or a credit, +3
Agent leaves /app/tools/usagebill_run.py byte-for-byte as shipped, +1
Agent returns the account name exactly as given in the file, whatever its case, spacing or characters, +1
Agent floors the overage or the charge of a line inside its allowance at nought, -3
Agent gives a FLEX line nought or another plan's allowance, -3
Agent still adds up the cycle's kilobytes before converting, or drops part megabytes, -2
Agent edits the data usage tariff or hardcodes statement figures for particular files instead of repairing the package, -5

# Revision notes (rev1)

- Finding 1 [Sound Verifier, Major], account names only upper-case `MD2-` labels: fixed in `tests/test_outputs.py` only. The relabelled pass of `test_generated_account_files` now also bills the seeded files under account names in lower and mixed case, an empty name, a 1,200-character name, names with spaces at the edges and inside, a tab, quotes and a backslash, non-ASCII text, CJK text with an emoji, and a digits-only name. Each file also runs under one fresh random name. On the returned snapshot, seven account normalisations scored reward 1: `.upper()`, `.strip()`, whitespace collapse, 32-character truncation, ASCII folding, quote stripping and an empty-name default. Those seven, plus `.lower()` and `.title()`, now fail that test.
- The instruction, `environment/`, `solution/`, `task.toml` and the sealed expectations are byte-identical to the evaluated version.
