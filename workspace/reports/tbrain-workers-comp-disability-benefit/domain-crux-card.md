# Domain-crux card (pattern-blind, written before the pattern catalog)

Slug: tbrain-workers-comp-disability-benefit
Date: 2026-09-27, builder E, task-batch 8 extension (builder_certified, CORE+ bar)

## Domain-native failure mode

A state workers' compensation claims unit pays temporary disability indemnity
(wage-replacement benefits, not medical costs) from a small benefit-statement
package. The statement turns an injured worker's payroll register, the
disability periods the treating doctor certified, the partial earnings the
worker reports after going back to light duty, and the statutory maximum and
minimum weekly rates into what the carrier owes. The package was written from
another state's habits and from how payroll exports look, and it carries slips
a claims adjuster has seen in real indemnity systems: pay credited to the week
it was paid instead of the week it was earned (payroll runs a week in arrears),
the injury week counted in the wage base, a divisor of "weeks with any pay"
for everyone, a 60 per cent rate where the statute says two thirds, this
year's maximum applied to an old injury, a low-wage worker lifted to the
statutory minimum above his own wage, disability periods counted without
their last day, a seven-day waiting period where the statute says three, and
indemnity amounts truncated to the cent.

## What an expert has to judge

- Wages are earned, not paid: an average weekly wage (AWW) is built from the
  weeks the work was done, so the payroll's lag has to be undone before the
  base period is cut. Pay outside the payroll (a bonus, holiday pay, a make-up
  of short pay) is a different animal: nothing in its line says what week's
  work it pays for.
- The base period ends before the injury week; the injury week is not a
  normal week of earnings.
- A full-time worker's AWW is spread over the whole base period; a worker who
  was not paid for most of it (a new hire, a seasonal worker) cannot be averaged
  the same way without understating the wage, and statutes treat that worker
  separately.
- The rate is a fraction of AWW held between a maximum and a minimum fixed by
  the date of injury, not the date of payment; the minimum never lifts a
  worker above his own wage.
- Days of disability are calendar days, both ends included; the waiting
  period is unpaid unless the disability outlasts a qualifying length, and
  then it is paid back.
- Partial disability pays a fraction of the wage loss, never more than the
  total-disability rate.

## Work surface and deliverable

A ~250-line synthetic Python package (`tdbenefit`) plus a fixed driver that
reads one job file (a statutory rate table and a list of claims) and prints a
JSON benefit statement per claim (AWW, weekly rate, waiting and retroactive
days, paid total-disability days and amount, partial weeks and amount,
total). The authority is one numbered in-environment benefits manual. The
candidate repairs the package so the statement follows the manual.

## Why difficulty should survive removing incidental schema

The deliverable is a handful of integers; the schema is trivial. What stays
hard is (a) which pay belongs to which earned week once the payroll lag is
undone, and (b) which workers the full-time averaging rule is written for. A
solver who writes a reference from the manual and fuzzes it only learns what
its own reading of those two scopes says.
