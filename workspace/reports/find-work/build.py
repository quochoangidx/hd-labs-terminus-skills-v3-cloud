import os, time
def build(root, entries, now):
    for path, kind, size, mode, age, extra in entries:
        p = os.path.join(root, path)
        if kind == "d":
            os.makedirs(p, exist_ok=True)
        elif kind == "f":
            with open(p, "wb") as h:
                h.truncate(size)
        elif kind == "l":
            os.symlink(extra, p)
        elif kind == "h":
            os.link(os.path.join(root, extra), p)
    for path, kind, size, mode, age, extra in sorted(entries, key=lambda e: -e[0].count("/")):
        p = os.path.join(root, path)
        if kind == "h":
            continue
        if kind != "l":
            os.chmod(p, mode)
        os.utime(p, (now - age, now - age), follow_symlinks=False)
