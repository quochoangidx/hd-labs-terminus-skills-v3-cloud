#!/usr/bin/env python3
"""cmp.py: run each case (stdin, args...) in the sedlab container through GNU sed and the
reference; print both. Cases from a JSON list [[input, [args...]], ...] on argv[1] or stdin."""
import json, os, subprocess, sys
cases = json.load(open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin)
bad = 0
for inp, args in cases:
    res = []
    for cmd in (["sed"], ["python3", "/ref/sed.py"]):
        p = subprocess.run(["docker", "exec", "-i", "-e", "LC_ALL=C", "-w", "/tmp", os.environ.get("SEDLAB", "sedlab"), "timeout", "5"] + cmd + args,
                           input=inp.encode("latin-1"), capture_output=True)
        res.append((p.stdout, p.returncode))
    same = res[0] == res[1]
    bad += not same
    print("OK  " if same else "DIFF", args, repr(inp[:40]), "sed=", res[0], "" if same else f"ref={res[1]}")
print("diffs:", bad)
