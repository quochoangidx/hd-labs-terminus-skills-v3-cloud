# SUBMISSION — tbrain-gnu-grep-reimplementation

File zip name: `tbrain-gnu-grep-reimplementation.zip`
Category / Subcategory: Software / Languages
Difficulty: advanced
Status: builder_certified (single builder, one independent reviewer, counted blind probe 0/2 with GPT-5.6 via stb harbor, 7/17 and 7/17; no quality panel)

# Difficulty Explanation

A drop-in GNU grep 3.8 has to be rebuilt from the manual alone, with no grep in the image to compare against. That means two engines.

The first is a regular-expression engine. It must handle BRE and ERE with the GNU escapes, character classes and back-references. It must also take the POSIX leftmost-longest match across every pattern, which Python's own re does not do: re is leftmost-first.

The second is the output machinery. It has to get the following exactly right:

- context groups and their separators, including across files;
- -m together with trailing context;
- -o with byte offsets, and -T alignment;
- the precedence of -c, -l, -L and -q;
- per-file counts and names, and NUL-terminated names and records;
- what a binary file prints, and what goes to standard error instead;
- the exit status after a missing file.

The expertise lies in reading each rule of the manual exactly and composing them. An engineer who implements grep from memory of older versions gets the binary-file message, the -L exit status and the context separators wrong, while simple searches pass.

# Solution Explanation

The reference is a standard-library implementation in two files. posixre.py parses GNU BRE and ERE into a tree and matches it with a thread search. The search keeps the leftmost start and the longest end, back-references included.

grep.py does the rest:

- parses options: clustered short options, long options and -NUM;
- splits the pattern list, keeping empty patterns;
- builds a matcher that applies -i, -w and -x. For -w it uses GNU's retry, first at a shorter length and then at later starts;
- runs each file through an emulation of GNU's print loop. That covers pending after-context, bounded before-context, group separators, -m, -o with offsets and the -T width taken from the file size;
- treats a file with a NUL byte as binary and turns each NUL into a line end;
- applies the -c/-l/-L/-q precedence and the exit-status rules.

# Verification Explanation

A separate verifier image holds 1999 cases, split into per-family files of one case per line, with a roster the verifier checks before running. Each case has options, patterns, standard input and named files; some name a missing file and some contain NUL bytes. For every case the verifier first runs the image's own GNU grep 3.8 as root, in a fresh directory, to get the expected standard output and exit status. It then runs /app/pygrep/grep.py as an unprivileged user in another fresh copy with LC_ALL=C. It compares standard output byte for byte, and also the exit status. The grep binary is made root-only before any candidate code runs, and the candidate runs through a launcher that ends the run if it starts another program, loads native code (such as glibc's regex engine through ctypes) or imports anything from outside the standard library.

The cases are grouped into 15 named tests, and two further tests check the launcher on probe programs and read the delivered package. Seven cover areas of the manual: patterns, output controls, only-matching, context, files and exit status, binary input, and NUL-separated data. The other eight hold mixed generated command lines.

Points the manual leaves open were handled in one of two ways. Some are stated in the instruction: option precedence, binary files and file errors. Each of those statements was checked against the real binary. The rest are filtered: a case was kept only if the builder's variant readings, such as the -T width, give the same result.

The reference scores reward 1 (17/17) and the unmodified stub scores reward 0. Nine deliberate wrong implementations each fail their target test:

- leftmost-first regex alternation;
- the first matching pattern winning;
- -w checking only the leftmost match;
- -m ignored;
- no group separator;
- binary files printed as text;
- -z ignored;
- a missing file not raising the exit status;
- delegation to the system grep.

Strict preflight passes, including determinism and a noexec /tmp run.

# Relevant Experience

Years of Unix tooling and text-processing work: writing and debugging grep, sed and awk pipelines, porting shell tooling to minimal containers, and implementing regular-expression engines with POSIX leftmost-longest semantics.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

```
Agent reads the grep manual shipped in /app/docs and the rules in the instruction before or while implementing, rather than relying only on recalled grep behaviour, +2
Agent implements POSIX leftmost-longest regex matching over all patterns instead of delegating matching to Python's re engine, +5
Agent implements context output with group separators, -m with trailing context, and -o with byte offsets as the manual describes, +3
Agent applies the stated precedence of -q, -l, -L and -c and the exit-status rule that 0 means a line was selected, including under -L, +2
Agent treats a file containing a NUL byte as binary and sends the binary-file notice to standard error rather than standard output, +2
Agent handles several files, standard input, --label, -H/-h and a missing file with the stated exit status, +1
Agent writes its own sample command lines and runs them inside the provided environment to check its implementation, +2
Agent keeps the implementation within the Python standard library, without native code (such as ctypes calls into libc regex) or other programs, +1
Agent invokes or tries to locate a system grep binary to produce output instead of implementing the behaviour, -5
Agent prints "Binary file ... matches" on standard output or inverts the -L exit status from memory of older grep versions, -2
```
