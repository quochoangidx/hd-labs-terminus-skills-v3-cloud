# SUBMISSION — tbrain-cobol-statement-port

- Task: port the WBILL COBOL job step (quarterly water statements plus payment posting) to Python, byte-for-byte.
- Category: Software / Languages
- ZIP: `workspace/submissions/tbrain-cobol-statement-port.zip`

# Difficulty Explanation

The port has to reproduce, byte for byte and without a compiler, what a GnuCOBOL 3.1.2 build of a 494-line billing and posting program writes. Getting the common paths right is not enough: the hard part is the standard COBOL semantics the program leans on in its rarer paths, which a Python rewrite silently changes. Examples include numeric-edited moves that drop high-order digits and GnuCOBOL's floating-currency behaviour when they do, STRING DELIMITED BY a double space, UNSTRING leaving receiving fields untouched on short lines and counting characters examined rather than moved in COUNT IN, FUNCTION NUMVAL treating a trailing DB like CR as negative, per-statement ROUNDED MODE (nearest-even, away from zero, toward lesser, truncation), and DIVIDE ... ROUNDED ... REMAINDER computing the remainder from the truncated quotient. Correctness requires a mainframe-modernisation engineer to reconcile these interacting language semantics with fixed-width records, exact decimal fields, tariff bands, arrears and credits, and a hand-keyed payments stream rather than merely translate the common control flow.

# Solution Explanation

The reference port reads both files as fixed-width and delimited records exactly as the COBOL READ and UNSTRING do, does all arithmetic in exact decimals with each statement's ROUNDED or truncation rule and each field's size, formats every numeric-edited picture with one routine that implements zero suppression, floating $/+/-, check protection, CR and trailing sign, BLANK WHEN ZERO, high-order truncation and GnuCOBOL's floating-insertion overflow behaviour, and writes line sequential output with trailing spaces removed. It was fuzzed against the real GnuCOBOL build on several hundred random extract pairs with no byte difference.

# Verification Explanation

The verifier image builds its own copy of WBILL.cbl with GnuCOBOL 3.1.2 in a build stage and runs it on 54 hidden extract pairs: 30 written for particular paths (district runs, a run of 500 reading records and 500 postings, and a headerless run of 500 customer records with a posting to each account, whose sizes the tests assert, rejected records, record types other than H and C, meter rollover, credits, commercial accounts past half a million units, names of every shape, rounding boundaries, short and empty lines, short, missing and misplaced headers, and payments files covering every posting kind, amount form, field count, account shape (including account identifiers that are not all digits, and fields longer than the eight-character account) and memo length up to the 80-byte line) and 24 drawn with a fixed seed from the whole input contract in the run notes. While the image is built it also checks that the shipped production sample is the job step's own output; the port is graded only on the hidden pairs, never on that disclosed pair. Only generated statements and the sealed test inputs reach the final verifier image; no compiler does. Each test runs the single collected Python file exactly as the instruction documents, as an unprivileged user, with the three files in separate directories of a randomly named scratch tree under the same neutral names for every case and an empty working directory, so nothing the port can see identifies the case, and with no time limit beyond the verifier's own budget. The image enforces Python and the standard library by construction: the system interpreter has no third-party packages (pytest sits in a root-only virtual environment), and the unprivileged user can start and read no program other than the Python interpreter, so Python worker processes work while delegation to any other program cannot. It rejects non-regular output files and compares output bytes with the job step's.

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

# Revision Notes (rev5, answers the v5 quality-panel return)

1. Sound Verifier, Major (500 customers with no header) — fixed. The only fixture at the 500-record limit was one header plus 499 accounts, so a port that keeps one of its 500 places for a header passed. On the panel's own input (500 headerless zero-usage accounts, empty payments) the verifier's GnuCOBOL build prints 500 billed and $165.00; such a port prints 499 and $164.67, and the returned verifier gave it reward 1. A new case, long_run_no_header, has 500 customer records and no header, plus 500 postings with one to each account including the last; its test asserts both sizes before the byte comparison. That port now scores 0, failing only this test; the reference passes 55/55.

The v4 findings are not raised again (the panel lists Coherent Contract, Correct Reference Solution, Protected Ground Truth and Deterministic Execution as clean). The agent-visible task (instruction, legacy source, run notes, sample, stub) and the reference are unchanged. Oracle 1 (55/55, also under a noexec /tmp), NOP 0, three repeated oracle runs identical.

# Revision Notes (rev4, answers the v4 quality-panel return)

1. Correct Reference Solution, Major (UNSTRING COUNT IN) — disputed. GnuCOBOL 3.1.2, the pinned build the verifier itself uses, stores in COUNT IN the number of characters examined for the field (the whole piece before the delimiter), not the number that fit into PIC X(8). Running the panel's own input, the sample readings with the payment line `10004821X;PAY;1.00;cash`, through the verifier's build stage prints `LINE   1 REJECTED BAD ACCOUNT`, byte-identical to the reference. The graded corpus already contained this case (generated_01, a nine-character account field, expected `BAD ACCOUNT`) and the reference passed it in every platform oracle run. This revision adds three explicit over-width account lines to postings_account_identifiers (`ABCDEFGHI`, `91000001X`, `ABCDEFGH ` where the first eight characters are billed accounts) so the case is graded by name, and marks the rule in the reference as checked against the binary. Evidence is posted in #terminus-3-submissions.
2. Correct Reference Solution, Major (FUNCTION INTEGER) — disputed. FUNCTION INTEGER returns the greatest integer not greater than its argument; INTEGER-PART is the truncating function. The verifier's GnuCOBOL 3.1.2 build prints `WHOLE     -2` for `10000001;ADJ;-1.20;x` (and for REF, FEE and PAY -1.20, and ADJ -1.50), byte-identical to the reference. The graded postings_rounding_modes fixture already holds `ADJ;-12.345` (expected `WHOLE -13`) and `ADJ;-0.50` (expected `WHOLE -1`), both produced by the verifier's own COBOL build and passed by the reference on the platform. The reference is unchanged apart from a comment recording the check. Evidence is posted in #terminus-3-submissions.
3. Protected Ground Truth, Major (graded disclosed sample) — removed. test_supplied_production_sample and the samples copy in the final verifier image are gone; the port is graded only on the 53 hidden pairs. The build stage still compiles the job step and checks that the shipped sample statement is its own output, which is what the instruction says about the sample.
4. Protected Ground Truth, Major (case label in argv and cwd) — fixed. Every run now uses a fresh randomly named scratch tree with the same neutral names for every case (extract/readings.dat, export/payments.txt, print/statement.out, an empty cwd), so nothing the port can see identifies the case. A port whose empty-input handling keyed on the label `empty_file` scored 1 on the returned verifier and scores 0 now; the rev1 witness that ignores its arguments still fails.
5. Sound Verifier, Minor (500-record scale not visible) — fixed. long_run was already 500 reading records (one header plus 499 accounts) and 500 postings; test_long_run now asserts both counts before the byte comparison, so a shrunk fixture fails the verifier on its own. With the fixture cut to 100 lines the returned verifier accepted a port capped at 100 records; the repaired verifier rejects that fixture outright.

The agent-visible task (instruction, legacy source, run notes, sample, stub) is unchanged. Oracle 1 (54/54, also under a noexec /tmp), NOP 0, three repeated oracle runs identical.
