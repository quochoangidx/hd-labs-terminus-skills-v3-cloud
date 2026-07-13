---
name: task-language-port
description: Use when the user wants an already-passing Terminus Regular task re-implemented in one or more additional languages, producing independently-submittable ZIPs rather than a re-languaged duplicate. Covers gallery-backed language-feasibility screening, category-hold checks, the mandatory narrative reskin, faithful placeholder+solution translation, and Harbor oracle/nop re-validation. Does not mine or invent new task concepts.
---

# Task Language Port

Turn an existing, validated Terminus task into one or more sibling tasks that implement the
identical behavior in a different language. The source task's `instruction.md`, `SPEC`, and
test judge define ground truth; nothing about *what* the task requires may change, only the
language it's built in and (per the reskin rule below) its surface narrative.

## Why this is usually safe

Most Regular tasks verify a compiled/interpreted program as a **black box**: the verifier
invokes a named binary/CLI by path (stdin/stdout or a file argument), parses its JSON output,
and compares it against a pure-Python reference/generator (`tests/_ref.py`, `tests/_gen.py`,
or an inline reference class in `tests/test_outputs.py`). Because the judge is already
language-agnostic, porting is mostly: translate the source faithfully, keep the judge
untouched, adapt the build system. Two source shapes exist — know which one you have:

- **From-scratch build**: `environment/repo` ships a naive/incomplete program; `solution/`
  ships a complete replacement file; `solve.sh` copies it in and rebuilds.
- **Fix-the-placeholder**: most of `environment/repo` is already correct; one function is a
  deliberately-wrong placeholder; `solution/` is a patch or full-file fix for just that piece.

Port **both** the wrong behavior and the fix, byte-for-byte faithfully — the gap between them
is the task's difficulty. Do not simplify the placeholder's bug or improve the algorithm.

## Step 0 — Feasibility and scope (do this before touching any file)

1. **Category hold check, first.** If the source task's `task.toml` category is `debugging`,
   `software-engineering`, or `data-processing` (blocked since 2026-07-11) — or its shape would
   PREDICT one of those to the category classifier — tell the user these are currently ON HOLD
   on the platform (see `task-miner`/`task-clone`); a port would sit un-submittable regardless
   of language. Confirm they still want it (e.g. for later, once the hold lifts) before
   spending build effort.

   **Template-shape check, same gate.** The CI `template_detection` static check (first
   observed 2026-07-13) BLOCKS submissions whose structural shape matches a named template —
   `rust_cli` is confirmed (minimal single-file stub crate, stdin-JSON→stdout-JSON batch
   binary, "extend the starter" instruction, hidden vector corpus, `codebase_size = minimal`);
   assume sibling templates exist for other languages. A port series multiplies exposure:
   every sibling shares the core's shape, so if one flags, all will. If the SOURCE task has
   this stub-CLI shape, de-template the CORE first (realistic multi-module layout, in-repo
   tests, domain-authentic file I/O where possible — levers UNVERIFIED, see AGENTS.md §9) and
   only then port; never try to clear the flag per-port.
2. Identify the source language and what the program is actually coupled to: pure JSON/stdin
   logic ports to nearly anything; a task tightly bound to a source-ecosystem library (e.g. a
   C program driving `sqlite3` directly, a Node program parsing npm lockfile conventions, tar
   extraction semantics) narrows the safe target set to languages with strong *offline*
   support for that same capability.
3. **Ground the target list in the live gallery, not assumption.** Re-run
   `python3 .agent/skills/task-miner/refresh_gallery_taxonomy.py` and read its "Language
   distribution" table (`task_inspiration_v2.languages`, real counts) before deciding what's
   plausible — a language can look niche or risky and turn out to be heavily represented
   already (e.g. a 2026-07-06 pull showed PHP at 262 tasks and Kotlin at 267, both well above
   several languages usually assumed "safe"). Treat that table, not a fixed personal shortlist,
   as the source of truth for "support as many languages as possible."
4. **General-purpose targets** — anything Turing-complete that can read/write JSON and ships
   an official Docker image or apt-installable interpreter on a canonical Debian/Ubuntu/gcc
   base is fair game. Confirmed low-friction examples, digest-pinned where this project has
   already vetted one:

   | Language | Canonical base (digest-pinned) |
   |---|---|
   | C / C++ | `gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c` |
   | Go | `golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac` |
   | Rust | `rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36` |
   | Java / Kotlin | `eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14` (Kotlin: add `kotlinc` at build time) |
   | TypeScript / JavaScript | `node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383` |
   | Ruby | `ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df` |
   | PHP, Perl, Lua | no pre-vetted digest yet — pin the official Docker Hub image yourself and add a one-line justification comment; all three are well-represented in the live gallery, so this is paperwork, not a real blocker |

   Python is intentionally left off this list — this project doesn't use it as a port target
   even though it is technically no harder than the others (a Python Regular task must be Hard,
   which just means checking the source's difficulty survives the port).
5. **Hard-stop languages — a task-shape mismatch, not a platform ban.** A declarative/config
   format (Terraform/HCL, YAML, TOML, JSON, HTML/CSS, Make/CMake) cannot host an imperative,
   stateful CLI algorithm that reads JSON and simulates a state machine — refuse this and say
   why. Note this is about what the *format* can express, not whether the platform accepts it:
   Terraform alone showed 153 gallery tasks and HCL 108, but those are tasks whose own
   deliverable already is a declarative config, a different task shape than the one this skill
   ports.
6. **Never assume the count.** Once you know the feasible set (often anywhere from 1 to ~10),
   tell the user exactly which languages you'd build and how many, and get explicit
   confirmation before spawning any work — including when the user already said "as many as
   possible." If Harbor/Docker validation will be expensive (many parallel builds), surface
   that as part of the same confirmation.

No JSON library exists offline for C/C++/Java/Kotlin by default — hand-roll a small parser
tailored to the task's exact fixed schema rather than vendoring a dependency; Go/Rust/Node/
Ruby/PHP/Perl/Lua all have adequate JSON in stdlib or a standard, low-risk package fetchable at
*image build* time (network is fine during `docker build`; only agent/verifier **runtime** is
offline).

## Step 1 — Stage the source

Extract the source ZIP (or point at an existing task folder) into
`workspace/<source-task-slug>/` inside this repo — confirm `/workspace/` is in `.gitignore`
first (it should already be). Read, in full, before delegating: `instruction.md`, `task.toml`,
the spec/SPEC doc, the shipped `environment/repo` source (placeholder and, if present, the
already-correct surrounding code), `solution/`, `solve.sh`, and every file under `tests/`.
Identify every literal the judge depends on: JSON field names, string-literal enum values
(kind/state tags), numeric thresholds, and the exact worked example — these must survive
every port unchanged.

## Step 2 — One distinct reskin per language (mandatory, not cosmetic)

A ZIP's filename is never seen by the platform or a reviewer — only `instruction.md` and
`task.toml` content are. So renaming the file alone does not stop a reviewer from noticing
that several submissions describe the identical scenario in different languages. For each
target language, invent a new, unrelated domain/cover story and rename the CLI binary, while
keeping 100% identical: JSON schema field names, string-literal values, numeric thresholds,
the worked example, and the algorithm. This means the existing test judge (`tests/_gen.py`,
`tests/_ref.py`, the reference class inside `tests/test_outputs.py`, curated fixtures, any
differential fuzzer) needs **zero logic changes** — only the one line that resolves the
binary name/build command may need editing. Never reuse the same cover story across two ports
of the same source, and check it doesn't collide with another sibling task already in this
portfolio. Pick a domain where the schema's existing vocabulary still reads naturally (an
abstract low/high/dwell schema fits almost any duty-cycle equipment; a schema with
software-flavored fields like `client`/`rate`/`banned_at` fits another software domain more
naturally than a physical-process one).

Update the task slug/folder/ZIP name and `task.toml` tags to match the new story. Check this
portfolio's own sibling `task.toml` files for the actual `languages =` casing convention
before trusting generic advice — this project's real accepted tasks use Title Case
(`"Rust"`, `"Go"`, `"C"`, `"TypeScript"`) with `"C++"` as a fixed idiomatic exception, not the
lowercase slugs some skill docs describe.

## Step 3 — Build, one parallel agent per confirmed language

Each agent independently: rewrites `instruction.md` + spec/README in the new voice (run the
`anti-llm` skill pass on the prose afterward, preserving every fact/number/path); adapts
`environment/Dockerfile` to the target's base image plus this project's standing Docker rules
(toolchain symlinked onto the login-shell PATH, warm build of the *unmodified* shipped source,
`git init` after the build); ports the placeholder and the solution with identical behavior;
renames the CLI binary everywhere, including the one resolution line in the test file; updates
`task.toml`; recomputes `codebase_size` honestly from the real file count. Then validates for
real — `stb harbor run -a oracle -p .` must be `1.000` and `stb harbor run -a nop -p .` must be
`0.000`, re-exercising the *entire* differential/verifier suite, not a spot check. Finally
packages per this project's ZIP-submission rules (allowlist zip, executable bits on
`solve.sh`/`test.sh`, no junk) and writes the result to
`workspace/<source-task-slug>/tbrain-<new-problem-slug>-<language-suffix>.zip`.

Before calling a port done, `grep -r` the whole task folder for the OLD binary name and the
OLD domain word — a stray docstring/comment mention is the single most common leftover and
costs a follow-up round every time it's skipped.

If a spawned agent stalls or fails (rate limit, crash), don't assume nothing happened —
inspect its actual files on disk (folder renamed? binary renamed? zip already placed?) and
resume it with a precise done-vs-pending list, rather than restarting from scratch or trusting
an idle ping alone.

## Output location

`workspace/<source-task-slug>/` — gitignored, never committed. Confirm this before the first
write of a session; if the user wants the result somewhere else (e.g. a Downloads folder),
mirror the same `<source-task-slug>/tbrain-<new-slug>-<language>.zip` layout there instead.
