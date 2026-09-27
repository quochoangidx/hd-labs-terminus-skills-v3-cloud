"""Every finding this revision answered with a case still has that case in the corpus.

A coverage finding is answered by a fixture, and a fixture is one edit away from being
dropped again. This reads the map written with the revision and fails when a case it
names is no longer in tests/cases, or when a finding in the map has no case at all.

usage: check_coverage_map.py <task-folder> <coverage-map.json>
"""
import json
import sys
from pathlib import Path


def key(case):
    return (tuple(case["args"]), case["stdin"], case["script"],
            json.dumps(case["files"], sort_keys=True))


def expand(text):
    """Mirror the verifier: a fixture file is its text or a compact long-run form."""
    if isinstance(text, str):
        return text
    return text["repeat"] * text["count"] + text.get("then", "")


def load_corpus(task):
    """The corpus as the verifier loads it: a file per family, fixtures shared by name."""
    case_dir = task / "tests" / "cases"
    raw = json.loads((case_dir / "fixtures.json").read_text(encoding="utf-8"))
    fixtures = {name: [[fname, expand(text)] for fname, text in files]
                for name, files in raw.items()}
    roster = json.loads((case_dir / "roster.json").read_text(encoding="utf-8"))
    corpus = set()
    for family in roster["families"]:
        for line in (case_dir / f"{family}.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            corpus.add(key({"args": row["args"], "stdin": row["stdin"], "script": row["script"],
                            "files": fixtures[row["fixture"]]}))
    return corpus


def main():
    task, map_path = Path(sys.argv[1]), Path(sys.argv[2])
    corpus = load_corpus(task)
    mapping = json.loads(map_path.read_text(encoding="utf-8"))
    missing = []
    for finding, entry in sorted(mapping["findings"].items(), key=lambda kv: int(kv[0])):
        if not entry["cases"]:
            missing.append(f"finding {finding}: the map names no case")
        for case in entry["cases"]:
            if key(case) not in corpus:
                missing.append(f"finding {finding}: {case['script']!r} is no longer in the corpus")
    print(f"{len(mapping['findings'])} findings mapped, {len(corpus)} cases in the corpus, "
          f"{len(missing)} missing")
    for line in missing:
        print(" ", line)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
