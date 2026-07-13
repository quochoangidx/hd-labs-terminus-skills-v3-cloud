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
- Warm the unmodified build during Docker image construction, for example with
  `cargo build --tests --locked`, and preserve the dependency/build cache needed
  for fast incremental agent rebuilds.
- Keep verifier dependencies in the Docker image. Never store wheels under
  `tests/` and never install packages from `tests/test.sh`.
- Supply Rust verifier programs at verification time from
  `tests/test_outputs.py` or verifier fixtures. Do not stage hidden
  `*_test.rs` or reproducer programs inside `environment/repo`.
- Drive public behavior through temporary Cargo projects, binaries, or public
  APIs. Avoid source-string checks and private implementation assertions.
- Run deterministic focused commands rather than the entire upstream suite.
  Every subprocess should have a practical timeout and useful captured output.
- Preserve instruction/test symmetry for feature flags, workspace layouts,
  target-specific behavior, generated artifacts, and compatibility paths.
- **Do NOT ship the bare `cargo new` stub-CLI skeleton.** The CI
  `template_detection` static check (first observed 2026-07-13 on
  tbrain-bundler-resolve) BLOCKS submissions matching the named template
  `rust_cli`: a minimal single-crate repo (`Cargo.toml` + one `src/main.rs`
  stub + README), a stdin-JSON→stdout-JSON batch binary, an "extend the
  starter" instruction, a hidden vector-corpus verifier, and
  `codebase_size = "minimal"`. It judges structural SHAPE (an LLM fallback
  scores the match), so a wording sweep will not clear it. Minimum
  de-templating for a new Rust task: a realistic multi-module crate
  (`lib.rs` + several `src/*.rs` modules), in-repo unit tests and repo
  furniture, and — where the domain allows — a file-based I/O surface
  instead of a stdin→stdout batch pipe. Remediation levers are still
  UNVERIFIED (single data point); see AGENTS.md §9 for the current verdict
  before relying on any one lever.

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
