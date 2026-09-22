# Quality Panel Appendix — Worked examples

Companion to the [Quality Panel Judge Guide](/portal/docs/testing-and-validation/quality-panel-judge-guide).

These are **synthetic composites of realistic task patterns**, not excerpts from submitted tasks or results from executed reviews. Snippets are abbreviated to show the decisive behavior. Labels describe the stated scenario; a finding on your task needs evidence from your own package.

Start with the requirement, identify the exact input or code path that exposes the defect, then check the repair in both directions: valid work must pass and the specific wrong behavior must fail. A reference solution passing once does not establish complete coverage or reproducibility.

In the current panel, `Minor` and `Major` block on the contract, reference, verifier, and deterministic-execution axes. For `protected_ground_truth`, only `Major` blocks; a `Minor` alone does not. An explicitly `Advisory` partial-coverage observation does not block. See the guide for [how results are combined](/portal/docs/testing-and-validation/quality-panel-judge-guide#how-the-review-works).

| Find an example for… | Go to |
|---|---|
| Unclear requirements, hidden rules, or broken instructions | [A — Contract](#a--contract) |
| A reference solution that gets a format or state transition wrong | [B — Reference solution](#b--reference) |
| Exposed answers, accepting wrong work, or rejecting valid work | [C — Verifier and environment](#c--verifier) |
| Grading that changes between runs | [D — Deterministic execution](#d--deterministic-execution) |
| A useful revision note or evidence-backed disagreement | [E — Responding to a review](#e--responding-to-a-review) |

---

<h2 id="a--contract">A — Contract</h2>

### A-1 — Broken render in Required outputs

*`coherent_contract` · Major*

**Task.** Build a CLI that produces a reconciliation report. The rendered instructions instead list these deliverables:

```markdown
## Required outputs

- `/app/tool'`
- `/app/'error_codes': ['internal.test.id']}`
```

**Evidence and impact.** The verifier invokes `/app/tool` and reads `/app/report.json`. Neither exact path is correctly disclosed: one contains a stray quote, and the other is a serialized Python object. The candidate cannot recover the required interface from this list.

**Repair and check.** Fix the generated text to name the actual tool and report. Open the rendered instructions, then compare each required path with its invocation or read in the verifier. Correct the generation source too, so the next export preserves the repair.

---

### A-2 — Verifier sentinel listed as a required output

*`coherent_contract` · Major*

**Task.** A report CLI must reject a nonexistent input. The instructions accidentally require the candidate to create `/definitely/missing/input.json` alongside `/app/report.json`.

```python
result = run_cli("solve", "--input", "/definitely/missing/input.json")
assert result.returncode != 0  # assumes the path does not exist
```

**Evidence and impact.** In this example, the declared artifacts include that input path. Obeying the instructions makes it exist during grading, so the test no longer checks the condition it claims to check.

**Repair and check.** Remove the sentinel from required outputs. Create the missing-file probe under a fresh verifier-owned temporary directory and assert it is absent before invoking the CLI. Confirm that a real input succeeds and the absent input produces the documented error.

---

### A-3 — An edge the contract allows but never defines

*`coherent_contract` · Minor in the scenario below*

**Task.** Summarize an event ledger. The instructions say, “A group whose records are all deleted is not a group of the output,” and define `min_time` as the earliest record time. They do not say whether deleted records contribute to the overall time range.

**Concrete ambiguity.** Group A has a deleted record at `09:00`; group B has a surviving record at `10:00`. One implementation reports `min_time = 09:00` over all records; another reports `10:00` over surviving records. The contract never resolves that choice.

**Why this label.** Assume all shipped graded fixtures contain only surviving records. The ambiguity is real, but it has not been shown to change a graded answer, so this is `Minor`. If the verifier grades the mixed case and silently requires one interpretation, that supports `Major`.

**Repair and check.** State, “Deleted records do not contribute to output groups or to `min_time`/`max_time`; if no records survive, both fields are `null`.” Add a mixed fixture and an all-deleted fixture with hand-calculated expectations. A contract-axis `Minor` still blocks.

---

### A-4 — A payment tie-break rule exists only in the verifier

*`coherent_contract` · Major*

**Task.** Reconstruct account balances by applying ledger events “in timestamp order.” The verifier additionally sorts equal timestamps by ascending `sequence`, but the candidate-visible instructions never mention that rule.

| Event | Timestamp | Sequence | Action |
|---|---|---|---|
| A, first in the input file | `12:00:00` | 20 | Set balance to 100 |
| B, second in the input file | `12:00:00` | 10 | Add 5 |

**Evidence and impact.** Starting at zero, input order produces `105`; sequence order produces `100`. Both follow “timestamp order.” A graded fixture expects `100`, so an otherwise reasonable implementation can fail on an undisclosed rule.

**Repair.** Disclose the full order: “Apply events by ascending `(timestamp, sequence, original input position)`.” If the task intends a different rule, use it consistently in the contract, reference, and verifier.

**Check.** Keep the equal-timestamp fixture: distinct timestamps cannot exercise this rule. Verify the reference produces `100` and a timestamp-only implementation produces `105` and fails. Also include equal timestamp/sequence values if input position is the final tie-break.

---

<h2 id="b--reference">B — Reference solution</h2>

### B-1 — Documented field width, copied through unpadded

*`correct_reference_solution` · Major*

**Task.** Export a fixed-width banking file. Field 14 must contain eleven digits, left-padded with zeroes.

**Evidence and impact.** The source value is `1234567890`. The reference copies those ten bytes directly, although the documented result is `01234567890`. Every supplied row takes this path. Goldens generated from that reference therefore reject correctly padded output if the verifier compares them byte for byte.

**Repair and check.** Pad the field when serializing and regenerate affected goldens. Inspect actual output bytes and assert both the value and `len(field) == 11`. Include a short value and an already eleven-digit value. A passing old golden comparison would only show that two files share the same mistake.

---

### B-2 — Minimum significant digits lost to the format string

*`correct_reference_solution` · Major*

**Task.** Export nonzero measurement values with at least twelve significant digits. The reference uses `printf("%.12g", v)`, which emits `1.5` for `v = 1.5`.

**Evidence and impact.** `%g` limits significant digits but removes trailing zeroes; it does not guarantee a minimum. An ordinary allowed value therefore violates the explicit output requirement. A verifier that checks only numerical tolerance would miss this defect; a passing Oracle would not make the reference correct against the contract.

**Repair and check.** If scientific notation is allowed, `%.11e` supplies twelve significant digits, for example `1.50000000000e+00`. Check actual strings for small, large, and negative values; define and test zero separately. Do not introduce a notation the contract forbids.

---

### B-3 — Loop-carried state refreshed on only one branch

*`correct_reference_solution` · Major*

**Task.** A warehouse tracker reports how long a pallet has continuously occupied its current zone. Every zone change resets its entry time.

```python
if current_zone is None:
    current_zone = observed_zone
    entered_at = now
elif observed_zone != current_zone:
    current_zone = observed_zone
    # BUG: entered_at still belongs to the previous zone
return now - entered_at
```

**Trace.** The pallet enters A at minute 0, B at minute 10, and C at minute 20. At minute 25, the correct C dwell time is `5`; this code reports `25`. A test that observes only one zone misses the defect.

**Repair and check.** Set `entered_at = now` on every actual zone change. Trace A → B → C and assert `0` at each entry and `5` at minute 25. Check that another observation in the same zone does **not** reset the clock. Together these distinguish a proper reset from a fix that resets on every observation.

---

<h2 id="c--verifier">C — Verifier and environment</h2>

For answer-exposure findings, establish the complete path: what candidate-controlled bytes survive staging, what the grader reads or executes, and how that earns credit. A sealed golden, unused writable directory, or suspicious API call alone does not establish an exploit.

### C-1 — Privileged read of a candidate-written path, no symlink guard

*`protected_ground_truth` · Major · `chmod_follow`*

**Task and setup.** The candidate must write a calculated report to `/app/out/result.json`. In this example, staging preserves symlinks, the candidate-visible environment names `/tests/expected/orders.json`, and only verifier root can read that golden. The entire report is graded by this comparison:

```python
actual = Path("/app/out/result.json").read_bytes()  # root follows symlinks
expected = Path("/tests/expected/orders.json").read_bytes()
assert actual == expected
```

**Evidence and impact.** A submitted symlink from the output path to the known golden path survives staging. The privileged read follows it, so the comparison checks the golden against itself. No report calculation is required, and no independent check defeats this path.

**Repair and check.** Reject symlinks at the actual read and protect traversal through candidate-controlled parent directories. Open relative to a trusted directory with suitable no-follow controls and verify the opened file; a separate earlier `is_symlink()` check can race if candidate code still runs. Check a correct report, an incorrect report, and a symlink submission through the real staging path.

Separate containers do not by themselves make a privileged read safe. Conversely, if staging rejects the symlink, the proposed path above does not work and is not evidence of a finding.

---

### C-2 — Same mechanism, unguessable golden root: why this is Minor

*`protected_ground_truth` · Minor · `chmod_follow` — does not block by itself*

Keep C-1's privileged read, but put the golden under a task-specific random identifier that appears only in sealed verifier files. The candidate supplies only an output file: it cannot execute code in the verifier, list the golden directory, or learn the identifier through another channel.

**Why the label changes.** The auditor can name a target that the candidate has no practical way to discover. The path weakness remains, but this does not establish a usable bypass. The standard framework path `/tests` is **not** such a secret; omitting that familiar prefix from `instruction.md` does not justify `Minor`.

**Repair and check.** Apply C-1's read protection. Inspect actual disclosure and staging before deciding severity; obscuring a filename is not a substitute for safe reads. If the symlink never reaches the reader at all, this mechanism is `None`.

---

### C-3 — A privilege drop a setuid binary can undo

*`protected_ground_truth` · Major only with the preconditions below · `chmod_follow`*

```python
DROP = ["setpriv", "--reuid=12000", "--regid=12000", "--clear-groups"]
subprocess.run(DROP + [str(binary), str(input_path)])
```

**Evidence needed.** Suppose the verifier itself installs the submitted binary as root-owned mode `4755` on a setuid-capable filesystem before this invocation. Its own files establish the capability; there is no need to assume transfer preserved it. Without `--no-new-privs`, executing that binary can regain privilege and read known answer files.

**Repair and check.** Set `no_new_privs` for candidate execution and avoid making candidate binaries setuid-root. Verify ownership, modes, effective privileges, and answer-file access at execution. **A missing `--no-new-privs` flag alone is not a confirmed finding** when the task provides no evidence that the binary can acquire that privilege.

---

### C-4 — Test identity leaked through the working directory

*`protected_ground_truth` · Major · `label_from_basename`*

**Task.** Validate an archive. Every case checks only success versus rejection, and the harness names each working directory for that expected outcome:

```python
work = WORK / f"reject-{case}"
result = invoke(archive, cwd=work)
assert result.returncode != 0
```

The corresponding acceptance cases use `accept-{case}`. A program that returns failure when its working directory's basename starts with `reject-`, and success otherwise, satisfies these assertions without inspecting the archive.

**Repair and check.** Use outcome-neutral temporary names. Keep readable names in pytest's report. Confirm that the same archive receives the same verdict under different neutral paths, and that valid and invalid archives under neutral paths get different verdicts.

---

### C-5 — Test identity leaked through the test's own name

*`protected_ground_truth` · Major · `label_from_basename`*

**Same validation task, different channel.** The harness derives a directory from `request.node.name` and invokes the candidate with `--archive /work/test_validate_rejects_checksum_mismatch/dataset.tar.gz`. The test checks only rejection.

**Evidence and repair.** A candidate can return failure on the `rejects` token without validating the checksum. Give candidate-facing paths neutral identifiers and keep test names inside verifier reporting. Check the full argument vector, working directory, and environment, not just the leaf filename.

---

### C-6 — Test identity leaked through the fixture directory

*`protected_ground_truth` · Major · `label_from_basename`*

**Same task, another channel.** The candidate receives paths under `fixtures/invalid/` or `fixtures/valid/`; expected success follows that label. Checking the parent directory is enough to pass a verdict-only suite.

**Repair and check.** Stage inputs at neutral paths and keep expected outcomes in verifier-owned data that candidate code cannot read. Confirm the test distinguishes valid and invalid **contents** after removing revealing directory names. Random scratch names are compatible with deterministic grading when their values do not affect what is checked; see [D-3](#d-3--random-temporary-names-that-do-not-change-grading).

---

### C-7 — A persisted directory that is only partially reset

*`protected_ground_truth` · Major with the answer-bearing state below · `cache_carryover`*

**Task.** Produce a two-phase reconciliation. The verifier checks phase one's result, then leaves it candidate-writable and trusts it as the expected baseline for phase two without rechecking it. Candidate code can rewrite the first result before producing the second; the comparison now accepts two matching fabricated results.

**Repair and check.** After checking phase one, retain its validated value in verifier-owned storage or independently revalidate it before use. Reset unrelated scratch space between invocations. Check that modifying phase one's stored artifact cannot change the expected phase-two result.

A cache of the candidate's own legitimately computed intermediate results is not automatically an exposure. Name the answer or grading decision the persisted state can change.

---

### C-8 — Oracle binary copied into the candidate's build workspace

*`protected_ground_truth` · Major · `colocation_walk`; can also support `sound_verifier`*

**Task.** Implement a documented legacy conversion format. A verifier-only reference executable is accidentally copied into a directory that submitted code can execute from during grading.

**Evidence and impact.** A wrapper can call the reference executable on every input and return its output. Comparing final outputs does not distinguish that wrapper from a reimplementation.

**Repair and check.** Keep the reference out of the candidate process's accessible filesystem and execution path. Check the actual candidate invocation: excluding one copied path is insufficient if the original remains reachable. The wrapper should fail after isolation, while an independent correct implementation passes.

---

### C-9 — Candidate binary left writable by its own UID

*`protected_ground_truth` · severity depends on a demonstrated check-to-use bypass*

**Task.** The verifier inspects a compiled binary for prohibited dependencies, then runs several cases. It leaves both that binary and its parent directory writable to the executing candidate UID. A process can replace the already-inspected binary before a later invocation uses it.

**Evidence needed.** Name the checked file, replacement opportunity, later invocation, and behavior the replacement makes possible. Writable mode bits alone do not show that a reward condition can be bypassed.

**Repair and check.** Put the inspected executable in verifier-owned storage that the candidate UID cannot modify or replace, and execute that same protected artifact. `chmod 0555` alone is insufficient when the candidate owns the file and can change its mode, or can replace it through a writable parent. Verify both file and directory ownership and a replacement attempt.

---

### C-10 — A test that asserts the opposite of the contract

*`sound_verifier` · Major — rejects valid work*

**Task.** An incremental documentation generator must reuse a cache entry when rerunning the action would produce identical bytes. A comment-only source edit does not change those bytes.

**Evidence and impact.** The test makes that edit, confirms identical output, then requires the generator to have run again. A correct implementation records a cache hit and fails. The verifier enforces source-byte invalidation even though the instructions promise output-based reuse.

**Repair and check.** Make the assertion match the documented promise. A comment-only edit should hit the cache; an edit that changes rendered content should miss. These paired cases catch both unconditional reruns and an implementation that always reuses stale output.

---

### C-11 — A restriction stated in prose and enforced nowhere

*`sound_verifier` · Major when an ordinary noncompliant implementation passes*

**Task.** Implement a CSV processor in Python using only its standard library. The verifier image also contains pandas, and the suite checks only output values. A straightforward pandas implementation produces correct output and passes every assertion while violating the explicit dependency requirement.

**Repair and check.** If the restriction is necessary, enforce it through the actual grading environment and build/execution boundary. Otherwise remove it from the contract. A source-text grep is not a complete dependency boundary. Confirm that a compliant implementation passes and the concrete prohibited-dependency implementation fails under the stated restriction.

---

### C-12 — A schema check accepts an incorrect settlement report

*`sound_verifier` · Major — accepts wrong work*

**Task.** Read line items and produce the total in integer cents for each merchant. For merchant `M-7`, two line items of `1200` and `350` require `1550`.

```python
report = json.loads(Path("/app/report.json").read_text())
assert len(report["merchants"]) == 1
assert report["merchants"][0]["merchant_id"] == "M-7"
assert isinstance(report["merchants"][0]["total_cents"], int)
```

**Evidence and impact.** Assume these are all the report checks. An implementation that groups merchant IDs but leaves each total initialized to `0` passes every assertion. That is an ordinary incomplete implementation, and the report is wrong by `1550` cents. This is a demonstrated acceptance gap, not just a request for more tests.

**Repair.** Compute expected per-merchant totals from sealed canonical inputs, then validate every required value and native type. Include a second merchant, multiple line items, and any documented adjustments such as refunds.

**Check.** The correct report passes; the zero-total report fails. Change a line-item amount and confirm the required total changes, so an implementation that embeds the original answer also fails. In Python, use `type(value) is int` if the schema excludes booleans: `isinstance(True, int)` is true.

---

### C-13 — Exact JSON text matching rejects a valid report

*`sound_verifier` · Major — rejects valid work*

**Task.** Write JSON with integer fields `count` and `total_cents`. The contract explicitly allows any object-key order and whitespace.

```python
assert output_text == '{"count":2,"total_cents":1550}'
```

**Concrete valid answer.** `{"total_cents": 1550, "count": 2}` satisfies the contract but fails this assertion. The problem is the comparator, not missing instructions about a required byte format.

**Repair and check.** Parse JSON, validate its permitted fields and native types, and compare required values. Both serializations above should pass; `{"count": 2, "total_cents": 0}` should fail. Keep byte-exact comparison when the contract requires canonical bytes, such as the fixed-width export in [B-1](#b-1--documented-field-width-copied-through-unpadded).

---

<h2 id="d--deterministic-execution">D — Deterministic execution</h2>

The question is whether a **fixed submission and task package**, under the declared conditions, face the same graded cases and expected results. The traces below illustrate possible runs; they are not claims that these examples were executed.

### D-1 — Unseeded dates make the graded workload change

*`deterministic_execution` · Major*

**Task.** Convert calendar dates to the next day, including leap years. The verifier chooses its graded dates from a generator seeded with the current time, then compares the candidate with a correct calendar implementation.

**Two-run trace.** Hold the submission fixed: it handles ordinary dates but treats February as always having 28 days. One reachable draw contains only ordinary dates, so it passes. Another contains `2024-02-28`; it returns `2024-03-01` instead of `2024-02-29`, so it fails. The uncontrolled draw changes which required behavior grading exercises.

**Repair.** Commit a fixed representative fixture set or use a fixed seed and pinned generator behavior. Include mandatory boundary cases explicitly; do not rely on a random draw to include them. Keep held-out inputs and generator details sealed from candidate code.

**Check.** Confirm clean runs select the same graded dates and expectations. The correct implementation must pass; the no-leap-year implementation must fail consistently. A `REPLAY_SEED` option that is unset by default does not repair a clock-seeded default path.

### D-2 — An expiry check uses the real date

*`deterministic_execution` · Minor when confined to this one rule*

**Task.** Evaluate a fixed subscription snapshot as of the supplied `as_of` date. The verifier correctly uses that date everywhere except one expiry assertion, which calls `date.today()`.

**Two-run trace.** The package says `as_of = 2026-01-15` and the subscription expires on `2026-01-31`. The same “active” result is accepted when grading runs on January 20 and rejected on February 1. The snapshot did not change; the verifier's clock did.

**Repair and check.** Use the supplied date for this assertion and declare timezone/boundary semantics where relevant. Check dates before, on, and after expiry against those semantics. Changing the wall clock must not change the fixed snapshot's verdict. This localized `Minor` still blocks on the deterministic-execution axis.

### D-3 — Random temporary names that do not change grading

*`deterministic_execution` · None for this mechanism*

**Task.** Validate the same sealed archives on every run. The verifier stages them under fresh random temporary directory names, then checks the same content-based success or rejection results. Neither paths nor their random suffixes are compared as required output.

**Why this is acceptable.** The random value changes scratch storage only. It does not choose inputs, alter expected answers, or change acceptance. Removing answer-bearing directory names as in [C-6](#c-6--test-identity-leaked-through-the-fixture-directory) improves isolation without making grading nondeterministic.

**Check.** Trace the random value to every use. This conclusion changes if, for example, the verifier compares that generated path with a fixed path in the submitted report.

---

<h2 id="e--responding-to-a-review">E — Responding to a review</h2>

### E-1 — A revision note that closes the specific gap

Suppose the panel reports the hidden payment tie-break in [A-4](#a-4--a-payment-tie-break-rule-exists-only-in-the-verifier). A useful response names the rule, changed files, and what the checks establish. This is an illustrative response, **not a test receipt**; replace it with checks you actually ran and their results.

```text
Finding: coherent_contract — equal timestamps have an undisclosed tie-break.

Changed instruction.md to specify ascending timestamp, then sequence,
then original input position. The reference and verifier now use that order.

Added a fixture with input-order events A=(12:00, seq 20, set 100) and
B=(12:00, seq 10, add 5), starting from zero. Expected balance: 100.

Validation performed:
- Reference on the revised task: passes.
- A timestamp-only implementation: fails the new fixture with balance 105.
- Equal timestamp/sequence fixture: checks the final input-position rule.

Evidence: [revision, command/run ID, and retained result locations].
Scope: these results exercise ordering; they do not prove every panel axis.
```

If the review contains several findings, give each one a disposition and its own evidence. Avoid “fixed all feedback” without a mapping to the claims. Do not rely on the next review automatically receiving earlier comments; include the necessary context in the revision response.

### E-2 — A disagreement that shows why the proposed failure cannot occur

Suppose a finding says JSON key order is incorrectly enforced, but the cited test actually parses JSON before comparing objects. A useful response quotes the check and supplies a counterexample:

```text
Finding: sound_verifier — alternate JSON key order would fail.

The cited comparison is json.loads(actual) == expected, not a text
comparison. instruction.md permits any key order. I checked the same
report with its keys reversed and added whitespace; it still passes.
A report with the wrong total fails. [Attach the actual check results.]

Please re-evaluate this finding against [revision and exact test location].
If another check rejects the valid serialization, please identify it.
```

That addresses the claimed false rejection. “The Oracle passes” would not: the Oracle may emit only the single serialization the disputed check accepts. For an answer-exposure dispute, provide analogous evidence about artifact staging, accessible paths, and the exact privileged read.

See [Defending Your Submission](/portal/docs/reviewing-tasks/defending-your-submission) for the review and escalation process.

---

## Next steps

- [Return to the Quality Panel Judge Guide](/portal/docs/testing-and-validation/quality-panel-judge-guide)
- [Writing Tests](/portal/docs/creating-tasks/writing-tests)
- [Dockerfile Requirements](/portal/docs/creating-tasks/dockerfile-best-practices)
