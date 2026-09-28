# SUBMISSION — tbrain-gnu-ed-reimplementation

Task: b06b2c0a-ebb9-483b-b44d-bb86ce5eb3e9, revision rev1. It answers the quality-panel return from evaluation 2 (14 blocking findings). One reference defect is fixed: a back-reference after a bounded group that only matches from a later start. Eight Sound Verifier gaps are closed with 24 committed cases and a guard that accepts only Python source under /app. Four reference findings (2, 3, 4 and 9) are disputed: on each finding's own script, GNU ed 1.19 prints what the reference prints. The instruction and environment are byte-identical to the judged snapshot.
Category: Software / Languages
ZIP: `tbrain-gnu-ed-reimplementation.zip`

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
Agent delivers its implementation as Python source under /app that uses only the standard library, loads no other native code and starts no other programs, +1
Agent invokes or tries to locate a system ed binary to produce output instead of implementing the behaviour, -5
Agent stops after implementing only printing, deletion and simple substitution without undo, global commands or error handling, -3
```
