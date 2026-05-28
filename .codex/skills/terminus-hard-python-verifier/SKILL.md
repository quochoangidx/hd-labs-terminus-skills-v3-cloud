---
name: terminus-hard-python-verifier
description: Use when writing pytest verifier suites and oracle solutions for hard Python debugging tasks in Terminus. Focuses on behavioral subprocess tests, anti-cheating coverage, edge cases, and making tasks hard enough that coding agents may fail.
---

# Terminus Hard Python Verifier

Use this skill after choosing a Python debugging task.

## Test Design

Write verifier tests that exercise the system from the outside:

- CLI: run `subprocess.run([...], capture_output=True, text=True)`.
- Library: import only public APIs unless the task is explicitly internal.
- Framework: create temporary user projects and invoke the framework command.
- File outputs: parse JSON/XML/CSV with real parsers.

Avoid reading source to assert implementation choices.

## Coverage Shape

For hard tasks, include:

- one direct regression reproducer
- one boundary condition
- one normal-behavior preservation test
- one anti-shortcut test
- one test proving the failure mode is recoverable, not just hidden

Map every prompt requirement to at least one test.

## Making Python Tasks Hard

Prefer bugs involving interactions:

- datetime/timezone plus deduplication
- Decimal rounding plus aggregation order
- parser state plus error recovery
- cache invalidation plus file system changes
- pytest collection plus fixture teardown/reporting
- async cancellation plus cleanup

Avoid tasks where the fix is a single obvious if-statement unless the surrounding framework behavior is subtle.

## Subprocess Test Pattern

```python
def run_cmd(args, cwd, timeout=20):
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
```

On failure, include stderr/stdout in assertion messages. For generated files, assert both existence and parsed content.

## XML/JSON Output Checks

Use parsers:

```python
import json
import xml.etree.ElementTree as ET

data = json.loads(path.read_text())
tree = ET.parse(path)
```

Check semantic fields rather than full formatting unless sorted key order or exact serialization is a prompt requirement.

## tests/test.sh

Use this pattern:

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

Ensure `pytest` and `pytest-json-ctrf` are installed in the Docker image.

## Oracle Pattern

For large repos:

```bash
#!/bin/bash
set -euo pipefail

cd /app
patch -p1 < /solution/fix.patch
python -m pytest <focused upstream or smoke test>
```

For small apps, `solve.sh` may rewrite files directly, but it must implement general behavior and not encode verifier outputs.
