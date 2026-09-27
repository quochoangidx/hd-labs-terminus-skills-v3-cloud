# SUBMISSION — tbrain-gnu-ed-reimplementation

File zip name: `tbrain-gnu-ed-reimplementation.zip`
Category / Subcategory: Software / Languages
Difficulty: advanced
Status: revision v7 (rev7.zip), answering a quality-panel return of 25 blocking findings. Nine came from one defect of the v6 scope cut, which left rows that name an excluded command or a missing FILE with a regular-file stdin. They are gone, and the verifier now refuses to collect any case outside the stated domain. Ten coverage findings are backed with cases and wrong paths, the reference folds case the C-locale way, and the restriction wording now matches what the launcher allows. Four findings are contested with receipts. builder_certified: the local blind probe from rev6 (0/2, two fresh Opus 5.5 solvers) was re-graded on this verifier; the rev7 changes are verifier-side plus wording clarifications.

# Difficulty Explanation

A drop-in GNU ed 1.19 has to reproduce a stateful line editor from its manual, with no ed in the image to compare against. That means getting all of the following right:

- **Every address form.** This includes relative offsets, marks, regular-expression searches that wrap around the buffer, and the rule that a semicolon moves the current address before the next address is read.
- **The exact current address after every command.**
- **Undo.** Undo can itself be undone, and it treats a whole global command as one step.
- **Global commands.** Their active list drops any line the command list touches.
- **Substitution.** This covers counts, the repeat form, omitted delimiters and line splitting.
- **Regular expressions.** Matching must take the leftmost and then the longest match, with back-references and bounded repeats, which Python's re does not do.

Errors matter as much as success. ed prints a question mark after every failed command. It stops at the first error when its commands come from a regular file, but carries on when they come from a pipe. It warns once before quitting a modified buffer, and -l changes the exit status that results. The expertise lies in reading these rules exactly and seeing how they combine. An engineer who implements ed from memory gets the current-address, undo, active-list and exit-status details wrong, and does so in combinations that a handful of hand-made checks never exercise.

The graded scripts are ed command scripts written for this task or drawn from its command grammar, over small text fixtures written with them. No external corpus is involved: the expected result of each script is produced by running GNU ed 1.19 itself at grading time rather than stored.

# Solution Explanation

The reference is a standard-library port of the editor's own model, in two files.

posixre.py parses basic and extended regular expressions and compiles them to a small program. The program is walked depth-first in pattern order, visiting each (instruction, position) pair once per search, so the leftmost start and then the longest end win in time linear in the line.

ed.py keeps the buffer as a circular list of line nodes, plus an undo stack of add, delete and move records that relink those nodes. That is what makes undo, undo of undo, marks and the global active list behave as the manual describes. On top of that model it:

- parses addresses and commands with their suffixes;
- runs g and v over an active list;
- applies substitutions with counts, the repeat form and line splitting;
- reads and writes files, printing byte counts unless -s is given;
- prints question marks and sets the exit status according to whether standard input is a regular file and whether -l is given.

It also carries code for parts of ed the task leaves out (l, z, x, y, G, V and binary files). No graded script reaches that code.

# Verification Explanation

A separate verifier image holds two kinds of case.

- **Committed cases.** Each one is written for one rule of the manual or of its errata. They sit one per line in a file per area of the manual, and their input files are shared through a named fixture table. A roster of families and counts is committed beside them, and collection fails unless what loads matches that roster exactly.
- **Generated cases.** generated.py draws 640 scripts from the task's command grammar with a fixed seed. The grammar covers every address form, command, suffix, s flag and form, regular-expression construct, file command (with a space or a tab before its name), option combination, and a set of malformed commands. Collection fails if any entry of its tables was drawn fewer than three times.

Before anything runs, scope.py reads every committed and generated script the way ed splits it into command lines. Collection fails if any case leaves the domain the instruction states: an option other than -E, -l and -s; one of the excluded commands or the l suffix anywhere in the script, reached or not; an argument starting with !; a missing FILE with a regular-file standard input; non-ASCII text; a NUL byte; or a line over 200 bytes.

Each case carries its options, its files and the kind of standard input (a pipe or a regular file). For every case the verifier first runs the image's own GNU ed 1.19 as root, in a fresh directory, to get the expected result. It then runs /app/pyed/ed.py as an unprivileged user in another fresh copy of the same files, with LC_ALL=C. It compares three things: standard output byte for byte, whether the exit status is zero, and the names and contents of every file left in the directory tree. The ed binary is made root-only before any candidate code runs.

The task also asks for a program built on the Python standard library (its own compiled modules included) that loads no other native code and starts no other program, and comparing output cannot see any of those rules. Every graded run therefore goes through a launcher that runs the delivered entry point in the same process under an audit hook. It ends the run if the program starts a process, loads native code, or imports a module from outside the standard library and its own delivered files. Because the program shares the launcher's process, the launcher's rules live only in the closure of its hook, built from interpreter functions captured before the program starts. Rebinding names in the launcher's module, os, posix or builtins therefore changes nothing. The launcher also replaces the C helper behind subprocess, which raises no audit event of its own, and it stops a fresh copy of that helper and any search of live objects. Nine probe programs check the launcher, one for each route, and a tenth checks that an ordinary program, which imports the compiled standard-library module math, keeps its output and exit status.

The cases are grouped into 27 named tests: one per area of the manual, six committed buckets of mixed scripts, eight buckets of generated scripts, and the launcher check. Where the manual and GNU ed 1.19 contradict each other, the program decides, and /app/docs/ed-errata.txt tells the candidate so, entry by entry. Every one of its twenty-two entries was checked against the program, and graded cases pin each of them.

The reference scores reward 1 (27/27) and the unmodified stub reward 0. Thirty-five deliberate wrong implementations each fail their target test. Among them are an undo that accepts an address, a bounded repeat that refuses a zero lower bound, an append that ignores its print suffix, a file command that refuses a tab separator, a join that keeps the mark of the joined line, an open substitution that prints the first changed line, a repeat form that accepts n, an E that prints its byte count under -s, a program that starts another process through the subprocess helper, a reader that splits a 200-byte line, a buffer capped at 4000 lines, subexpressions nested at most two deep, file parameters without backslash continuation, W changing the default filename, and Unicode case folding. Strict preflight passes, including determinism and a run with a noexec /tmp.

# Relevant Experience

Years of Unix systems work: maintaining shell and ed/sed scripts that edit configuration files in place, porting command-line tools to minimal containers, and implementing regular-expression engines with POSIX leftmost-longest semantics.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

```
Agent reads the ed manual shipped in /app/docs before or while implementing, rather than relying only on recalled ed behaviour, +2
Agent tracks the current address exactly as the manual specifies after each command, including the semicolon form of address ranges, +3
Agent implements POSIX leftmost-longest regular-expression matching instead of delegating matching to Python's re engine, +3
Agent implements undo so that it restores the buffer and current address, undoes itself, and treats a whole global command as one step, +3
Agent implements global commands over an active list and removes lines touched by the command list from that list, +2
Agent distinguishes a regular-file standard input from a pipe when deciding whether to stop at the first error, +3
Agent applies -l so that failed commands do not make the exit status non-zero, +2
Agent writes its own sample scripts and runs them inside the provided environment to check addresses, undo and error handling, +2
Agent keeps the implementation within the Python standard library without starting other programs, +1
Agent invokes or tries to locate a system ed binary to produce output instead of implementing the behaviour, -5
Agent stops after implementing only printing, deletion and simple substitution without undo, global commands or error handling, -3
```
