---
name: terminus-rust-task-authoring
description: Guidelines and strict checklist for authoring Terminus Regular tasks for Rust repositories to avoid common layout, verifier, and environment bugs.
---

# Terminus Rust Task Authoring Guidelines

When transforming a Rust bug into a Terminus task, strictly follow these standards to ensure quality, reproducibility, and proper evaluation on the platform. These rules address critical pitfalls discovered in previous authoring attempts.

## 1. Initial State & Cleanliness
- **Strictly Buggy Baseline**: `environment/repo` MUST be on the exact parent commit (the buggy state). It cannot have the patch already applied.
- **No Dirty Files**: The repository must be completely clean. No `.rej`, `.orig`, or untracked patch files left behind. Run `git clean -fdx` and `git reset --hard HEAD` before packaging.
- **Solution Isolation**: The patch should exist only in `solution/fix.patch`. Do not leave traces of the fix in the environment repo.

## 2. Strict Task Layout & Sizing
A valid task folder must only contain:
```
instruction.md
task.toml
environment/
  Dockerfile
  .dockerignore
  repo/
solution/
  fix.patch
  solve.sh
tests/
  test.sh
  test_outputs.py
  files/wheels/ (if local pip installs are needed)
```
- **Remove Caches and Git**: Before zipping, remove `.git/`, `target/`, `__pycache__/`, `.pytest_cache`, `.DS_Store`. The final submission size should be as small as possible (ideally under 15-20MB, strictly < 100MB).
- **.dockerignore**: Always include `environment/.dockerignore` blocking `.git`, `target`, `__pycache__`, `*.rej`, etc., so the image build is clean and fast.

## 3. Dockerfile Environment
- **Digest-Pinned Base**: Use a specific, pinned digest for the base image (e.g., `FROM rust:1.85.0-slim-bookworm@sha256:...`).
- **Required Tools**: Install essential tools the agent will need: `asciinema`, `bash`, `ca-certificates`, `coreutils`, `git`, `patch`, `python3`, `python3-pip`, `ripgrep`, `sed`, `tmux`, `util-linux`.
- **Working Directory & Mount**: 
  - Explicitly set `WORKDIR /app`.
  - Copy the repo properly: `COPY repo/ /app/`.
- **Preloading Dependencies**: Run `cargo fetch --locked` (and optionally pre-build sub-crates if applicable) in the Dockerfile so that agents do not encounter network dependency fetches during their run.

## 4. Verifier Standards (Pytest is King)
Even for Rust tasks, the standard Terminus test harness relies on Python `pytest` and `pytest-json-ctrf`.
- **`tests/test_outputs.py`**: Write a robust Python test script that:
  - Generates a temporary Rust project using `tmp_path_factory.mktemp()`.
  - Sets up path dependencies pointing to the local `/app` repository.
  - Compiles the temporary project via `subprocess.run(['cargo', 'run', ...])`.
  - **Asserts Real Behavior**: Don't just assert string matching on generated outputs. For example, if testing bash completion, actually source the script in `bash` and assert the `COMPREPLY` array contains the expected tokens.
  - **Docstrings**: EVERY test function MUST have a clear docstring explaining what behavior is being tested.
- **`tests/test.sh`**: Must run pytest, output CTRF to `/logs/verifier/ctrf.json`, and set `/logs/verifier/reward.txt` to `1` or `0`.
- **Offline Wheels**: Do not hit the network in `test.sh`. Install `pytest` and `pytest-json-ctrf` from local `.whl` files stored in `tests/files/wheels/` using `--no-index --find-links`.

## 5. Instruction & Test Symmetry
- `instruction.md` must describe the bug **purely from an observable behavior standpoint**.
- Do not expose GitHub PR IDs, Issue numbers, or exact implementation hints.
- Every edge case, "normal behavior preservation", or anti-shortcut condition asserted in the pytest verifier **must** be explicitly mandated in the `instruction.md`.
- Ensure difficulty metadata in `task.toml` honestly reflects the complexity. If the fix is a localized one-line change, it is likely `difficulty = "medium"`, not `"hard"`.
