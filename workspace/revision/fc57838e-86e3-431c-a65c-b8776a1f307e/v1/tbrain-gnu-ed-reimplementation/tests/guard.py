"""Launcher that runs the delivered ed in this same process under an audit hook.

The task says the program must be built on the Python standard library alone and must
not start other programs. Comparing output with GNU ed cannot see either rule, so every
graded run goes through this launcher instead of straight to the interpreter: it runs
the named program as __main__ with the same argv, standard streams and working
directory, and stops the run when the program starts a process, loads native code, or
imports a module from outside the standard library and its own delivered files.

The launcher holds no expected results and runs with the same unprivileged credentials
as the program it launches, so it belongs to the candidate's side of the comparison
rather than to the verifier.
"""

import os
import runpy
import sys
import sysconfig

MARKER = "pyed-guard: "
STDLIB = tuple(os.path.realpath(p) for p in
               (sysconfig.get_paths()["stdlib"], sysconfig.get_paths()["platstdlib"]))
BLOCKED_PREFIXES = ("subprocess.", "ctypes.", "os.exec", "os.spawn", "os.fork", "os.posix_spawn",
                    "pty.spawn", "_posixsubprocess.")
BLOCKED = {"os.system", "os.startfile", "os.forkpty", "cpython._PySys_ClearAuditHooks"}
ALLOWED_ROOTS = ()


def stop(reason):
    sys.stderr.write(MARKER + reason + "\n")
    sys.stderr.flush()
    try:
        sys.stdout.flush()
    except Exception:
        pass
    os._exit(120)


def hook(event, args):
    if event in BLOCKED or event.startswith(BLOCKED_PREFIXES):
        stop("started another program or loaded native code (%s)" % event)
    if event == "import" and args[1]:
        check_origin(args[0], args[1])


def check_origin(name, origin):
    if not origin or origin in ("built-in", "frozen", "namespace"):
        return
    real = os.path.realpath(origin)
    if not real.startswith(ALLOWED_ROOTS):
        stop("imported %s from outside the standard library (%s)" % (name, real))


class Warden:
    """Runs before the ordinary finders and refuses a module from anywhere else."""

    def __init__(self, finders):
        self.finders = finders

    def find_spec(self, name, path=None, target=None):
        for finder in self.finders:
            find = getattr(finder, "find_spec", None)
            if find is None:
                continue
            spec = find(name, path, target)
            if spec is not None:
                check_origin(name, getattr(spec, "origin", None))
                return spec
        return None

    def invalidate_caches(self):
        for finder in self.finders:
            if hasattr(finder, "invalidate_caches"):
                finder.invalidate_caches()


def main():
    global ALLOWED_ROOTS
    if len(sys.argv) < 2:
        stop("no program to run")
    program = os.path.realpath(sys.argv[1])
    delivered = "/app" if program.startswith("/app" + os.sep) else os.path.dirname(program)
    ALLOWED_ROOTS = STDLIB + (os.path.realpath(delivered),)
    sys.argv = sys.argv[1:]
    sys.path.insert(0, os.path.dirname(program))
    sys.meta_path.insert(0, Warden(list(sys.meta_path)))
    sys.addaudithook(hook)
    status = 0
    try:
        runpy.run_path(program, run_name="__main__")
    except SystemExit as leaving:
        code = leaving.code
        status = 0 if code is None else code if isinstance(code, int) else 1
    try:
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    os._exit(status)


main()
