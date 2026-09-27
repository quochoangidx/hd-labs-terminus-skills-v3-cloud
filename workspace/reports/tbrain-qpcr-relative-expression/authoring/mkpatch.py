"""mkpatch.py: write solution/fix.patch as the diff shipped/app -> patched/app (paths relative to /app)."""
import difflib
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-qpcr-relative-expression"
old_root, new_root = HERE / "shipped" / "app", HERE / "patched" / "app"
out = []
for new in sorted(p for p in new_root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
    rel = new.relative_to(new_root).as_posix()
    old = old_root / rel
    a = old.read_text().splitlines(keepends=True) if old.exists() else []
    b = new.read_text().splitlines(keepends=True)
    if a != b:
        out.extend(difflib.unified_diff(a, b, f"a/{rel}", f"b/{rel}"))
(TASK / "solution" / "fix.patch").write_text("".join(out))
print("".join(out).count("\n@@"), "hunks")
