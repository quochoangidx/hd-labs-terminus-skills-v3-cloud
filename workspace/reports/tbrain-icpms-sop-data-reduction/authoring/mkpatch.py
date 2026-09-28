"""mkpatch.py VARIANT_APP OUT.patch: unified diff of environment/app/src -> VARIANT_APP/src, paths app/src/... (a/ b/ prefixes)."""
import difflib, sys
from pathlib import Path
TASK = Path(__file__).resolve().parents[3] / "tasks" / "tbrain-icpms-sop-data-reduction"
base = TASK / "environment" / "app" / "src"
var = Path(sys.argv[1]) / "src"
out = []
names = sorted({p.relative_to(base).as_posix() for p in base.rglob("*.py")} | {p.relative_to(var).as_posix() for p in var.rglob("*.py")})
for rel in names:
    a = (base / rel).read_text().splitlines(keepends=True) if (base / rel).exists() else []
    b = (var / rel).read_text().splitlines(keepends=True) if (var / rel).exists() else []
    if a == b:
        continue
    out.append(f"diff --git a/app/src/{rel} b/app/src/{rel}\n")
    out.extend(difflib.unified_diff(a, b, f"a/app/src/{rel}", f"b/app/src/{rel}", n=3))
Path(sys.argv[2]).write_text("".join(out))
print(f"{sys.argv[2]}: {sum(1 for l in out if l.startswith('@@'))} hunks")
