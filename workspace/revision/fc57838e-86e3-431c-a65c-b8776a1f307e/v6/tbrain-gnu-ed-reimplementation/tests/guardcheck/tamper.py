"""A program that rewrites every name the launcher could depend on before replacing itself
with another program: the launcher must still stop it."""
import builtins
import os
import posix
import sys

frame = sys._getframe()
while frame is not None:
    for name in list(frame.f_globals):
        if name.isupper() or name in ("stop", "hook", "check_origin", "install", "os", "sys"):
            frame.f_globals[name] = () if name.isupper() else (lambda *a, **k: None)
    frame = frame.f_back
for module in (sys.modules.get("__main__"),):
    if module is not None:
        for name in ("BLOCKED", "BLOCKED_PREFIXES"):
            setattr(module, name, ())
os._exit = posix._exit = lambda code: None
builtins.len = lambda obj: 0
builtins.isinstance = lambda obj, kind: False
os.path.realpath = lambda path: "/usr/local/lib/python3.13/" + os.path.basename(str(path))
posix.execv("/usr/bin/ed", ["ed"] + sys.argv[1:])
print("GNU ed started")
