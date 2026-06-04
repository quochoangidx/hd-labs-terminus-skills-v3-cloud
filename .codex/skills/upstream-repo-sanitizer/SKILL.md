---
name: upstream-repo-sanitizer
description: Use when staging an upstream repository under environment/repo for a Terminus task. Prunes large files and irrelevant content, enforces Docker build context limits, removes secret-shaped files, handles ruff exclusion, and keeps codebase_size metadata honest.
---

# Upstream Repo Sanitizer

Use this skill before submitting a task that contains `environment/repo`, usually under `workspace/tbrain-*`.

## Why Size Matters

Terminus CI blocks oversized Docker build contexts:

- `environment/` must be at most `100 MiB` total.
- no single file under `environment/` may exceed `50 MiB`.

This keeps builds reproducible, cacheable, auditable, and lazy-pull friendly.

## Required Checks

From the task root:

```bash
du -sh environment
find environment -type f -exec du -h {} + | sort -h | tail -30
find environment -type f | wc -l
```

Check secret-shaped and macOS junk:

```bash
find environment -type f \( -name '*.key' -o -name '*.pem' -o -name '*.crt' -o -name 'id_rsa*' \) -print
find environment \( -name '.DS_Store' -o -name '._*' -o -name '__MACOSX' -o -name '__pycache__' \) -print
```

Check task-environment hint leakage:

```bash
find environment -type f \( -iname 'README*' -o -iname 'spec*.md' -o -iname '*architecture*' -o -iname '*.md' -o -iname '*.txt' \) -print
grep -RInE 'step[- ]by[- ]step|solution|hint|TODO|walkthrough|implement by|fix by|you should|verifier|oracle|hidden tests' environment || true
```

Environment docs may define realistic API contracts, schemas, protocols, or
business rules. They must not contain procedural solve guides, commented
solution plans, or extra task goals that should have been in `instruction.md`.

Check blacklist-prone database substrings only if CI or docs mention them:

```bash
grep -RilE 'maxscale|oci_|oracle|mysql|sqlserver|mariadb|snowflake|redshift|bigquery|postgres' environment/repo || true
```

Follow any explicit CI feedback before applying broad pruning.

## Safe Pruning Targets

Usually safe to remove from `environment/repo`:

- `.git/`
- `.github/` unless task needs workflow files
- docs site build outputs
- coverage files
- caches
- virtualenvs
- `node_modules`
- compiled artifacts not needed by the task
- huge fixtures unrelated to the regression
- release signing keys or certificates
- image/video assets unrelated to tests

Do not remove files needed to import, build, or run the focused subsystem.

## Codebase Size Metadata

Count files under `environment/`, excluding Dockerfile/compose. Choose:

- `minimal`: roughly 0-19 environment files
- `small`: roughly 20-199 environment files
- `large`: 200+ environment files

All three sizes are accepted. Keep the value honest and vary sizes across the
task portfolio; do not add filler files or remove useful context solely to move
between buckets.

## Local Tooling Config

Do not add root-level `pyproject.toml` as a submitted task artifact. If local
ruff or editor tooling needs to exclude `environment/repo`, keep that
configuration outside the submitted task or remove it before packaging.

For local-only checks, this is the relevant exclusion shape:

```toml
[tool.ruff]
target-version = "py312"
extend-exclude = ["environment/repo"]
```

Use the Python target version matching the Docker image.

## Dockerignore

Ensure `environment/.dockerignore` exists:

```text
.git
.gitignore
**/__pycache__/
**/*.pyc
**/.pytest_cache/
**/.mypy_cache/
**/.ruff_cache/
**/node_modules/
**/dist/
**/build/
**/.venv/
**/venv/
.env
*.log
solution/
tests/
```

## Sanitization Discipline

Do not silently rewrite upstream source behavior to dodge CI. If a blacklist or size issue touches source needed by the bug, explain the tradeoff and choose the smallest safe change.

After pruning, run:

```bash
python -m pytest <focused smoke test>
```

inside the container or equivalent local environment when possible.
