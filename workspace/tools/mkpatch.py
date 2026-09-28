"""mkpatch.py <orig-root> <fixed-root> <out.patch> — git-style unified diff of two trees, paths relative to roots."""
import difflib, os, sys
a_root, b_root, out = sys.argv[1:4]
prefix = sys.argv[4] if len(sys.argv) > 4 else ""
files = set()
for root in (a_root, b_root):
    for d, _, fs in os.walk(root):
        if "__pycache__" in d: continue
        for f in fs:
            if f.endswith(".pyc") or f == ".DS_Store": continue
            files.add(os.path.relpath(os.path.join(d, f), root))
chunks = []
for rel in sorted(files):
    pa, pb = os.path.join(a_root, rel), os.path.join(b_root, rel)
    a = open(pa).read().splitlines(True) if os.path.exists(pa) else []
    b = open(pb).read().splitlines(True) if os.path.exists(pb) else []
    if a == b: continue
    name = prefix + rel
    diff = list(difflib.unified_diff(a, b, "a/" + name if a else "/dev/null", "b/" + name if b else "/dev/null", n=int(os.environ.get("CTX", "3"))))
    head = f"diff --git a/{name} b/{name}\n" + ("new file mode 100644\n" if not a else "")
    chunks.append(head + "".join(diff))
open(out, "w").write("".join(chunks))
