#!/bin/bash
# mkpatch.sh <base-parent> <variant-parent>: git-style diff of app/ (a/app/..., b/app/...)
find "$1" "$2" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null
cd "$1/.." && diff -ruN "$(basename $1)/app" "$2/app" | python3 -c "
import sys,re
for line in sys.stdin:
    if line.startswith('diff '):
        continue
    m=re.match(r'^(---|\+\+\+) (\S+)', line)
    if m:
        path=m.group(2); rel=path[path.index('app/'):]
        if m.group(1)=='---':
            sys.stdout.write('diff --git a/%s b/%s\n'%(rel,rel))
        line='%s %s/%s\n'%(m.group(1), 'a' if m.group(1)=='---' else 'b', rel)
    sys.stdout.write(line)
"
