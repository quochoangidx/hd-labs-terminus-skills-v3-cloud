# Submission readability and panel input size

Apply when building, revising, or preparing a task for quality review. These are
local readability heuristics for submitted task files, not published platform
limits, new correctness requirements, or limits on this skill repository.

## Size is a diagnostic, not a gate

- Flag task text files over **800 lines** for a bounded readability assessment.
  Do not reject a task or rewrite a necessary file solely for crossing that mark.
- Record text-file line counts and bytes, largest contributors, and aggregate
  size per axis packet. If estimating tokens, state the tokenizer or heuristic
  and its limitations; otherwise mark the estimate unavailable. Track binary
  asset bytes separately rather than interpreting them as text tokens.
- No safe platform token/line threshold is known. Several short files can still
  exceed a combined input budget; splitting files does not prove they will all
  be read. A file below 800 lines is not certified complete or readable.
- Do not minify JSON, remove useful formatting, compress text, or pack long lines
  merely to reduce line count. Consider actual content volume and navigation.

## Reduce repetition without reducing the task

1. Give each rule one authoritative definition; reference it clearly from the
   instruction. Align schema constraints, domain prose, Oracle and verifier with
   that definition. Do not duplicate the full rule across several documents or
   move necessary authority into hidden tests/solution to make the prompt short.
2. Split code by genuine responsibilities such as validation, state transitions
   and output rendering, not arbitrary line boundaries. Keep entrypoints and
   dependency links easy to follow; preserve packet visibility boundaries.
3. Remove unused scaffolding, duplicate prose and provably redundant fixtures
   only within authorized edits. Large native assets and necessary upstream
   source can remain; file length alone is no reason to prune relevant evidence.
4. Prefer a compact set of discriminating witnesses over repeated cases covering
   the same branch. Before removing a fixture, identify the retained witness for
   its requirement, boundary, interaction and partial-fix mutant. Preserve named
   rule isolation, meaningful input variation, required artifact checks and
   promised lifecycle coverage. Never weaken expectations to save input space.
5. Keep essential contract authority discoverable independently of large fixture
   corpora. A short navigation entry may point to authoritative files, but a
   summary is not a substitute for their complete contents or implementation.

## Review and reporting

Include size diagnostics and justified retain/simplify decisions in the existing
report outside the task/ZIP. Do not add a separate reviewer or review cycle for
size. Read-only review reports opportunities without editing the task.

Reviewers must paginate and record unread/truncated evidence; never equate a
small packet with a completed review. A long file alone is advisory, while an
actually incomplete mandatory inspection blocks local clearance independently
of size. Missing evidence is not by itself a confirmed defect in the task.

After authorized simplification, run affected deterministic checks and preserve
semantic/mutant discrimination. Follow the existing snapshot invalidation and
clearance rules; do not reuse old semantic clearance just because an edit was
called cleanup. Do not split or rewrite portal-mirrored docs or AGENTS.md merely
to satisfy this heuristic.
