# Contract closure

How to write a task whose contract answers a reviewer's question without a
reviewer having to ask it. Every rule here is mechanically checkable, which is
why a task built this way can clear its axes on receipts instead of opinions.

The shape comes from a Java task that cleared the platform panel on all five
axes: a package that departs from an in-repo design note in twenty-nine places,
and a verifier that re-derives the note's answers instead of recording the
reference's. Where a rule below says "verified", it was read out of that task.

---

## 1. One authority, and close it

An authority is a specific, complete, deterministic artifact the candidate can
read: a numbered design note under `environment/`, a named external standard, or
the shipped behavior itself. Point at exactly one. The instruction states the
goal and the boundary; it does not restate the authority's rules, because two
statements of one rule can disagree and a reviewer must then decide which counts.

An authority that only covers the cases you thought of leaves the rest
undecided, and an undecided case is where a contract finding comes from. Close
it with two sentences in the instruction:

- **Universal-rule clause** — a stated rule holds for *every* argument, not only
  the illustrated ones. Without it, `shorter(0, 5)` is an open question.
- **Silence clause** — where the authority says nothing, the existing behavior
  stands. Name what that forbids, with examples from the boundary the candidate
  will actually reach: *"add no throw, clamp or guard to what a published method
  takes now: a side of nought or less, a key or a value of nothing, a setting
  read back that asking for would have been refused."*

The silence clause needs a deterministic artifact behind it, so it belongs to
tasks that repair existing code. A from-scratch task instead declares the domain
it grades and grades nothing outside it.

Add an **entry-point scope clause** to the authority itself whenever tests drive
helpers directly: *"public helpers implement the same rules when called
directly, not only through the top-level entry point."* Otherwise a candidate who
satisfies the entry point and leaves a helper inconsistent has a real argument.

## 2. Publish the coverage envelope

One instruction paragraph naming the *families* of hidden input — shapes, extreme
values, operation orders, malformed data, repeated queries — and no values. It
maps one-to-one onto the test groups.

This is the honest way to keep hidden generalization: the candidate learns what
will be exercised and still has to work out every answer. Without it, a hidden
case outside the visible families reads as an unannounced requirement.

## 3. Every exact convention quotes a sentence

Format, rounding, addition order, overflow, tie-breaks, precedence, error
ordering: if the verifier pins it, the authority must say it, and the manifest
must carry the anchor. An arbitrary constant with no citable sentence is a
finding no matter how reasonable it is.

Disclosing a set is not disclosing an order. Naming six error codes
alphabetically while saying *"listed alphabetically, which is not the order that
matters"* publishes the exact strings and keeps the precedence a real inference.

## 4. State the restriction *and* its allowed exceptions

A restriction enforced by an audit will reject things the prose did not mention:
compiler-generated references, a standard library call that is fine in context, a
sanctioned subset of an otherwise forbidden API. List them.

The verified example allows a whitelist of namespaces, excludes a named list of
subpackages and classes inside them, and then names the exceptions that remain
legal — the print stream behind standard output, the compiler's own bootstraps,
four specific reflection-adjacent methods. An honest solution cannot then fail on
a rule nobody wrote down. Set `allowed_exceptions_disclosed` once this is true.

Every restriction in prose gets a mechanical audit. A restriction the verifier
cannot see is decoration.

## 5. Derive expectations independently of the reference

This is the rule that lets a task stand without a reference reviewer.

The usual chain is circular: the reference defines the behavior, the verifier
records what the reference does, the reference passes. That proves nothing.

Instead, re-derive the expected answers from the authority in the test code,
without importing or invoking the implementation under repair. Oracle=1 then
means two independent derivations of the same authority agree — evidence, not
tautology. The verified task says so in its own words: the plan and the count are
worked out from the note, not recorded from a run, *so the verifier cannot
inherit a mistake the reference made*.

Declare where each expectation comes from:

| `expected_source` | Use when |
|---|---|
| `independent_model` | the test re-derives the answer from the authority |
| `authority_text` | the authority fixes the exact bytes |
| `shipped_differential` | the expectation is the untouched behavior, read from both the shipped and the repaired tree |
| `invariant` | a global claim checked without any expected value |
| `oracle_recorded` | last resort; must be paired with an invariant or a differential |

Write the independent model **before** the Oracle. Written afterwards it copies.

## 6. Turn global claims into invariants

Any authority sentence of the form "doing X at setting Y returns the input
unchanged" or "these two paths agree" is a test that needs no expected value.
The verified task uses one as its main structural check: at unit gain the result
must equal the input cell for cell, which only holds when the level sizes, the
strides and the pairing of parts to passes are all correct at once.

Invariants are the cheapest real coverage available. Harvest every one.

## 7. Guard the silence with a differential

The silence clause promises untouched behavior. Prove it: run the untouched
region against both the shipped and the repaired tree and require the same
answer, including at the ugly boundaries — out-of-range indexes, negative sizes,
non-finite values.

This is the only thing that catches over-repair, where a candidate tidies past
the contract and adds a guard the authority never asked for. An ordinary test
suite never notices.

## 8. One skeleton, four views

The authority's section order, the instruction's topic order, the verifier's test
group order, and the solution's change table are the same list. A reader entering
from any one of them can line it up against the others.

This is not tidiness. It is what makes a reviewer's sampling cheap and a missing
rule visible as a gap in a column.

## 9. Make the solution stand on its own

The reference is judged with the instruction and nothing else — no authority
document, no tests. A patch that is obviously right in context is unreadable
without it, which is how a correct reference collects an `Unsure`.

Head `solve.sh` with a table mapping each authority topic to the file and the
change, plus a sentence on strategy. Keep each hunk to one rule. The verified
example does exactly this, in nine rows and one closing paragraph.

## 10. Get mutants from the design

For a task built by seeding departures, every hunk of the fix reverted on its own
*is* a mutant, and the test for that rule must be the one that fails. Revert them
one at a time through `wrong_path_runner.py`; the untouched repository must fail
every behavioral test. No hand-written mutant catalogue, and no padding to reach
a count.

## 11. Repair the authority, not the test

When a contract finding lands, add a deterministic sentence to the authority.
Loosen or delete a test only when it is demanding something no authority
supports. Patching the test to match the reference hides the defect and keeps the
verifier circular.
