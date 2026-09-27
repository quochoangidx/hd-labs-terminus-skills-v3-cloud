# SUBMISSION — tbrain-gnu-sed-reimplementation

File zip name: `tbrain-gnu-sed-reimplementation.zip`
Category / Subcategory: Software / Languages
Difficulty: advanced
Status: rev6 after v7, where rev5 passed the quality panel and every quality gate but the difficulty run was invalid: all 8 agent trials died with NonZeroAgentExitCodeError. The cause was the agent image deleting /bin/sed, which the platform's agent harness itself calls inside the container (Terminus's get-asciinema-timestamp.sh and Harbor's node bootstrap). rev6 keeps GNU sed in the agent image and says so in the instruction; the program is still barred from calling it, and the verifier still makes it root-only. Nothing graded changed. rev7: the rev6 upload failed the static instruction_check (the LLM judge found the 879-word instruction too dense), so the detailed scope moved verbatim into /app/docs/scope.md and instruction.md is now 338 words of prose; nothing graded changed.

# Difficulty Explanation

A drop-in GNU sed 4.9 has to reproduce a stream-editor semantics from its manual. That means four things. First, a script parser that follows sed's own rules for text, labels and delimiters. Second, the cycle model: pattern and hold space, the append queue, n/N at end of input, D restarting without a read, and the t flag resetting on every read. Third, every address form, including per-file numbering under -s and the GNU range forms. Fourth, a regular-expression engine for BRE and ERE with the GNU escapes and classes. It must take the leftmost match and then the longest one, which Python's own re does not do, and it must do so within five seconds even on a pattern that makes a backtracking matcher explode. The expertise lies in knowing which details the manual actually pins down and reading them exactly. For instance, addr1,~N runs to the next multiple of N after addr1 even when addr1 is itself a multiple. And a script whose first two characters are #n turns on -n. An engineer who works from memory of sed rather than from the manual gets these wrong while everything else passes. The image keeps GNU sed for comparison, which shows that an output is wrong but not why, and it cannot be called at grading time, so the matcher and the cycle model still have to be built and reasoned out.

# Solution Explanation

The reference is a standard-library implementation in two files. posixre.py parses GNU BRE and ERE into a tree and compiles it to a thread program that it simulates in the style of a Pike VM, so matching takes time linear in the input for a fixed pattern, on `(a|aa)*b` over a long run of a's as much as on `s/a/b/`. It keeps the leftmost start and the longest end, and takes the groups from the first path in traversal order that reaches that end. sed.py parses scripts: addresses, blocks, labels, a/i/c text and s. It then runs the sed cycle, covering:

- pattern and hold space and the append queue;
- D restarts and n/N at end of input (and at the end of each file under -s);
- the t flag reset on each read but kept across a D restart;
- per-file line numbering, hold space and ranges under -s;
- the section 5.8 escapes inside a/i/c text and the replacement, and any s delimiter, backslash included;
- q/Q exit codes and c over a range;
- input files opened only as the run reaches them, so a missing file after the line where q stops leaves q's exit code alone.

# Verification Explanation

A separate verifier image holds 1,266 cases in five case files, each under 60 KB, plus a small table of shared inputs. Each case has options, a script, input and optional files; files include a missing one, an empty one and `-`. The verifier refuses to run unless the loaded families and their counts match its roster. For every case the verifier first runs the image's own GNU sed 4.9 as root to get the expected standard output and exit status. It then runs /app/pysed/sed.py as an unprivileged user in a fresh directory with LC_ALL=C, with a five-second limit, with no site-packages on its path, under a Python audit hook that ends the run as soon as it starts another process or program, opens native code through ctypes, or loads an extension module from outside Python's own lib-dynload. It compares standard output byte for byte, and also the exit status. Before any candidate runs, the sed binary is made root-only and /app is made unwritable for the candidate's user. A separate test, test_editing_is_done_in_python, rejects any ELF file under /app and any run that trips the hook.

The cases are grouped into 21 named tests, plus the Python-only test. There is one test per area of the manual: substitution and escapes, leftmost-longest matching, bracket expressions, step and regex addresses, +N ranges, multiple ranges, 0,/re/, a/i/c, hold space, multiline commands, branching and the t flag, q/Q, z and =, comments and #n, several files and -s, options and the script argument, and empty input. Four more tests hold mixed generated scripts. Fifteen matrix tests then go through the instruction clause by clause: the section 5.8 escapes in every position; the regex escapes in s and in addresses; every order of g, p and a number; each group \1 to \9; BRE and ERE intervals; q/Q codes including never-reached missing files; t and T around n and N; addresses on blocks; - among files; the append queue flushed by n and N; 40-line inputs; anchors in multi-line pattern spaces; 0,/re/ ends; delimiters; and bracket expressions.

Every case uses only the features the instruction lists, and only behaviour the manual describes; /app/docs/scope.md, which the instruction points to, names the documented commands, flags, modifiers and escapes that are not used, the points the manual leaves open and how GNU sed 4.9 settles them, and the places where the binary departs from its manual, which are not checked. The reference solution scores reward 1 (37/37) and agrees with GNU sed 4.9 on every one of the 1,266 cases. The unmodified stub scores reward 0. Twenty-four deliberate wrong implementations each fail their target test, among them:

- ,~N stopping at addr1;
- #n requiring a newline;
- leftmost-first alternation;
- an exponential backtracking matcher, and a correct matcher that takes six seconds on a pathological pattern;
- the t flag surviving reads, and D clearing the t flag;
- ranges spanning files under -s;
- [\n] as a literal n, and a missing [:xdigit:] class;
- one-line i/c text dropped, and a/i/c text leaving escapes undecoded;
- a tab not accepted before a command;
- an escaped delimiter kept in the replacement;
- an ERE `\?` read as a quantifier;
- delegation to the system sed, and ctypes calls into libc;
- input files all opened before the run, a one-digit q/Q exit code, \r left literal, a number after g ignored, a range on a block kept only on its first line, \n read literally as a bracket range's upper end, and an import of a package that exists only in the verifier image.

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
Agent invokes, bundles or downloads a sed binary, or calls native regex code through ctypes or an extension module, to produce output instead of implementing the behaviour, -5
Agent stops after implementing only the common commands (s, p, d) without handling addresses, hold space or branching, -3
```
