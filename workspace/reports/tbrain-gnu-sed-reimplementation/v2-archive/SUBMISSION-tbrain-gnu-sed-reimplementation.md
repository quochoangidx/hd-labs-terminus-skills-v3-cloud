# SUBMISSION — tbrain-gnu-sed-reimplementation

File zip name: `tbrain-gnu-sed-reimplementation.zip`
Category / Subcategory: Software / Languages
Difficulty: advanced
Status: rev1 after quality-panel return v1 (79 findings: 62 fixed, 3 dropped with their promise, 14 contested with GNU sed 4.9 binary evidence); two fresh fairness reviewers pass; local stb GPT-5.6 trials 0/2

# Difficulty Explanation

A drop-in GNU sed 4.9 has to reproduce a whole stream-editor semantics from its manual, with no sed in the image to compare against. That means four things. First, a script parser that follows sed's own rules for text, labels and delimiters. Second, the cycle model: pattern and hold space, the append queue, n/N at end of input, D restarting without a read, and the t flag resetting on every read. Third, every address form, including per-file numbering under -s and the GNU range forms. Fourth, a regular-expression engine for BRE and ERE with the GNU escapes and back-references. It must take the leftmost match and then the longest one, which Python's own re does not do. The expertise lies in knowing which details the manual actually pins down and reading them exactly. For instance, addr1,~N runs to the next multiple of N after addr1 even when addr1 is itself a multiple. And a script whose first two characters are #n turns on -n. An engineer who works from memory of sed rather than from the manual gets these wrong while everything else passes.

# Solution Explanation

The reference is a standard-library implementation in two files. posixre.py parses GNU BRE and ERE into a tree and compiles it to a thread program in the style of a Pike VM, back-references included, so matching stays polynomial on inputs such as `(a|aa)*b` over a long run of a's. It keeps the leftmost start and the longest end, and takes the groups from the first path in traversal order that reaches that end. sed.py parses scripts: addresses, blocks, labels, a/i/c text, s and y. It then runs the sed cycle, covering:

- pattern and hold space and the append queue;
- D restarts and n/N at end of input (and at the end of each file under -s);
- the t flag reset on each read but kept across a D restart;
- per-file line numbering, hold space and ranges under -s;
- case-insensitive back-references under I, and the section 5.8 escapes inside y;
- q/Q exit codes and l line wrapping.

# Verification Explanation

A separate verifier image holds 927 cases in three case files, each under 25 KB, plus a small table of shared inputs. Each case has options, a script, input and optional files; files include a missing one, an empty one and `-`. The verifier refuses to run unless the loaded families and their counts match its roster. For every case the verifier first runs the image's own GNU sed 4.9 as root to get the expected standard output and exit status. It then runs /app/pysed/sed.py as an unprivileged user in a fresh directory with LC_ALL=C. It compares standard output byte for byte, and also the exit status. The sed binary is made root-only before any candidate runs, so the candidate cannot hand the work to it. A candidate that tries fails on the first case it delegates.

The cases are grouped into 24 named tests. There is one test per area of the manual: substitution and escapes, leftmost-longest matching, back-references, bracket expressions, case conversion, step and regex addresses, +N ranges, multiple ranges, 0,/re/, a/i/c, hold space, multiline commands, branching and the t flag, q/Q, l, y/z/=, comments and #n, several files and -s, options and the script argument, and empty input. Four more tests hold mixed generated scripts.

Each case was kept only if its output does not change under any other plausible reading of the manual that the manual itself does not rule out. Where the manual is silent but a case is still graded, the instruction states the convention: the `l` wrap width, `[=c=]` in the C locale, and escapes inside `y`. The reference solution scores reward 1 (24/24). The unmodified stub scores reward 0. Fourteen deliberate wrong implementations each fail their target test:

- ,~N stopping at addr1;
- #n requiring a newline;
- leftmost-first alternation;
- the t flag surviving reads;
- ranges spanning files under -s;
- [\n] as a literal n;
- delegation to the system sed;
- one-line i/c text dropped;
- lowercase i/m s flags rejected;
- equivalence classes matching nothing;
- \u consumed by an empty group;
- back-references case-sensitive under I;
- D clearing the t flag;
- an exponential backtracking matcher.

Strict preflight, including determinism and a noexec /tmp run, passes.

# Relevant Experience

Years of Unix tooling and text-processing work: writing and debugging sed and awk pipelines, porting shell tooling to minimal containers, and implementing regular-expression engines with POSIX leftmost-longest semantics.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

```
Agent reads the sed manual shipped in /app/docs before or while implementing, rather than relying only on recalled sed behaviour, +2
Agent implements POSIX leftmost-longest regex matching (longest match among those starting leftmost, across alternatives) instead of delegating matching to Python's re engine, +5
Agent implements the GNU address forms first~step, addr1,+N, addr1,~N and 0,/regexp/ as the manual defines them, +3
Agent implements the sed cycle with hold space, the append queue, D restart without reading new input, and n/N behaviour at end of input, +3
Agent resets the t command's substitution flag whenever a new line of input is read, +2
Agent handles -s by restarting line numbers and address ranges for each input file, +2
Agent treats a script whose first two characters are #n as equivalent to -n, +1
Agent writes its own comparison checks or sample scripts and runs them inside the provided environment to exercise its implementation, +2
Agent invokes or tries to locate a system sed binary to produce output instead of implementing the behaviour, -5
Agent stops after implementing only the common commands (s, p, d) without handling addresses, hold space or branching, -3
```
