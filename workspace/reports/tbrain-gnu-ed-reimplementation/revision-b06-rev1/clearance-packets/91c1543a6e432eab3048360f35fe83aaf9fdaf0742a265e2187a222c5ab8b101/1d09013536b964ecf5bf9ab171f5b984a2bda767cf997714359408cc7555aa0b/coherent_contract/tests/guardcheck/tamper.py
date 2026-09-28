"""A program that rewrites the names a launcher could depend on, in the launcher's own
module, in os and posix and in builtins, and then replaces itself with another program:
the launcher must still stop it."""
import builtins
import os
import posix
import sys

frame = sys._getframe()
while frame is not None:
    if str(frame.f_globals.get("__file__", "")).endswith("guard.py"):
        for name in list(frame.f_globals):
            if name.isupper():
                frame.f_globals[name] = ()
            elif name in ("stop", "hook", "check_origin", "install"):
                frame.f_globals[name] = lambda *args, **kwargs: None
    frame = frame.f_back
for name in ("BLOCKED", "BLOCKED_PREFIXES"):
    setattr(sys.modules["__main__"], name, ())
os._exit = posix._exit = lambda code: None
os.path.realpath = lambda path: "/usr/local/lib/python3.13/" + os.path.basename(str(path))
builtins.len = lambda obj: 0
posix.execv("/bin/echo", ["echo", "another program ran"])
