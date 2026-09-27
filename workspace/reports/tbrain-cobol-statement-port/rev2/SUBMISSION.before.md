# SUBMISSION — tbrain-cobol-statement-port

- Task: port the WBILL COBOL job step (quarterly water statements plus payment posting) to Python, byte-for-byte.
- Category: Software / Languages
- ZIP: `workspace/submissions/tbrain-cobol-statement-port.zip`

# Difficulty Explanation

The port has to reproduce, byte for byte and without a compiler, what a GnuCOBOL 3.1.2 build of a 494-line billing and posting program writes. Getting the common paths right is not enough: the hard part is the standard COBOL semantics the program leans on in its rarer paths, which a Python rewrite silently changes. Examples: numeric-edited moves that drop high-order digits and GnuCOBOL's floating-currency behaviour when they do (visible only in the production sample), STRING DELIMITED BY a double space, UNSTRING leaving receiving fields untouched on short lines and counting characters examined rather than moved in COUNT IN, FUNCTION NUMVAL treating a trailing DB like CR as negative, per-statement ROUNDED MODE (nearest-even, away from zero, toward lesser, truncation), and DIVIDE ... ROUNDED ... REMAINDER computing the remainder from the truncated quotient. Two GPT-5.6 runs each ported the program cleanly enough to match the production sample and 21 of the 24 hidden extracts (22 of 25 tests), and both failed on the COUNT IN, NUMVAL DB and ROUNDED REMAINDER rules. The extracts are synthetic but shaped like a water utility's quarterly run: tariff bands, arrears and credits, and a hand-keyed payments file.

# Solution Explanation

The reference port reads both files as fixed-width and delimited records exactly as the COBOL READ and UNSTRING do, does all arithmetic in exact decimals with each statement's ROUNDED or truncation rule and each field's size, formats every numeric-edited picture with one routine that implements zero suppression, floating $/+/-, check protection, CR and trailing sign, BLANK WHEN ZERO, high-order truncation and GnuCOBOL's floating-insertion overflow behaviour, and writes line sequential output with trailing spaces removed. It was fuzzed against the real GnuCOBOL build on several hundred random extract pairs with no byte difference.

# Verification Explanation

The verifier image builds its own copy of WBILL.cbl with GnuCOBOL 3.1.2 in a build stage and runs it on 24 hidden extract pairs (district runs, rejected records, meter rollover, credits, large accounts, names of every shape, rounding boundaries, short lines, header placement, and payments files covering every posting kind, amount form, field count, account shape and memo length); only the resulting statement files are copied into the final image, so no compiler is reachable when the port runs. Each test runs the port as an unprivileged user on copies of one pair and compares its output with the job step's byte for byte, reporting the first differing line. The reference port passes all 25 tests; the shipped stub fails all 24 port tests.

# Relevant Experience

Mainframe and COBOL modernisation: porting batch billing programs to Python and Java, COBOL numeric editing and decimal arithmetic rules, and GnuCOBOL runtime behaviour.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb` (agent image; the verifier's build stage uses the same base plus Debian's gnucobol3 package)
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent writes /app/port/wbill.py as a Python 3 standard-library program that takes the readings, payments and output paths as its three arguments and writes the statement file, +2
Agent formats every numeric-edited field as the picture defines it, including zero suppression, floating currency and sign, check protection, CR and trailing minus, BLANK WHEN ZERO and dropped high-order digits, +3
Agent reproduces the job step's floating-currency output when a value is too large for its field, as the production sample shows, +2
Agent applies each statement's rounding exactly: ROUNDED half away from zero, NEAREST-EVEN for payments, TOWARD-LESSER for refunds, truncation for the relief discount and fees, +3
Agent splits a fee with the part rounded and the remainder computed from the truncated quotient, +2
Agent parses payments lines as UNSTRING does, leaving fields from an earlier line in place when a line has fewer fields and checking the account length by characters examined, +3
Agent accepts, refuses and values amounts exactly as the program's NUMVAL functions do, including trailing CR and DB as negative, +2
Agent prints names cut at the first double space and uppercased, with the no-name text when nothing is left, +1
Agent handles rejected records, meter rollover, credit carry-forward, missing or misplaced headers and short lines as the program does, +2
Agent writes line sequential output with trailing spaces removed and one line feed per record, +1
Agent uses binary floating point for money amounts, -3
Agent runs a COBOL compiler or runtime instead of porting the program's logic, -5
Agent hardcodes statement text for particular input files, -5
Agent edits the legacy program, copybooks, run notes or sample files, -2
