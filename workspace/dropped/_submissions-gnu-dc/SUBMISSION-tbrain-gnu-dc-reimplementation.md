# SUBMISSION — tbrain-gnu-dc-reimplementation

File zip name: `tbrain-gnu-dc-reimplementation.zip`
Category / Subcategory: Software / Languages
Difficulty: advanced
Status: builder_certified (single builder, one independent reviewer, counted blind probe PROBE_RESULT; no quality panel)

# Difficulty Explanation

A drop-in GNU dc 1.4.1 has to reproduce an arbitrary-precision reverse-Polish language from its manual, with no dc in the image to compare against.

The first part is the scale rules of every arithmetic operation. Multiplication keeps the larger operand scale up to the precision, but never beyond the exact result. Division, remainder, divide-with-remainder, exponentiation and modular exponentiation each truncate differently. The square root is taken at the larger of the precision and the argument's scale.

The second part is exact conversion to and from every input and output radix. That includes the grouped digits of radixes above 16, the fraction digits of non-decimal output, and the splitting of long numbers across lines.

The third part is a macro language. Its register stacks each carry their own array, and it has conditional execution, tail calls, and q and Q commands that leave a counted number of macro levels.

Errors are part of the behaviour: dc prints a diagnostic and carries on. The expertise lies in reading these rules exactly. An engineer who implements dc from memory of simpler calculators gets the scale, radix and quit-level details wrong while everything else passes.

# Solution Explanation

The reference is a standard-library port of GNU dc's evaluator, together with the arithmetic of the bc number library. Numbers are kept as a sign, their digits and a scale. That lets each operation reproduce the library's scale and truncation rules, including the Newton iteration of the square root at growing scale and the in-place scale cut of exponentiation.

The evaluator:

- reads commands from expressions, files and standard input with the same one-character lookahead;
- keeps a main stack, plus register stacks that each carry an array;
- evaluates macros with tail-call handling and the level counting of q and Q;
- prints numbers in any output radix, splitting lines at 70 columns.

# Verification Explanation

A separate verifier image holds 1476 scripts, each with its command-line arguments, input files and standard input.

For every case the verifier first runs the image's own GNU dc 1.4.1 as root, in a fresh directory, to get the expected output. It then runs /app/pydc/dc.py as an unprivileged user in another fresh copy, with LC_ALL=C, and compares standard output byte for byte. The dc binary is made root-only before any candidate code runs, so the candidate cannot hand the work to it.

The cases are grouped into 23 named tests: one per chapter of the manual, four buckets of hand-shaped mixed scripts, and eight buckets of generated scripts. A case was kept only if its output does not change under any other plausible reading of a point the manual leaves open or states differently from GNU dc. Some points come up in almost every script, such as leading zeros, how zero prints, line splitting, stack effects after errors, and non-decimal fraction digits. Those conventions are stated in the instruction instead.

The reference scores reward 1 (23/23) and the unmodified stub reward 0. Eight deliberate wrong implementations each fail their target test:

- the full product scale
- lowercase hexadecimal digits
- no line splitting
- l on an empty register pushing nothing
- Z counting leading zeros
- q leaving only one level
- negated comparisons ignored
- delegation to the system dc

Strict preflight passes, including determinism and a run with a noexec /tmp.

# Relevant Experience

Years of Unix tooling and numerical work: writing dc and bc scripts for build and report pipelines, porting command-line tools to minimal containers, and implementing arbitrary-precision decimal arithmetic.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

```
Agent reads the dc manual shipped in /app/docs and the conventions in the instruction before or while implementing, +2
Agent implements the scale rules of multiplication, division, remainder and exponentiation with exact decimal arithmetic rather than binary floating point, +5
Agent implements output in non-decimal radixes, including fraction digits and the grouped digits of radixes above 16, +3
Agent implements register stacks with per-entry arrays and the load, store, push and pop commands as the manual describes, +2
Agent implements macros, conditional execution and the q and Q level counting, +3
Agent splits long numbers across lines as specified, +1
Agent writes its own sample scripts and runs them inside the provided environment to check arithmetic, radix output and macros, +2
Agent keeps the implementation within the Python standard library without starting other programs, +1
Agent invokes or tries to locate a system dc or bc binary to produce output instead of implementing the behaviour, -5
Agent uses Python float or Decimal defaults for arithmetic so that results lose digits or round instead of truncating, -3
```
