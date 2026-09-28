# SUBMISSION — tbrain-gnu-bc-reimplementation

File zip name: `tbrain-gnu-bc-reimplementation.zip`
Category / Subcategory: Software / Languages
Difficulty: advanced
Status: builder_certified (single builder, one independent reviewer, counted blind probe 0/2 with GPT-5.6 via stb harbor, 2/20 and 3/20; no quality panel)

# Difficulty Explanation

A drop-in GNU bc 1.07.1 has to be rebuilt from its manual page, with no bc in the image to compare against. bc is an arbitrary-precision decimal calculator language with its own grammar and scale rules, and it needs three layers.

**The parser.** It must follow bc's unusual precedence: relational operators bind more loosely than assignment, `!` more loosely than arithmetic, and unary minus more tightly than `^`. It must also know which expression statements print.

**The number layer.** It must reproduce the scale and truncation rules of every operator, of square roots and of powers with negative exponents. It must convert exactly to and from every input and output base, including the grouped digits of bases above 16 and the fraction digits of non-decimal output. All output is split at 70 columns, with one column count shared by numbers and strings.

**The interpreter.** It covers:

- running each line as an execution block that a runtime error abandons;
- keeping `last`;
- dynamically scoped autos and parameters;
- arrays passed by value or by variable;
- converting constants with the input base in force when they run, which inside a function is the base at call time;
- honouring `quit` when it is read, but `halt` only when it executes.

The expertise lies in reading the manual and the stated rules exactly. An engineer who writes bc from memory gets the precedence of `!`, the printing of parenthesised assignments, literal strings, line splitting and constant conversion wrong, while simple arithmetic passes.

# Solution Explanation

The reference is one standard-library file that ports GNU bc 1.07.1. It has four parts:

- **An exact decimal number type** implementing the bc number library: add, subtract, multiply with the product-scale rule, truncating divide and remainder, power by repeated squaring with the in-place scale cut, and a Newton square root.
- **A flex-style scanner.**
- **A precedence-climbing parser** that reproduces the yacc grammar's precedence, its expression flags (which decide whether a statement prints) and its code generation with labels.
- **A byte-code interpreter** mirroring execute.c and storage.c. It keeps per-name stacks for autos and parameters, copies or aliases array parameters, clamps the special variables, and abandons the block on a runtime error. Output goes through bc_out_num with one shared column for line splitting.

# Verification Explanation

A separate verifier image holds 1905 bc programs, split into per-family files of one case per line, with a roster the verifier checks before running. Some programs are split between a FILE argument and standard input.

For every case the verifier first runs the image's own GNU bc 1.07.1 as root, in a fresh directory, to get the expected standard output. It then runs /app/pybc/bc.py as an unprivileged user in another fresh copy with LC_ALL=C, and compares standard output byte for byte. The candidate runs through a launcher that ends the run if it starts another program, loads native code or imports anything from outside the standard library. The bc binary and the dc of the same package are made root-only before any candidate code runs.

The cases are grouped into 18 named tests: one per area of the manual, plus eight buckets of generated programs. The areas are numbers and bases, arithmetic and scale, built-in functions, printing and radixes, strings and print, relational and boolean operators, assignment and variables, control flow, user functions, and runtime errors. Two further tests check the launcher on probe programs and read the delivered package.

The reference matches GNU bc on all 2600 generated programs. Points the manual leaves unstated were handled in one of two ways:

- **Specified in the instruction**, each checked against the binary: product and square-root scale, truncation, number printing, line splitting, constant conversion, `length`, evaluation order, and runtime errors.
- **Filtered.** A program was kept only if four variant readings give the same output. The readings are the manual's literal assignment-statement rule, clean 0/1 results from `&&` and `||`, the manual's base limits, and a negative zero from `^`.

The reference scores reward 1 (20/20) and the unmodified stub scores reward 0. Eleven deliberate wrong implementations each fail their target test:

- full product scale;
- a leading zero printed below one;
- a line column restarted for each number;
- constants converted when the line is read;
- unary minus binding below `^`;
- a runtime error ending the whole program;
- square-root scale ignoring the argument;
- print leaving `last` alone;
- `for` headers printing;
- by-value arrays aliased;
- delegation to the system bc.

Strict preflight passes, including determinism and a noexec /tmp run.

# Relevant Experience

Years of Unix tooling and numerical work: writing bc and dc scripts for build and report pipelines, porting command-line tools to minimal containers, implementing arbitrary-precision decimal arithmetic, and writing parsers and byte-code interpreters for small languages.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

```
Agent reads the bc manual page shipped in /app/docs and the rules in the instruction before or while implementing, +2
Agent implements bc's operator precedence from the manual, including relational operators below assignment and ! below arithmetic, +3
Agent implements exact decimal arithmetic with the scale and truncation rules of each operator rather than binary floating point, +5
Agent implements number output in every obase, including grouped digits above 16, and splits lines at the 69th character across numbers and strings, +3
Agent implements functions with dynamically scoped autos, array parameters by value and by variable, and call-time ibase for constants, +2
Agent makes a runtime error abandon only the current execution block, +1
Agent writes its own sample programs and runs them inside the provided environment to check arithmetic, printing and functions, +2
Agent keeps the implementation within the Python standard library without native code or other programs, +1
Agent invokes or tries to locate a system bc or dc binary, or loads native code, to produce output instead of implementing the behaviour, -5
Agent uses Python floats or Decimal rounding so that results round instead of truncating, -3
```
