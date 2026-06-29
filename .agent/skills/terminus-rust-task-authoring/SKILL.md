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
- Put Cargo on the login-shell `PATH`, including symlinks for `cargo` and
  `rustc` under `/usr/local/bin` when necessary.
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
