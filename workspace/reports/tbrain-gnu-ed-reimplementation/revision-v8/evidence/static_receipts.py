"""Snapshot-bound receipts for the v8 findings answered by a contract or scope edit, or disputed.
Run from the repo root: python3 <this> ; docker must have edv8-verifier (tests/ of the repaired tree)."""
import json, os, subprocess, sys, pathlib, importlib
ROOT = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / ".agent/skills/terminus-regular-task-authoring/scripts"))
from revision_ledger_check import tree_hash
RET = ROOT / "workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v8/tbrain-gnu-ed-reimplementation"
REP = ROOT / "workspace/tasks/tbrain-gnu-ed-reimplementation"
OUT = pathlib.Path(__file__).resolve().parents[1] / "receipts"
H = {"returned": tree_hash(RET), "repaired": tree_hash(REP)}
SNAP = {"returned": RET, "repaired": REP}

def load(tag):
    for m in ("scope", "generated"):
        sys.modules.pop(m, None)
    sys.path.insert(0, str(SNAP[tag] / "tests"))
    scope = importlib.import_module("scope"); gen = importlib.import_module("generated")
    sys.path.pop(0)
    return scope, gen

def corpus(tag):
    t = SNAP[tag] / "tests/cases"
    fx = json.load(open(t / "fixtures.json")); ro = json.load(open(t / "roster.json"))
    out = []
    for fam in ro["families"]:
        for i, l in enumerate(open(t / f"{fam}.jsonl")):
            r = json.loads(l); out.append({"family": fam, "row": i, **r, "files": fx[r["fixture"]]})
    return out

SELF = "python3 workspace/reports/tbrain-gnu-ed-reimplementation/revision-v8/evidence/static_receipts.py"
LAST = {}

def write(tag, name, body):
    (OUT / tag).mkdir(parents=True, exist_ok=True)
    run = LAST.pop("run", None)
    cmd = {"command": run[0], "exit_code": run[1]} if run else {"command": f"{SELF}  # static read of {SNAP[tag].relative_to(ROOT)}", "exit_code": 0}
    json.dump({"schema_version": 1, "task_snapshot_sha256": H[tag], **cmd, **body}, open(OUT / tag / f"{name}.json", "w"), indent=1)

def docker(tag, script):
    t = SNAP[tag]
    argv = ["docker", "run", "--rm", "--network", "none", "-v", f"{t}/tests:/t:ro", "-v", f"{t}/solution:/sol:ro", "-v", f"{pathlib.Path(__file__).resolve().parent}:/ev:ro",
            "--entrypoint", "bash", "edv8-verifier", "-c", script]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    LAST["run"] = (" ".join(argv), p.returncode)
    return p.stdout

# finding 1: the excluded \> escape
for tag in ("returned", "repaired"):
    scope, _ = load(tag)
    hits = [c for c in corpus(tag) if "\\>" in c["script"] or any(f"\\{e}" in c["script"] for e in "bBwWsS<`'")]
    write(tag, "excluded-escapes", {"finding": "v8-1", "cases_with_an_excluded_escape": [
        {"family": c["family"], "row": c["row"], "script": c["script"], "scope_problems": scope.case_problems(c)} for c in hits
        if any(p.startswith("the escape") for p in (scope.case_problems(c) or ["the escape?"]))],
        "scope_checks_escapes": hasattr(scope, "escape_problems")})

# finding 12: the % address in the generated grammar
for tag in ("returned", "repaired"):
    scope, gen = load(tag)
    b = gen.generate()
    pct = [(k, c["script"]) for k, v in b.items() for c in v
           if any(line.lstrip(" \t").startswith("%") for line in scope.command_lines(c["script"]))]
    write(tag, "percent-address", {"finding": "v8-12", "percent_in_RANGES": "%" in gen.RANGES,
        "generated_scripts_with_a_percent_address": len(pct), "first": pct[:3],
        "scope_rejects_percent": bool(scope.command_problems("%p")) })

# finding 8: the ! argument rule against s!a!b!p
for tag in ("returned", "repaired"):
    ins = open(SNAP[tag] / "instruction.md").read()
    rows = [(c["family"], c["row"], c["script"]) for c in corpus(tag) if "s!" in c["script"]]
    write(tag, "bang-argument", {"finding": "v8-8",
        "instruction_excludes_any_command_argument": "no FILE or command argument starts with `!`" in ins,
        "instruction_excludes_file_names_only": "no file name, on the command line or after a command, starts with `!`" in ins,
        "graded_s_with_bang_delimiter": rows})

# finding 3: stdlib-only promise and the /app import rule
for tag in ("returned", "repaired"):
    ins = open(SNAP[tag] / "instruction.md").read()
    out = docker(tag, "mkdir -p /app/pyed/vend/site-packages; echo 'NAME=\"v\"' > /app/pyed/vend/site-packages/helper.py; "
                 "printf 'import sys\\nsys.path.insert(0, \"/app/pyed/vend/site-packages\")\\nimport helper\\nprint(helper.NAME)\\n' > /app/pyed/ed.py; "
                 "cd /tmp; python3 /t/guard.py /app/pyed/ed.py; echo status=$?")
    write(tag, "delivered-imports", {"finding": "v8-3",
        "instruction_promises_stdlib_only": "Use only the Python standard library" in ins,
        "instruction_allows_python_files_under_app": "Python source files under `/app`" in ins,
        "delivered_module_under_a_site-packages_dir": out.strip()})

# finding 14: SQLite extension loading
for tag in ("returned", "repaired"):
    out = docker(tag, "cd /tmp; cp /t/guard.py /tmp/g.py; cp /ev/sqlite_probe.py /tmp/p.py; chmod 644 /tmp/*.py; "
                 "setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs -- python3 /tmp/g.py /tmp/p.py 2>&1; echo status=$?")
    write(tag, "sqlite-extension", {"finding": "v8-14", "run": out.strip()})

# findings 9 and 10: the reference against GNU ed on the findings' own scripts (reference unchanged by the repair)
probe = r'''
t(){ n=$1; fc=$2; kind=$3; sc=$4; shift 4
  for impl in ed ref; do d=$(mktemp -d); cd $d; [ -n "$fc" ] && printf "$fc" > f; printf "$sc" > /tmp/s
    if [ $impl = ed ]; then cmd=/usr/bin/ed; else cmd="python3 /sol/pyed/ed.py"; fi
    if [ $kind = file ]; then out=$($cmd "$@" < /tmp/s 2>/dev/null; echo "status=$?"); else out=$(cat /tmp/s | $cmd "$@" 2>/dev/null; echo "status=$?"); fi
    echo "$n $impl $(echo "$out" | tr '\n' '|') files=$(for x in *; do printf '%s:' "$x"; od -An -c "$x" | tr -s ' ' | tr '\n' ' '; done)"; cd /; done; }
t v8-9 '0\n' file '1s/[-a]/X/p\nQ\n' -s f
t v8-9-ctl '0\n-\na\n' pipe 'g/[-a]/p\nQ\n' -s f
t v8-10 'x\n' pipe '1m1\nq\n' f
t v8-10-range 'x\ny\n' pipe '1,2m2\nq\n' f
'''
write("returned", "reference-findings-9-10", {"findings": ["v8-9", "v8-10"], "gnu_ed_versus_reference": docker("returned", probe).strip().split("\n")})

# finding 15: what the agent can see
env = sorted(str(p.relative_to(RET / "environment")) for p in (RET / "environment").rglob("*") if p.is_file())
write("returned", "lookup-table-inputs", {"finding": "v8-15", "agent_image_files": env,
    "tests_in_agent_image": any("tests" in e or "cases" in e or "generated" in e for e in env),
    "seed_lives_in": "tests/generated.py (verifier image only)"})
print("ok", H)
