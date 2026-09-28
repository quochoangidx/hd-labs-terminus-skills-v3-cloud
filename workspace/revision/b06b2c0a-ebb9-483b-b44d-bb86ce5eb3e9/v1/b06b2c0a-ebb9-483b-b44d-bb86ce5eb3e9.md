# Terminal Bench 2.0 — Task Revise Report

> Comprehensive task information extracted from the Snorkel Experts task payload.
> This is the same data that populates the task's right-hand **Revise panel** (Difficulty Explanation, Solution Explanation, checks, rubrics, agent runs, etc.).

## 1. Task Identity & Metadata

| Field | Value |
|---|---|
| Project | `Terminus-3-Prod` |
| Project ID | `a34832f4-76f4-4d2a-aa62-c92deb15675d` |
| Assignment ID | `e716194e-50d9-4ed3-9ec7-fb282233f05f` |
| Task ID | `b06b2c0a-ebb9-483b-b44d-bb86ce5eb3e9` |
| Submission ID | `b06b2c0a-ebb9-483b-b44d-bb86ce5eb3e9` |
| Task category (stage) | `SUBMISSION` |
| Submission task type | `submission-8d482d68-4d7e-449f-9388-b3cb0cefb643` |
| Review task type | `submission-8d482d68-4d7e-449f-9388-b3cb0cefb643` |
| Form schema revision | `9110301d-4bfc-42cc-8185-74945ca1a856` |
| Skippable | `false` |
| Further revisions allowed | `true` |
| Expiry time | `2027-02-24T15:45:00.018031Z` |

### Task Classification (submission_document)

| Field | Value |
|---|---|
| Difficulty | **** |
| Solvable | `` |
| Task category | `Software` |
| Task subcategories | `["Languages"]` |
| Task languages | `python` |
| Codebase size | `` |
| Number of milestones | `` |
| Submission AHT (min) | `120` |
| Uses approved canonical base image | `true` |
| Used Task Gallery inspiration | `false` |
| Send to reviewer | `` |
| Generate rubrics | `` |

## 2. Submission Artifact

| Field | Value |
|---|---|
| Filename | `tbrain-gnu-ed-reimplementation.zip` |
| Uploaded at | `2026-09-27T07:20:11.877Z` |
| S3 URI | `s3://daas-blobs/prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/e716194e-50d9-4ed3-9ec7-fb282233f05f/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-27T07:20:10.412Z.zip` |
| S3 key | `prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/e716194e-50d9-4ed3-9ec7-fb282233f05f/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-27T07:20:10.412Z.zip` |

- **Difficulty-check artifact:** `s3://daas-blobs/codebuild_uploads/autoeval_artifacts/agent_runner/fbe4246a-5328-4836-a491-bd5bd26e0849/difficulty_check/2f8dce8181f0/logs_artifact.zip`

## 3. Reviewer Narrative Fields (Right Panel)

### Difficulty Explanation

> *Describe in your own words why your task is challenging for humans and agents to solve.*



### Solution Explanation



### Verification Explanation



## 4. Difficulty Check — Agent Simulation Summary

Overall: **difficulty check not run** (see the summary and quality panel below).

### Agent Performance

| Agent | Accuracy | Runs | Successes | Timeouts | Other failures |
|---|---|---|---|---|---|

### Per-Test Results (pass count across runs)

| Test | Passed / 0 |
|---|---|

### Full Difficulty-Check Text Summary

```
## Pre-Difficulty Gate Failed

Difficulty not run: the submission did not pass every blocking quality or quality panel check. Oracle/NOP already passed. No Opus, GPT, analysis, or rubric-generation runs were started.

QUALITY PANEL: NEEDS REVISION -- 14 blocking issues to fix. Details for each are below.

Blocking (fix every one):
   1. [Correct Reference Solution] MAJOR: Bounded-repeat run bookkeeping is reused across search
      starting positions even for patterns with backreferences, suppressing a capture needed by
      the later, leftmost valid match.
   2. [Correct Reference Solution] MAJOR: Successful substitution yanks the deleted
      pre-substitution line instead of copying the last modified replacement line into the cut
      buffer.
   3. [Correct Reference Solution] MAJOR: A bare alternative substitution-repeat command `s` is
      rejected as a malformed new substitution instead of repeating the last substitution.
   4. [Correct Reference Solution] MAJOR: Repeated substitution with r uses any last compiled
      regexp, rather than only a search regexp that occurred after the previous substitution.
   5. [Sound Verifier] MAJOR: No case requires `*`, basic `\+`, or basic `\{N,\}` to match a
      long run, so a plausible fixed repetition cap passes despite changing their open-ended
      semantics.
   6. [Sound Verifier] MAJOR: Global-list coverage omits the supported f FILE command, allowing
      an otherwise functional editor to reject that command only inside g lists.
   7. [Sound Verifier] MAJOR: No case checks that v rejects a nested global command in its
      command list, although v inherits g's prohibition on nested g and v.
   8. [Sound Verifier] MAJOR: No extended-regexp case rejects a repeat whose upper bound exceeds
      32767.
   9. [Correct Reference Solution] MINOR: The address parser caps each numeric offset component
      before evaluating the complete address, potentially rejecting an address whose final value
      is valid.
  10. [Sound Verifier] MINOR: The corpus never uses a valid lowercase mark outside a, b, and x,
      allowing a mark implementation restricted to those letters to pass.
  11. [Sound Verifier] MINOR: The import guard treats any import origin under /app as allowed
      without requiring it to be Python source, so it accepts candidate-supplied Python bytecode
      despite the contract's source-files-only allowance.
  12. [Sound Verifier] MINOR: The corpus has no decimal-address case above line 33, despite the
      contract allowing starting files of a few dozen lines and decimal N through the last line.
  13. [Sound Verifier] MINOR: The generated grammar never exercises a numeric relative offset
      whose magnitude exceeds two, leaving +N/-N support beyond that value unverified.
  14. [Sound Verifier] MINOR: The tests exercise no more than three consecutive bare + or -
      signs, so cumulative bare-offset repetition beyond that is not checked.

Checked and clean: Coherent Contract, Protected Ground Truth, Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Correct Reference Solution] MAJOR
   Bounded-repeat run bookkeeping is reused across search starting positions even for patterns
   with backreferences, suppressing a capture needed by the later, leftmost valid match.
   Why this fails:
     Reach: Start with a file containing `aaab\n` and submit `s/\(a\{1,2\}\)\1b/X/\n,p\nQ\n`
     through a pipe. The contract requires a search to find the leftmost match: none starts at
     byte 0, but starting at byte 1 the group captures `a`, `\1` consumes the next `a`, and `b`
     consumes the last byte. Substitution must produce `aX\n`. At start 0 the reference's
     bounded-repeat instruction offers endpoints 1 and 2 and records them as already offered. At
     start 1 it offers endpoint 3 but suppresses endpoint 2, the one representing capture `a`;
     the endpoint-3 capture `aa` cannot satisfy the backreference. Search therefore reports no
     match. Flip: the reference emits `?\n`, leaves `aaab\n` for `,p`, and exits nonzero instead
     of printing the successful substitution's `aX\n` and exiting zero.
   Where to look: environment/app/docs/ed.txt:509-515, environment/app/docs/ed.txt:446-450,
     solution/pyed/posixre.py:324-333, solution/pyed/posixre.py:426-445,
     solution/pyed/posixre.py:467-476, solution/pyed/posixre.py:501-509

2. [Correct Reference Solution] MAJOR -- core domain and business logic
   Successful substitution yanks the deleted pre-substitution line instead of copying the last
   modified replacement line into the cut buffer.
   Why this fails:
     Reach: run the valid pipe script `a\nabc\n.\ns/b/X/\nx\n,p\nQ\n`. Contractually, s changes
     line 1 to `aXc` and copies that last modified line to the cut buffer, so x after current
     line 1 yields two lines `aXc`, and `,p` prints `aXc\naXc\n`. The reference's
     search_and_replace calls delete_lines(1,1), whose delete_lines first calls yank_lines and
     therefore stores `abc`; it then inserts `aXc` without changing yank. x consequently inserts
     `abc`, and `,p` prints `aXc\nabc\n`. Flip: the required stdout and final buffer differ.
   Where to look: environment/app/docs/ed.txt:897-902, solution/pyed/ed.py:302-313,
     solution/pyed/ed.py:637-655, solution/pyed/ed.py:1304-1313

3. [Correct Reference Solution] MAJOR -- core domain and business logic
   A bare alternative substitution-repeat command `s` is rejected as a malformed new
   substitution instead of repeating the last substitution.
   Why this fails:
     Reach: run the valid pipe script `a\naa\n.\ns/a/b/\ns\np\nQ\n`. The first substitution
     changes `aa` to `ba`; the documented zero-suffix alternative `s` repeats it and changes
     `ba` to `bb`, so p must print `bb\n` with no error. In command_s, the bare newline sets
     sflags to 8, but the code then takes the `else` new-substitution branch rather than the
     repeat branch, calls get_pattern_for_s with newline as delimiter, and fails. It emits `?\n`
     and p prints `ba\n`. Flip: stdout is `?\nba\n` rather than `bb\n`, and the buffer differs.
   Where to look: environment/app/docs/ed.txt:923-933, solution/pyed/ed.py:1029-1089,
     solution/pyed/ed.py:1265-1267, solution/pyed/ed.py:1411-1420

4. [Correct Reference Solution] MAJOR -- core domain and business logic
   Repeated substitution with r uses any last compiled regexp, rather than only a search regexp
   that occurred after the previous substitution.
   Why this fails:
     Reach: with pipe stdin, run the contract-valid script `a\na\n.\ns/a/aa/\nsr\np\nQ\n`. The
     first substitution changes `a` to `aa`; no address search has occurred after it. The
     contract says r uses the last search RE only if that search happened after the
     substitution, so `sr` must fail, producing `?\n`; `p` then prints `aa\n`, and absent -l the
     exit status is nonzero. Flip: at lines 1058-1081 the reference merely tests that
     last_regexp is non-null. The preceding substitution compiled `a` and stored it as
     last_regexp (lines 430-437 and 1107), so `sr` succeeds and replaces the first `a` in `aa`
     with the prior replacement `aa`, leaving `aaa`; `p` emits `aaa\n` and Q exits zero. This
     differs in stdout, buffer result, and exit status.
   Where to look: environment/app/docs/ed.txt:923-934, solution/pyed/ed.py:430-437,
     solution/pyed/ed.py:1058-1081, solution/pyed/ed.py:1106-1112

5. [Sound Verifier] MAJOR -- missing behavioral coverage
   No case requires `*`, basic `\+`, or basic `\{N,\}` to match a long run, so a plausible fixed
   repetition cap passes despite changing their open-ended semantics.
   Why this fails:
     Reach: A contract-legal pipe script `a\n` followed by 100 `a` characters and
     `\n.\ns/a*/X/p\nQ\n` has a 100-byte input line. GNU ed prints `X\n`. Equivalent scripts
     using `s/a\+/X/p` or `s/a\{1,\}/X/p` require the same 100-character match. Flip: A regex
     implementation that caps open-ended repetitions at 64 matches only 64 characters and prints
     `X` followed by 36 `a` characters and a newline. It can still compile the 32767-count
     patterns in regex.jsonl:66-69, whose short fixture does not require matching 32767
     characters, and handle the short repeated matches in regex.jsonl:72-74. The generated
     source lines are drawn from the short table at generated.py:22-27. The verifier's equality
     comparison would reject this implementation on the proposed input, but none of those shown
     cases supplies it.
   Where to look: instruction.md:7-10, tests/cases/regex.jsonl:66-69,
     tests/cases/regex.jsonl:72-74, tests/generated.py:22-27, tests/generated.py:183-185,
     tests/test_outputs.py:170-179

6. [Sound Verifier] MAJOR -- missing behavioral coverage
   Global-list coverage omits the supported f FILE command, allowing an otherwise functional
   editor to reject that command only inside g lists.
   Why this fails:
     Reach: The contract-legal pipe script `a\nx\n.\ng/x/f target\nf\nQ\n`, starting with no
     files, distinguishes the behavior. GNU ed's global f sets and prints `target`; the
     following bare f prints `target` again. Flip: An implementation with working ordinary f but
     a global-list dispatcher limited to the commands exercised by the corpus rejects `f target`
     in the list, producing a `?` instead of the first `target\n`. The committed global cases
     and mixed scripts shown do not invoke global f, and the generated G_LISTS table has no f
     entry, so that omission clears their comparisons while failing this permitted script.
   Where to look: environment/app/docs/ed.txt:651-653, environment/app/docs/ed.txt:668-675,
     tests/generated.py:59-61, tests/test_outputs.py:165-179

7. [Sound Verifier] MAJOR -- missing behavioral coverage
   No case checks that v rejects a nested global command in its command list, although v
   inherits g's prohibition on nested g and v.
   Why this fails:
     Reach: With an empty starting buffer and pipe stdin, the contract-legal script
     `a\nx\n.\nv/nomatch/g/x/p\nQ\n` selects `x` for v, then attempts a forbidden nested g. GNU
     ed emits `?\n`; a v handler that executes the nested g instead also prints `x\n`. Flip:
     That handler can implement the other rules normally and pass the shown nested-global
     checks, which are `g/a/g/a/p` and `g/a/v/a/p`, while producing different stdout on this
     input. The generated command-list table contains no nested g or v, so its v draws do not
     supply the missing check.
   Where to look: environment/app/docs/ed.txt:668-677, environment/app/docs/ed.txt:787-789,
     tests/cases/global_commands.jsonl:24-25, tests/generated.py:59-61,
     tests/generated.py:168-174, tests/test_outputs.py:165-179

8. [Sound Verifier] MAJOR -- missing behavioral coverage
   No extended-regexp case rejects a repeat whose upper bound exceeds 32767.
   Why this fails:
     Reach: With a starting file containing `z\n`, run `-E` and `g/y{0,32768}|z/p\nQ\n`; the
     upper bound makes the expression invalid under the stated GNU rule. Flip: A plausible
     implementation with separate BRE and ERE repeat parsers that validates both BRE bounds but
     only the ERE lower bound would print `z\n` instead of the reference error notification. It
     clears the committed boundary cases: the basic tests check upper bounds, while the extended
     test checks `{32768,}` and `{32767,}`. The generated ERE pattern table contains no large
     upper bound.
   Where to look: environment/app/docs/ed-errata.txt:51-52, tests/cases/regex.jsonl:66-69,
     tests/cases/regex_extended.jsonl:16, tests/generated.py:43-45

9. [Correct Reference Solution] MINOR -- Input validation and contract-bound behavior
   The address parser caps each numeric offset component before evaluating the complete address,
   potentially rejecting an address whose final value is valid.
   Why this fails:
     Reach: unverified—the contract permits intermediate address values beyond the last line.
     With a one-line buffer, `0+2147483648-2147483648=` has final address 0, but parse_int
     rejects its first offset at 2147483648, before the subtraction. Flip: if GNU ed accepts
     that component, it prints `0\n`, whereas the reference prints `?\n` and records a failure.
     GNU ed's disposition for this oversized component was not independently established.
   Where to look: environment/app/docs/ed.txt:415-430, solution/pyed/ed.py:818-835,
     solution/pyed/ed.py:843-866, solution/pyed/ed.py:1412-1414

10. [Sound Verifier] MINOR -- missing behavioral coverage
   The corpus never uses a valid lowercase mark outside a, b, and x, allowing a mark
   implementation restricted to those letters to pass.
   Why this fails:
     Reach: A contract-legal regular-file-stdin case starts with f.txt containing `a\n` and uses
     `1kc\n'cs/a/b/\nw out\nQ\n` with `-s f.txt`. GNU ed accepts mark c, leaves out containing
     `b\n`, emits no stdout, and exits zero. Flip: An otherwise correct implementation that
     rejects marks outside a, b, and x emits `?\n` at `1kc` and stops on regular-file stdin,
     leaving no out file and exiting nonzero. It clears the shown mark cases, which use only
     those three letters, and the generator's k branch, which chooses only a or b. This exact
     restricted set is verifier-tailored, hence Minor.
   Where to look: environment/app/docs/ed.txt:409-412, tests/generated.py:156-157,
     tests/cases/addresses.jsonl:81-83, tests/test_outputs.py:159, tests/test_outputs.py:165-179

11. [Sound Verifier] MINOR -- build, dependency, or interface enforcement mismatch
   The import guard treats any import origin under /app as allowed without requiring it to be
   Python source, so it accepts candidate-supplied Python bytecode despite the contract's
   source-files-only allowance.
   Why this fails:
     Reach: a submission can leave /app/pyed/ed.py as source but have it import
     /app/pyed/implementation.pyc, a legacy bytecode module produced during image construction
     and containing the editor implementation. On the first graded run the import warden
     resolves that origin under its own-tree prefix and returns it as permitted at
     guard.py:103-105; it does not inspect the suffix. Flip: the .pyc implementation can emit
     exactly GNU ed's output, status, and filesystem state, so every test_outputs.py:171-179
     comparison passes, although importing a .pyc is not importing a Python source file as O24
     requires. This construction requires knowledge of the guard's prefix-only rule rather than
     being an ordinary source-based submission, hence Minor.
   Where to look: tests/guard.py:97-113, tests/guard.py:123-133, tests/test_outputs.py:165-179

12. [Sound Verifier] MINOR -- missing behavioral coverage
   The corpus has no decimal-address case above line 33, despite the contract allowing starting
   files of a few dozen lines and decimal N through the last line.
   Why this fails:
     Reach: the complete fixture table's largest starting buffer is big_03 with 33 lines, and
     generated buffers have only 2-14 lines. A contract-legal fixture containing 34
     newline-terminated ASCII lines with script `34p\n` would require decimal address 34. Flip:
     an implementation that rejects line numbers above 33 (or caps its buffer at 33) matches
     every graded fixture and generated buffer, hence clears the tuple equality at
     tests/test_outputs.py:171-179, but emits `?` rather than GNU ed's 34th line on that input.
     This exact cap is verifier-aware, so the finding is Minor.
   Where to look: tests/cases/fixtures.json:14-18, tests/generated.py:183-185,
     tests/test_outputs.py:171-179

13. [Sound Verifier] MINOR -- missing behavioral coverage
   The generated grammar never exercises a numeric relative offset whose magnitude exceeds two,
   leaving +N/-N support beyond that value unverified.
   Why this fails:
     Reach: `ATOMS` contains only literal `+2` and `-2`, and `OFFSETS` contains only `+1` and
     `-1` in addition to bare signs. A legal four-line input with current line 1 and script
     `1+3p\n` distinguishes an implementation that parses only magnitudes 0, 1, and 2. Flip:
     that implementation behaves identically on all generated forms and the displayed committed
     cases, so it clears the GNU tuple comparison, but rejects or misaddresses `+3` where GNU
     prints line 4. Choosing this boundary requires knowledge of this grammar table, making it
     Minor.
   Where to look: tests/generated.py:29-34, tests/generated.py:95-110,
     tests/test_outputs.py:171-179

14. [Sound Verifier] MINOR -- missing behavioral coverage
   The tests exercise no more than three consecutive bare + or - signs, so cumulative
   bare-offset repetition beyond that is not checked.
   Why this fails:
     Reach: an address parser that accepts one, two, and three bare signs but rejects a fourth
     passes the generator: its atom is at most `++`/`--`, followed by at most one optional bare
     sign. On a valid five-line buffer, `1++++p\n` must print line 5. Flip: the capped parser
     clears all generated and committed cases but gives GNU-incompatible failure/output for that
     distinguishing input. The three-sign cap is tailored to the visible generator, so this is
     Minor.
   Where to look: tests/generated.py:30-34, tests/generated.py:109-121,
     tests/test_outputs.py:171-179
```

## 5. Quality Check Results

### Quality Check Summary

```
## Quality Check Results
✅ pass - verifiable: The verifier (tests/test_outputs.py + guard.py + generated.py + scope.py) is fully programmatic: it runs the candidate's ed.py and the real GNU ed 1.19 binary on identical fixtures and diff-checks stdout, exit status, and the resulting file tree byte-for-byte. No LLM-as-judge, no subjective grading. It runs entirely offline (no-network verifier), with a fixed random seed for generated cases, so re-runs are deterministic. test.sh performs no runtime installs (pytest/ed are baked into tests/Dockerfile).
✅ pass - solvable: A complete working solution is provided (solution/pyed/ed.py, 1442 lines; solution/pyed/posixre.py, 476 lines) implementing the full editor and a POSIX leftmost-longest regex engine, installed via solve.sh. The task declares expert_time_estimate_hours = 8, i.e. roughly a single expert workday rather than a multi-day/team effort, and the manual plus errata document are provided so an expert does not need to discover the spec from scratch.
✅ pass - difficult: Reimplementing GNU ed exactly (undo/redo stack semantics, global-command active lists, mark invalidation, POSIX BRE/ERE leftmost-longest matching with backreferences and bounded repeats, substitution edge cases, and 22 documented deviations from the manual) requires genuine systems/regex-engine expertise well beyond an average undergraduate project; this is reflected in the detailed errata list and the fact that memory-based reimplementations reliably get subtle cases wrong.
✅ pass - interesting: The instruction motivates the task with a realistic scenario (porting maintenance scripts that pipe commands into ed onto minimal images lacking ed), and reimplementing standard Unix tools for constrained/embedded environments is genuine professional work (e.g., BusyBox-style utilities, embedded Linux teams).
✅ pass - outcome_verified: Instruction states only the end-state contract (behave exactly like GNU ed 1.19, byte-identical stdout, correct exit status, correct file state) and does not prescribe implementation steps or specific tools; verification is purely output/behavior comparison against the real ed binary, not process-based.
✅ pass - anti_cheat_robustness: The real ed binary and all test corpora live only in the verifier image (tests/Dockerfile); the agent image never contains ed or expected outputs. The ed binary is additionally chmod 700'd before the candidate runs, and a purpose-built launcher (guard.py) with an audit hook blocks subprocess/exec/ctypes/native-code/foreign-import shortcuts, with 10 dedicated adversarial probe programs verifying the guard cannot be bypassed even via C-helper reimport, GC introspection, or global rebinding.
✅ pass - task_security: No credential access, network exfiltration, obfuscated payloads, or host-escape code was found anywhere in environment/, tests/, or solution/. The guardcheck probe scripts intentionally attempt sandbox-escape techniques (fork/exec, ctypes, sqlite extension loading) but these run only inside the isolated verifier container against the launcher itself, purely to validate the anti-cheat guard, and are not malicious.
✅ pass - functional_verification: Tests execute the candidate program directly (via the launcher) and the real ed binary, then compare actual stdout, exit status, and on-disk file state — not source-code string/keyword matching. scope.py performs static text analysis only on the test corpus itself (to keep cases in-domain), not on the candidate's implementation.
✅ pass - deterministic_reproducible: Base images are pinned by sha256 digest identically in both Dockerfiles; pytest/pytest-json-ctrf are version-pinned; generated.py uses a fixed seed so the 640 generated scripts are identical on every run; apt packages (ed) are appropriately left unpinned per guidance since apt mirrors don't retain historical versions. No live/mutable external services are used at verify time.
✅ pass - essential_difficulty: The hard part is genuinely semantic (undo bookkeeping, POSIX regex matching order, global-command active-list semantics, substitution edge cases) rather than output-formatting minutiae; byte-for-byte output matching is inherent to the domain (replicating an existing tool's exact behavior), not an artificial precision requirement layered on top of a separate task.
✅ pass - test_instruction_alignment: Every command/option/regex-construct listed in the instruction has a corresponding case family (addresses, append_insert_change, substitute, global_commands, undo, regex/regex_extended, files_and_write, errors_and_exit, options, print_list_number, mixed_scripts) and the excluded commands/options/escapes are enforced via scope.py, matching the instruction's stated scope exactly; no test introduces behavior outside what the instruction describes.
✅ pass - novel: While 'implement an ed clone' concept exists in various forms online, exact byte-level replication of GNU ed 1.19's specific undocumented quirks (the 22-item errata list, e.g. zero-length-match-with-g rules, m accepting the range's last line, s-with-no-final-delimiter behavior inside g-lists) is not something reproducible from generic training-corpus memorization.
✅ pass - agentic: The agent must explore a 796-line manual and errata document, iteratively write and debug a ~1400-line stateful program and a regex engine, and self-test without any oracle available at runtime (network is disabled and ed is not installed in the agent image) — this requires sustained multi-step file editing, testing, and debugging, not a single-shot generation.
✅ pass - reviewable: Ground truth is not hardcoded anywhere; every expected result is produced by running the actual GNU ed 1.19 binary at verify time, so a reviewer can independently install ed and check any case script by hand, making the task exceptionally reviewable despite its specialized domain.
✅ pass - instruction_concision: The instruction is short, uses absolute paths (/app/pyed/ed.py, /app/docs/ed.txt), states the end-state contract without prescribing implementation steps, and contains no roleplay, fluff, or unnecessary headings; it reads as carefully hand-written domain prose rather than generated boilerplate.
✅ pass - solution_quality: The solution is a genuine from-scratch implementation (line-node buffer with undo stack, a compiled regex-matching engine) rather than echoed/hardcoded answers, and the large files (ed.py, posixre.py) are kept as separate files under solution/ rather than inlined as heredocs in solve.sh, which itself is a short, readable script.
✅ pass - separate_verifier_configured: The only artifact the verifier needs (/app/pyed/ed.py) is declared in task.toml's artifacts; all verifier tooling (pytest, pytest-json-ctrf, ed, the guard launcher package) is baked into tests/Dockerfile with no runtime installs in test.sh; the shared base-image digest is byte-identical across environment/Dockerfile and tests/Dockerfile.
✅ pass - environment_hygiene: environment/Dockerfile only copies app/ (the manual, errata, and stub ed.py) and installs generic terminal tooling (tmux/asciinema/patch/ca-certificates), with no tests/solution content or test-only dependencies (pytest, ctrf) baked in; tests/Dockerfile owns all verifier-only dependencies and pre-creates artifact directories; both Dockerfiles perform apt-get update before install and rm -rf /var/lib/apt/lists/* after.
➖ not_applicable - structured_data_schema: The task's output is plain stdout text and file contents compared byte-for-byte against a real reference program, not a structured schema (JSON/CSV/API) requiring a normative spec document.
✅ pass - typos: No typos were found in filenames, paths, commands, or identifiers across instruction.md, task.toml, the Dockerfiles, test scripts, or solution files during inspection; naming is consistent (e.g., ENTRY/GUARD/GUARDCHECK paths match actual copied locations).
✅ pass - difficulty_explanation_quality: The difficulty_explanation is detailed and concrete, describing specific reasoning challenges (address/mark semantics, undo-of-undo, global active lists, POSIX leftmost-longest matching, error/exit-status rules) for both agents and humans, and notes the corpus is task-specific with ground truth from running real ed rather than being stored — it avoids vague or pass-rate-based framing.
✅ pass - solution_explanation_quality: The solution_explanation accurately summarizes the two-file architecture (posixre.py's depth-first pattern-matching program, ed.py's linked-list buffer with an undo stack) and is congruent with the actual solution files inspected; it explains the key design insight (why undo/marks/global-lists behave correctly) without being a step-by-step walkthrough.
✅ pass - verification_explanation_quality: The verification_explanation precisely describes the committed+generated case corpus, the roster/fixture consistency checks, scope.py's domain enforcement, the oracle-vs-candidate comparison (stdout, exit status, file tree), and the launcher's anti-cheat mechanics — all of which match what was found in test_outputs.py, generated.py, scope.py, and guard.py exactly.
✅ pass - category_and_tags: category = 'Software' correctly reflects the domain (reimplementing a command-line tool); subcategory = 'Languages' is a reasonable fit given the task centers on parsing a command language and a regex engine; tags (gnu-ed, line-editor, posix-regex, undo, reimplementation) are specific and directly descriptive rather than generic.
✅ pass - no_extraneous_files: Every file traced back to a purpose: docs/ed.txt and ed-errata.txt are referenced by the instruction, all tests/cases/*.jsonl files are referenced by roster.json and loaded by test_outputs.py, all guardcheck/guardvendor probes are referenced by test_launcher_stops_delegation_and_foreign_code, and solution/ files are used by solve.sh; the small README.md is a reasonable scaffold doc for the shipped package.
✅ pass - verifier_execution_isolation: Candidate code is always executed via setpriv --reuid=65534 (unprivileged) through the guard.py launcher, never as root; /logs/verifier and /tests are chmod 700 and the oracle ed binary is chmod 700 before any candidate code runs; the root test.sh/pytest process derives the reward from the demoted subprocess's return code/output rather than letting candidate code write it, and dedicated adversarial probes (fork_exec reimport, GC reachability, global tampering, execv self-replacement) validate the isolation holds.
✅ pass - ctrf_reporting: test.sh invokes pytest with `--ctrf /logs/verifier/ctrf.json` directly against test_outputs.py, matching the required per-test CTRF reporting pattern.
➖ not_applicable - do_not_modify_enforced: The instruction does not direct the agent to preserve or avoid modifying any specific concrete artifact (docs are reference material to read, not files whose immutability is asserted); no such constraint exists to enforce.
✅ pass - binary_reward: test.sh only ever writes literal 0 or 1 to /logs/verifier/reward.txt (initialized to 0, then set to 1 iff the pytest exit code is 0, else 0); no fractional, weighted, or clamped score is ever written on any reachable path.

## Blocking Quality Gates
✅ PASS - verifiable
✅ PASS - solvable
✅ PASS - outcome_verified
✅ PASS - anti_cheat_robustness
✅ PASS - task_security
✅ PASS - functional_verification
✅ PASS - deterministic_reproducible
✅ PASS - test_instruction_alignment
✅ PASS - agentic
✅ PASS - separate_verifier_configured
✅ PASS - environment_hygiene
✅ PASS - structured_data_schema
✅ PASS - typos
✅ PASS - category_and_tags
✅ PASS - no_extraneous_files
✅ PASS - verifier_execution_isolation
✅ PASS - ctrf_reporting
✅ PASS - do_not_modify_enforced
✅ PASS - binary_reward
```

### Quality Check Logs

```
## Quality Check Results
✅ pass - verifiable: The verifier (tests/test_outputs.py + guard.py + generated.py + scope.py) is fully programmatic: it runs the candidate's ed.py and the real GNU ed 1.19 binary on identical fixtures and diff-checks stdout, exit status, and the resulting file tree byte-for-byte. No LLM-as-judge, no subjective grading. It runs entirely offline (no-network verifier), with a fixed random seed for generated cases, so re-runs are deterministic. test.sh performs no runtime installs (pytest/ed are baked into tests/Dockerfile).
✅ pass - solvable: A complete working solution is provided (solution/pyed/ed.py, 1442 lines; solution/pyed/posixre.py, 476 lines) implementing the full editor and a POSIX leftmost-longest regex engine, installed via solve.sh. The task declares expert_time_estimate_hours = 8, i.e. roughly a single expert workday rather than a multi-day/team effort, and the manual plus errata document are provided so an expert does not need to discover the spec from scratch.
✅ pass - difficult: Reimplementing GNU ed exactly (undo/redo stack semantics, global-command active lists, mark invalidation, POSIX BRE/ERE leftmost-longest matching with backreferences and bounded repeats, substitution edge cases, and 22 documented deviations from the manual) requires genuine systems/regex-engine expertise well beyond an average undergraduate project; this is reflected in the detailed errata list and the fact that memory-based reimplementations reliably get subtle cases wrong.
✅ pass - interesting: The instruction motivates the task with a realistic scenario (porting maintenance scripts that pipe commands into ed onto minimal images lacking ed), and reimplementing standard Unix tools for constrained/embedded environments is genuine professional work (e.g., BusyBox-style utilities, embedded Linux teams).
✅ pass - outcome_verified: Instruction states only the end-state contract (behave exactly like GNU ed 1.19, byte-identical stdout, correct exit status, correct file state) and does not prescribe implementation steps or specific tools; verification is purely output/behavior comparison against the real ed binary, not process-based.
✅ pass - anti_cheat_robustness: The real ed binary and all test corpora live only in the verifier image (tests/Dockerfile); the agent image never contains ed or expected outputs. The ed binary is additionally chmod 700'd before the candidate runs, and a purpose-built launcher (guard.py) with an audit hook blocks subprocess/exec/ctypes/native-code/foreign-import shortcuts, with 10 dedicated adversarial probe programs verifying the guard cannot be bypassed even via C-helper reimport, GC introspection, or global rebinding.
✅ pass - task_security: No credential access, network exfiltration, obfuscated payloads, or host-escape code was found anywhere in environment/, tests/, or solution/. The guardcheck probe scripts intentionally attempt sandbox-escape techniques (fork/exec, ctypes, sqlite extension loading) but these run only inside the isolated verifier container against the launcher itself, purely to validate the anti-cheat guard, and are not malicious.
✅ pass - functional_verification: Tests execute the candidate program directly (via the launcher) and the real ed binary, then compare actual stdout, exit status, and on-disk file state — not source-code string/keyword matching. scope.py performs static text analysis only on the test corpus itself (to keep cases in-domain), not on the candidate's implementation.
✅ pass - deterministic_reproducible: Base images are pinned by sha256 digest identically in both Dockerfiles; pytest/pytest-json-ctrf are version-pinned; generated.py uses a fixed seed so the 640 generated scripts are identical on every run; apt packages (ed) are appropriately left unpinned per guidance since apt mirrors don't retain historical versions. No live/mutable external services are used at verify time.
✅ pass - essential_difficulty: The hard part is genuinely semantic (undo bookkeeping, POSIX regex matching order, global-command active-list semantics, substitution edge cases) rather than output-formatting minutiae; byte-for-byte output matching is inherent to the domain (replicating an existing tool's exact behavior), not an artificial precision requirement layered on top of a separate task.
✅ pass - test_instruction_alignment: Every command/option/regex-construct listed in the instruction has a corresponding case family (addresses, append_insert_change, substitute, global_commands, undo, regex/regex_extended, files_and_write, errors_and_exit, options, print_list_number, mixed_scripts) and the excluded commands/options/escapes are enforced via scope.py, matching the instruction's stated scope exactly; no test introduces behavior outside what the instruction describes.
✅ pass - novel: While 'implement an ed clone' concept exists in various forms online, exact byte-level replication of GNU ed 1.19's specific undocumented quirks (the 22-item errata list, e.g. zero-length-match-with-g rules, m accepting the range's last line, s-with-no-final-delimiter behavior inside g-lists) is not something reproducible from generic training-corpus memorization.
✅ pass - agentic: The agent must explore a 796-line manual and errata document, iteratively write and debug a ~1400-line stateful program and a regex engine, and self-test without any oracle available at runtime (network is disabled and ed is not installed in the agent image) — this requires sustained multi-step file editing, testing, and debugging, not a single-shot generation.
✅ pass - reviewable: Ground truth is not hardcoded anywhere; every expected result is produced by running the actual GNU ed 1.19 binary at verify time, so a reviewer can independently install ed and check any case script by hand, making the task exceptionally reviewable despite its specialized domain.
✅ pass - instruction_concision: The instruction is short, uses absolute paths (/app/pyed/ed.py, /app/docs/ed.txt), states the end-state contract without prescribing implementation steps, and contains no roleplay, fluff, or unnecessary headings; it reads as carefully hand-written domain prose rather than generated boilerplate.
✅ pass - solution_quality: The solution is a genuine from-scratch implementation (line-node buffer with undo stack, a compiled regex-matching engine) rather than echoed/hardcoded answers, and the large files (ed.py, posixre.py) are kept as separate files under solution/ rather than inlined as heredocs in solve.sh, which itself is a short, readable script.
✅ pass - separate_verifier_configured: The only artifact the verifier needs (/app/pyed/ed.py) is declared in task.toml's artifacts; all verifier tooling (pytest, pytest-json-ctrf, ed, the guard launcher package) is baked into tests/Dockerfile with no runtime installs in test.sh; the shared base-image digest is byte-identical across environment/Dockerfile and tests/Dockerfile.
✅ pass - environment_hygiene: environment/Dockerfile only copies app/ (the manual, errata, and stub ed.py) and installs generic terminal tooling (tmux/asciinema/patch/ca-certificates), with no tests/solution content or test-only dependencies (pytest, ctrf) baked in; tests/Dockerfile owns all verifier-only dependencies and pre-creates artifact directories; both Dockerfiles perform apt-get update before install and rm -rf /var/lib/apt/lists/* after.
➖ not_applicable - structured_data_schema: The task's output is plain stdout text and file contents compared byte-for-byte against a real reference program, not a structured schema (JSON/CSV/API) requiring a normative spec document.
✅ pass - typos: No typos were found in filenames, paths, commands, or identifiers across instruction.md, task.toml, the Dockerfiles, test scripts, or solution files during inspection; naming is consistent (e.g., ENTRY/GUARD/GUARDCHECK paths match actual copied locations).
✅ pass - difficulty_explanation_quality: The difficulty_explanation is detailed and concrete, describing specific reasoning challenges (address/mark semantics, undo-of-undo, global active lists, POSIX leftmost-longest matching, error/exit-status rules) for both agents and humans, and notes the corpus is task-specific with ground truth from running real ed rather than being stored — it avoids vague or pass-rate-based framing.
✅ pass - solution_explanation_quality: The solution_explanation accurately summarizes the two-file architecture (posixre.py's depth-first pattern-matching program, ed.py's linked-list buffer with an undo stack) and is congruent with the actual solution files inspected; it explains the key design insight (why undo/marks/global-lists behave correctly) without being a step-by-step walkthrough.
✅ pass - verification_explanation_quality: The verification_explanation precisely describes the committed+generated case corpus, the roster/fixture consistency checks, scope.py's domain enforcement, the oracle-vs-candidate comparison (stdout, exit status, file tree), and the launcher's anti-cheat mechanics — all of which match what was found in test_outputs.py, generated.py, scope.py, and guard.py exactly.
✅ pass - category_and_tags: category = 'Software' correctly reflects the domain (reimplementing a command-line tool); subcategory = 'Languages' is a reasonable fit given the task centers on parsing a command language and a regex engine; tags (gnu-ed, line-editor, posix-regex, undo, reimplementation) are specific and directly descriptive rather than generic.
✅ pass - no_extraneous_files: Every file traced back to a purpose: docs/ed.txt and ed-errata.txt are referenced by the instruction, all tests/cases/*.jsonl files are referenced by roster.json and loaded by test_outputs.py, all guardcheck/guardvendor probes are referenced by test_launcher_stops_delegation_and_foreign_code, and solution/ files are used by solve.sh; the small README.md is a reasonable scaffold doc for the shipped package.
✅ pass - verifier_execution_isolation: Candidate code is always executed via setpriv --reuid=65534 (unprivileged) through the guard.py launcher, never as root; /logs/verifier and /tests are chmod 700 and the oracle ed binary is chmod 700 before any candidate code runs; the root test.sh/pytest process derives the reward from the demoted subprocess's return code/output rather than letting candidate code write it, and dedicated adversarial probes (fork_exec reimport, GC reachability, global tampering, execv self-replacement) validate the isolation holds.
✅ pass - ctrf_reporting: test.sh invokes pytest with `--ctrf /logs/verifier/ctrf.json` directly against test_outputs.py, matching the required per-test CTRF reporting pattern.
➖ not_applicable - do_not_modify_enforced: The instruction does not direct the agent to preserve or avoid modifying any specific concrete artifact (docs are reference material to read, not files whose immutability is asserted); no such constraint exists to enforce.
✅ pass - binary_reward: test.sh only ever writes literal 0 or 1 to /logs/verifier/reward.txt (initialized to 0, then set to 1 iff the pytest exit code is 0, else 0); no fractional, weighted, or clamped score is ever written on any reachable path.

## Blocking Quality Gates
✅ PASS - verifiable
✅ PASS - solvable
✅ PASS - outcome_verified
✅ PASS - anti_cheat_robustness
✅ PASS - task_security
✅ PASS - functional_verification
✅ PASS - deterministic_reproducible
✅ PASS - test_instruction_alignment
✅ PASS - agentic
✅ PASS - separate_verifier_configured
✅ PASS - environment_hygiene
✅ PASS - structured_data_schema
✅ PASS - typos
✅ PASS - category_and_tags
✅ PASS - no_extraneous_files
✅ PASS - verifier_execution_isolation
✅ PASS - ctrf_reporting
✅ PASS - do_not_modify_enforced
✅ PASS - binary_reward
```

## 5b. Quality Panel Judge Feedback

### Quality Panel Judge Feedback

```
QUALITY PANEL: NEEDS REVISION -- 14 blocking issues to fix. Details for each are below.

Blocking (fix every one):
   1. [Correct Reference Solution] MAJOR: Bounded-repeat run bookkeeping is reused across search
      starting positions even for patterns with backreferences, suppressing a capture needed by
      the later, leftmost valid match.
   2. [Correct Reference Solution] MAJOR: Successful substitution yanks the deleted
      pre-substitution line instead of copying the last modified replacement line into the cut
      buffer.
   3. [Correct Reference Solution] MAJOR: A bare alternative substitution-repeat command `s` is
      rejected as a malformed new substitution instead of repeating the last substitution.
   4. [Correct Reference Solution] MAJOR: Repeated substitution with r uses any last compiled
      regexp, rather than only a search regexp that occurred after the previous substitution.
   5. [Sound Verifier] MAJOR: No case requires `*`, basic `\+`, or basic `\{N,\}` to match a
      long run, so a plausible fixed repetition cap passes despite changing their open-ended
      semantics.
   6. [Sound Verifier] MAJOR: Global-list coverage omits the supported f FILE command, allowing
      an otherwise functional editor to reject that command only inside g lists.
   7. [Sound Verifier] MAJOR: No case checks that v rejects a nested global command in its
      command list, although v inherits g's prohibition on nested g and v.
   8. [Sound Verifier] MAJOR: No extended-regexp case rejects a repeat whose upper bound exceeds
      32767.
   9. [Correct Reference Solution] MINOR: The address parser caps each numeric offset component
      before evaluating the complete address, potentially rejecting an address whose final value
      is valid.
  10. [Sound Verifier] MINOR: The corpus never uses a valid lowercase mark outside a, b, and x,
      allowing a mark implementation restricted to those letters to pass.
  11. [Sound Verifier] MINOR: The import guard treats any import origin under /app as allowed
      without requiring it to be Python source, so it accepts candidate-supplied Python bytecode
      despite the contract's source-files-only allowance.
  12. [Sound Verifier] MINOR: The corpus has no decimal-address case above line 33, despite the
      contract allowing starting files of a few dozen lines and decimal N through the last line.
  13. [Sound Verifier] MINOR: The generated grammar never exercises a numeric relative offset
      whose magnitude exceeds two, leaving +N/-N support beyond that value unverified.
  14. [Sound Verifier] MINOR: The tests exercise no more than three consecutive bare + or -
      signs, so cumulative bare-offset repetition beyond that is not checked.

Checked and clean: Coherent Contract, Protected Ground Truth, Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Correct Reference Solution] MAJOR
   Bounded-repeat run bookkeeping is reused across search starting positions even for patterns
   with backreferences, suppressing a capture needed by the later, leftmost valid match.
   Why this fails:
     Reach: Start with a file containing `aaab\n` and submit `s/\(a\{1,2\}\)\1b/X/\n,p\nQ\n`
     through a pipe. The contract requires a search to find the leftmost match: none starts at
     byte 0, but starting at byte 1 the group captures `a`, `\1` consumes the next `a`, and `b`
     consumes the last byte. Substitution must produce `aX\n`. At start 0 the reference's
     bounded-repeat instruction offers endpoints 1 and 2 and records them as already offered. At
     start 1 it offers endpoint 3 but suppresses endpoint 2, the one representing capture `a`;
     the endpoint-3 capture `aa` cannot satisfy the backreference. Search therefore reports no
     match. Flip: the reference emits `?\n`, leaves `aaab\n` for `,p`, and exits nonzero instead
     of printing the successful substitution's `aX\n` and exiting zero.
   Where to look: environment/app/docs/ed.txt:509-515, environment/app/docs/ed.txt:446-450,
     solution/pyed/posixre.py:324-333, solution/pyed/posixre.py:426-445,
     solution/pyed/posixre.py:467-476, solution/pyed/posixre.py:501-509

2. [Correct Reference Solution] MAJOR -- core domain and business logic
   Successful substitution yanks the deleted pre-substitution line instead of copying the last
   modified replacement line into the cut buffer.
   Why this fails:
     Reach: run the valid pipe script `a\nabc\n.\ns/b/X/\nx\n,p\nQ\n`. Contractually, s changes
     line 1 to `aXc` and copies that last modified line to the cut buffer, so x after current
     line 1 yields two lines `aXc`, and `,p` prints `aXc\naXc\n`. The reference's
     search_and_replace calls delete_lines(1,1), whose delete_lines first calls yank_lines and
     therefore stores `abc`; it then inserts `aXc` without changing yank. x consequently inserts
     `abc`, and `,p` prints `aXc\nabc\n`. Flip: the required stdout and final buffer differ.
   Where to look: environment/app/docs/ed.txt:897-902, solution/pyed/ed.py:302-313,
     solution/pyed/ed.py:637-655, solution/pyed/ed.py:1304-1313

3. [Correct Reference Solution] MAJOR -- core domain and business logic
   A bare alternative substitution-repeat command `s` is rejected as a malformed new
   substitution instead of repeating the last substitution.
   Why this fails:
     Reach: run the valid pipe script `a\naa\n.\ns/a/b/\ns\np\nQ\n`. The first substitution
     changes `aa` to `ba`; the documented zero-suffix alternative `s` repeats it and changes
     `ba` to `bb`, so p must print `bb\n` with no error. In command_s, the bare newline sets
     sflags to 8, but the code then takes the `else` new-substitution branch rather than the
     repeat branch, calls get_pattern_for_s with newline as delimiter, and fails. It emits `?\n`
     and p prints `ba\n`. Flip: stdout is `?\nba\n` rather than `bb\n`, and the buffer differs.
   Where to look: environment/app/docs/ed.txt:923-933, solution/pyed/ed.py:1029-1089,
     solution/pyed/ed.py:1265-1267, solution/pyed/ed.py:1411-1420

4. [Correct Reference Solution] MAJOR -- core domain and business logic
   Repeated substitution with r uses any last compiled regexp, rather than only a search regexp
   that occurred after the previous substitution.
   Why this fails:
     Reach: with pipe stdin, run the contract-valid script `a\na\n.\ns/a/aa/\nsr\np\nQ\n`. The
     first substitution changes `a` to `aa`; no address search has occurred after it. The
     contract says r uses the last search RE only if that search happened after the
     substitution, so `sr` must fail, producing `?\n`; `p` then prints `aa\n`, and absent -l the
     exit status is nonzero. Flip: at lines 1058-1081 the reference merely tests that
     last_regexp is non-null. The preceding substitution compiled `a` and stored it as
     last_regexp (lines 430-437 and 1107), so `sr` succeeds and replaces the first `a` in `aa`
     with the prior replacement `aa`, leaving `aaa`; `p` emits `aaa\n` and Q exits zero. This
     differs in stdout, buffer result, and exit status.
   Where to look: environment/app/docs/ed.txt:923-934, solution/pyed/ed.py:430-437,
     solution/pyed/ed.py:1058-1081, solution/pyed/ed.py:1106-1112

5. [Sound Verifier] MAJOR -- missing behavioral coverage
   No case requires `*`, basic `\+`, or basic `\{N,\}` to match a long run, so a plausible fixed
   repetition cap passes despite changing their open-ended semantics.
   Why this fails:
     Reach: A contract-legal pipe script `a\n` followed by 100 `a` characters and
     `\n.\ns/a*/X/p\nQ\n` has a 100-byte input line. GNU ed prints `X\n`. Equivalent scripts
     using `s/a\+/X/p` or `s/a\{1,\}/X/p` require the same 100-character match. Flip: A regex
     implementation that caps open-ended repetitions at 64 matches only 64 characters and prints
     `X` followed by 36 `a` characters and a newline. It can still compile the 32767-count
     patterns in regex.jsonl:66-69, whose short fixture does not require matching 32767
     characters, and handle the short repeated matches in regex.jsonl:72-74. The generated
     source lines are drawn from the short table at generated.py:22-27. The verifier's equality
     comparison would reject this implementation on the proposed input, but none of those shown
     cases supplies it.
   Where to look: instruction.md:7-10, tests/cases/regex.jsonl:66-69,
     tests/cases/regex.jsonl:72-74, tests/generated.py:22-27, tests/generated.py:183-185,
     tests/test_outputs.py:170-179

6. [Sound Verifier] MAJOR -- missing behavioral coverage
   Global-list coverage omits the supported f FILE command, allowing an otherwise functional
   editor to reject that command only inside g lists.
   Why this fails:
     Reach: The contract-legal pipe script `a\nx\n.\ng/x/f target\nf\nQ\n`, starting with no
     files, distinguishes the behavior. GNU ed's global f sets and prints `target`; the
     following bare f prints `target` again. Flip: An implementation with working ordinary f but
     a global-list dispatcher limited to the commands exercised by the corpus rejects `f target`
     in the list, producing a `?` instead of the first `target\n`. The committed global cases
     and mixed scripts shown do not invoke global f, and the generated G_LISTS table has no f
     entry, so that omission clears their comparisons while failing this permitted script.
   Where to look: environment/app/docs/ed.txt:651-653, environment/app/docs/ed.txt:668-675,
     tests/generated.py:59-61, tests/test_outputs.py:165-179

7. [Sound Verifier] MAJOR -- missing behavioral coverage
   No case checks that v rejects a nested global command in its command list, although v
   inherits g's prohibition on nested g and v.
   Why this fails:
     Reach: With an empty starting buffer and pipe stdin, the contract-legal script
     `a\nx\n.\nv/nomatch/g/x/p\nQ\n` selects `x` for v, then attempts a forbidden nested g. GNU
     ed emits `?\n`; a v handler that executes the nested g instead also prints `x\n`. Flip:
     That handler can implement the other rules normally and pass the shown nested-global
     checks, which are `g/a/g/a/p` and `g/a/v/a/p`, while producing different stdout on this
     input. The generated command-list table contains no nested g or v, so its v draws do not
     supply the missing check.
   Where to look: environment/app/docs/ed.txt:668-677, environment/app/docs/ed.txt:787-789,
     tests/cases/global_commands.jsonl:24-25, tests/generated.py:59-61,
     tests/generated.py:168-174, tests/test_outputs.py:165-179

8. [Sound Verifier] MAJOR -- missing behavioral coverage
   No extended-regexp case rejects a repeat whose upper bound exceeds 32767.
   Why this fails:
     Reach: With a starting file containing `z\n`, run `-E` and `g/y{0,32768}|z/p\nQ\n`; the
     upper bound makes the expression invalid under the stated GNU rule. Flip: A plausible
     implementation with separate BRE and ERE repeat parsers that validates both BRE bounds but
     only the ERE lower bound would print `z\n` instead of the reference error notification. It
     clears the committed boundary cases: the basic tests check upper bounds, while the extended
     test checks `{32768,}` and `{32767,}`. The generated ERE pattern table contains no large
     upper bound.
   Where to look: environment/app/docs/ed-errata.txt:51-52, tests/cases/regex.jsonl:66-69,
     tests/cases/regex_extended.jsonl:16, tests/generated.py:43-45

9. [Correct Reference Solution] MINOR -- Input validation and contract-bound behavior
   The address parser caps each numeric offset component before evaluating the complete address,
   potentially rejecting an address whose final value is valid.
   Why this fails:
     Reach: unverified—the contract permits intermediate address values beyond the last line.
     With a one-line buffer, `0+2147483648-2147483648=` has final address 0, but parse_int
     rejects its first offset at 2147483648, before the subtraction. Flip: if GNU ed accepts
     that component, it prints `0\n`, whereas the reference prints `?\n` and records a failure.
     GNU ed's disposition for this oversized component was not independently established.
   Where to look: environment/app/docs/ed.txt:415-430, solution/pyed/ed.py:818-835,
     solution/pyed/ed.py:843-866, solution/pyed/ed.py:1412-1414

10. [Sound Verifier] MINOR -- missing behavioral coverage
   The corpus never uses a valid lowercase mark outside a, b, and x, allowing a mark
   implementation restricted to those letters to pass.
   Why this fails:
     Reach: A contract-legal regular-file-stdin case starts with f.txt containing `a\n` and uses
     `1kc\n'cs/a/b/\nw out\nQ\n` with `-s f.txt`. GNU ed accepts mark c, leaves out containing
     `b\n`, emits no stdout, and exits zero. Flip: An otherwise correct implementation that
     rejects marks outside a, b, and x emits `?\n` at `1kc` and stops on regular-file stdin,
     leaving no out file and exiting nonzero. It clears the shown mark cases, which use only
     those three letters, and the generator's k branch, which chooses only a or b. This exact
     restricted set is verifier-tailored, hence Minor.
   Where to look: environment/app/docs/ed.txt:409-412, tests/generated.py:156-157,
     tests/cases/addresses.jsonl:81-83, tests/test_outputs.py:159, tests/test_outputs.py:165-179

11. [Sound Verifier] MINOR -- build, dependency, or interface enforcement mismatch
   The import guard treats any import origin under /app as allowed without requiring it to be
   Python source, so it accepts candidate-supplied Python bytecode despite the contract's
   source-files-only allowance.
   Why this fails:
     Reach: a submission can leave /app/pyed/ed.py as source but have it import
     /app/pyed/implementation.pyc, a legacy bytecode module produced during image construction
     and containing the editor implementation. On the first graded run the import warden
     resolves that origin under its own-tree prefix and returns it as permitted at
     guard.py:103-105; it does not inspect the suffix. Flip: the .pyc implementation can emit
     exactly GNU ed's output, status, and filesystem state, so every test_outputs.py:171-179
     comparison passes, although importing a .pyc is not importing a Python source file as O24
     requires. This construction requires knowledge of the guard's prefix-only rule rather than
     being an ordinary source-based submission, hence Minor.
   Where to look: tests/guard.py:97-113, tests/guard.py:123-133, tests/test_outputs.py:165-179

12. [Sound Verifier] MINOR -- missing behavioral coverage
   The corpus has no decimal-address case above line 33, despite the contract allowing starting
   files of a few dozen lines and decimal N through the last line.
   Why this fails:
     Reach: the complete fixture table's largest starting buffer is big_03 with 33 lines, and
     generated buffers have only 2-14 lines. A contract-legal fixture containing 34
     newline-terminated ASCII lines with script `34p\n` would require decimal address 34. Flip:
     an implementation that rejects line numbers above 33 (or caps its buffer at 33) matches
     every graded fixture and generated buffer, hence clears the tuple equality at
     tests/test_outputs.py:171-179, but emits `?` rather than GNU ed's 34th line on that input.
     This exact cap is verifier-aware, so the finding is Minor.
   Where to look: tests/cases/fixtures.json:14-18, tests/generated.py:183-185,
     tests/test_outputs.py:171-179

13. [Sound Verifier] MINOR -- missing behavioral coverage
   The generated grammar never exercises a numeric relative offset whose magnitude exceeds two,
   leaving +N/-N support beyond that value unverified.
   Why this fails:
     Reach: `ATOMS` contains only literal `+2` and `-2`, and `OFFSETS` contains only `+1` and
     `-1` in addition to bare signs. A legal four-line input with current line 1 and script
     `1+3p\n` distinguishes an implementation that parses only magnitudes 0, 1, and 2. Flip:
     that implementation behaves identically on all generated forms and the displayed committed
     cases, so it clears the GNU tuple comparison, but rejects or misaddresses `+3` where GNU
     prints line 4. Choosing this boundary requires knowledge of this grammar table, making it
     Minor.
   Where to look: tests/generated.py:29-34, tests/generated.py:95-110,
     tests/test_outputs.py:171-179

14. [Sound Verifier] MINOR -- missing behavioral coverage
   The tests exercise no more than three consecutive bare + or - signs, so cumulative
   bare-offset repetition beyond that is not checked.
   Why this fails:
     Reach: an address parser that accepts one, two, and three bare signs but rejects a fourth
     passes the generator: its atom is at most `++`/`--`, followed by at most one optional bare
     sign. On a valid five-line buffer, `1++++p\n` must print line 5. Flip: the capped parser
     clears all generated and committed cases but gives GNU-incompatible failure/output for that
     distinguishing input. The three-sign cap is tailored to the visible generator, so this is
     Minor.
   Where to look: tests/generated.py:30-34, tests/generated.py:109-121,
     tests/test_outputs.py:171-179
```

## 5c. Oracle / NOP Validation

### Oracle / NOP Validation

```

```

### Difficulty Check Full Logs

```

```

## 6. Test Quality Report

### Test Quality Judge Report

```

```

## 7. TB 3.0 Rubric Feedback Checks

### TB 3.0 Rubric Feedback Checks

```

```

## 8. Agent Review Report

### Agent Review

```

```

## 9. CI & Static Checks

### CI Checks Summary

```

```

**Fast static checks:** status = `success`

- **AutoEval Execution Summary** — passed: `true` (codebuild)
  - AutoEval execution succeeded. Build status: SUCCEEDED. Build ID: CodeExecutionEnvironment:60a01e14-4b1d-4a69-b7f9-e36eb44bd562.

## 10. Evaluation Rubrics

### test_rubrics

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

## 10b. Automated Feedback

| Field | Value |
|---|---|
| Eval revision notes | `Agent Runner Summary: Evaluation FAILED. Pre-difficulty quality or quality panel gate failed; difficulty not run` |
| Eval revision requested at | `2026-09-27T15:45:00.018031Z` |
| Rebuttal notes | `` |

### Evaluation History (oldest first)

| # | Created | Outcome | Blocking stage | Stages |
|---|---|---|---|---|
| 1 | `2026-09-27T07:24:02.560087Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 2 | `2026-09-27T15:11:46.348480Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |

## 11. Reviewer Decision

| Field | Value |
|---|---|
| Submission Review Decision | **—** |

### Revision Notes

_(none)_

---

_Generated by TB Task Revise Extractor from the Snorkel Experts task payload._
