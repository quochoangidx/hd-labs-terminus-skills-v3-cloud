"""Replay a command sequence against a matchbook package and print what it did.

Usage: python3 run_session.py <package-root> < commands.json

The verifier runs this file from its own read-only copy as an unprivileged user.
After each command it records the returned events, Engine.book() and
Engine.held(), or the kind of exception raised. It decides nothing.
"""

import json
import sys


def main():
    sys.path.insert(0, sys.argv[1])
    from matchbook import Engine

    engine = Engine()
    out = []
    for command in json.load(sys.stdin):
        try:
            events = engine.submit(dict(command))
            out.append({"events": events, "book": engine.book(), "held": list(engine.held())})
        except Exception as exc:  # reported, never judged here
            out.append({"error": type(exc).__name__})
            break
    json.dump(out, sys.stdout)


if __name__ == "__main__":
    main()
