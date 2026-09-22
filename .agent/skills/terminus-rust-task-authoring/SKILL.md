---
name: terminus-rust-task-authoring
description: Guidelines and strict checklist for authoring Terminus Regular tasks for Rust repositories to avoid common layout, verifier, and environment bugs.
---

# Terminus Rust Task Authoring Guidelines

This is a Rust-specific supplement. Follow the `terminus-regular-task-authoring`,
`task-clone`, and `task-zip-submit` skills as the source of truth for layout,
verifier dependencies, submission explanations, review, and packaging. If this
file conflicts with those skills, the canonical skills win.

## Rust-Specific Rules

- Stage the exact buggy source under `environment/repo`; keep the oracle patch
  only under `solution/`.
- Use a digest-pinned Rust runtime image and install `tmux`, `asciinema`, Git,
  patching/search tools, Python, and the Rust toolchain needed by the task.
- In every Dockerfile, use digest-only external image refs for `COPY --from=`;
  do not write `COPY --from=image:tag@sha256:...`. Stage aliases remain valid.
  `COPY --chown=` may use named users or numeric IDs — the cloud builder
  resolves both.
- Put Cargo on the AGENT login-shell `PATH`. The `rust:*-slim` images expose
  cargo only via a Docker `ENV PATH=/usr/local/cargo/bin:$PATH` addition, which
  the verifier keeps through `docker exec` but the agent's tmux login shell drops
  because `/etc/profile` resets `PATH` — so `cargo`/`rustc` become "command not
  found" in the agent shell (and any rubric that rewards `cargo build` then
  punishes the agent unfairly). Fix in the Dockerfile:
  `RUN ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo && ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc`
  (`/usr/local/bin` is on the reset login `PATH`), or wire `/usr/local/cargo/bin`
  into `/etc/bash.bashrc`. `RUSTUP_HOME`/`CARGO_HOME` survive the reset — only
  `PATH` needs restoring.
- Do NOT warm-build the shipped source during Docker image construction unless
  the verifier's build helper clean-rebuilds and checks exit status (clean →
  assert the artifact is gone → build → assert `returncode == 0` with output in
  the message). A warm `RUN cargo build` otherwise leaves a stale binary that
  grades a non-compiling submission green (AGENTS.md §8, quill-plugin-resolver
  return). Prove the gate by injecting a compile error and confirming reward 0.
  Warming only the dependency cache (e.g. `cargo fetch --locked`) for fast
  incremental agent rebuilds is fine.
- Keep verifier dependencies in the Docker image. Never store wheels under
  `tests/` and never install packages from `tests/test.sh`.
- Supply Rust verifier programs at verification time from
  `tests/test_outputs.py` or verifier fixtures. Do not stage hidden
  `*_test.rs` or reproducer programs inside `environment/repo`.
- Drive public behavior through temporary Cargo projects, binaries, or public
  APIs. Avoid source-string checks and private implementation assertions.
- Run deterministic focused commands rather than the entire upstream suite.
  Every subprocess should have a practical timeout and useful captured output.
- When verifier Python rebuilds or executes Rust code, demote before exec and
  include `--no-new-privs` or equivalent containment. Keep goldens outside all
  directory trees passed to that process and probe that it cannot read them or
  `/logs/verifier`; separate mode alone does not hide verifier files from code
  executed inside the verifier.
- Preserve instruction/test symmetry for feature flags, workspace layouts,
  target-specific behavior, generated artifacts, and compatibility paths.
- Keep end-to-end expected-artifact generation in `solution/`, not `tests/`.
  Tests may execute the candidate, parse output, use golden/sealed truth, and
  assert invariants. If the task requires a variable config/input file, read it
  dynamically and add a mutation re-run so an original-value hardcode fails.
- **Do NOT ship the bare `cargo new` stub-CLI skeleton.** The CI
  `template_detection` static check (first observed 2026-07-13 on
  tbrain-bundler-resolve) BLOCKS submissions matching the named template
  `rust_cli`: a minimal single-crate repo (`Cargo.toml` + one `src/main.rs`
  stub + README), a stdin-JSON→stdout-JSON batch binary, an "extend the
  starter" instruction, a hidden vector-corpus verifier, and
  minimal single-crate layout. It judges structural SHAPE (an LLM fallback
  scores the match), so a wording sweep will not clear it. Minimum
  de-templating for a new Rust task: a realistic multi-module crate
  (`lib.rs` + several `src/*.rs` modules), in-repo unit tests and repo
  furniture, and — where the domain allows — a file-based I/O surface
  instead of a stdin→stdout batch pipe. A multi-module restructure ALONE is
  INSUFFICIENT (confirmed 2026-07-18, tbrain-depgraph-purl-canon: still
  flagged `rust_cli` 0.85 after the restructure) — stack ALL de-templating
  levers before resubmitting: file-surface I/O, deeper module tree plus
  realistic repo furniture, scrub stub-fill framing from instruction and
  module docs, and enrich Cargo.toml (description, non-`0.1.0` version);
  see AGENTS.md §9 for the current verdict.

## Submission Explanations

Create the reviewer-facing Difficulty, Solution, and Verification explanations
outside the task folder under:

```text
workspace/reports/<task-slug>/
```

Describe intrinsic Rust reasoning such as trait/API interactions, feature
resolution, workspace inheritance, ownership/lifetime constraints, generated
code, or state-machine invariants. Do not use compile time, repository size, or
timeouts as evidence of difficulty, and do not place the explanations in the
submission ZIP.
