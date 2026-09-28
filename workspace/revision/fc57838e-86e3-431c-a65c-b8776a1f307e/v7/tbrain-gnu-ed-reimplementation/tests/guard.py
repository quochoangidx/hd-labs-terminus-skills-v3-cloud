"""Launcher that runs the delivered ed in this same process under an audit hook.

The task says the program must be built on the Python standard library alone, must not
load native code and must not start other programs. Comparing output with GNU ed cannot
see those rules, so every graded run goes through this launcher instead of straight to
the interpreter: it runs the named program as __main__ with the same argv, standard
streams and working directory, and stops the run when the program starts a process,
loads native code, or imports a module from outside the standard library and its own
delivered files.

The program runs in the launcher's process, so nothing it can reach may decide the
policy. The rules live only in the closure of the audit hook, which nothing else refers
to once it is installed: the tuples are constants, the functions it calls are the
interpreter's own builtins captured before the program starts, and the garbage-collector
calls that could hand the program that closure are themselves stopped. The one piece of
policy the program can see, the import warden on sys.meta_path, is compared with a
snapshot held in that closure on every import, so replacing or editing it ends the run.
The C helper that forks and executes for subprocess raises no audit event of its own,
so it is replaced before the program starts and a fresh copy of it counts as native
code.

The launcher holds no expected results and runs with the same unprivileged credentials
as the program it launches, so it belongs to the candidate's side of the comparison
rather than to the verifier.
"""

import posix
import runpy
import sys
import sysconfig


def install(delivered):
    """Install the hook and the warden; return nothing the program could use."""
    # the interpreter's own functions and types, captured before the program runs:
    # the program can rebind names in os, posixpath, builtins or this module, but not
    # the objects held here
    exit_now = posix._exit
    write = posix.write
    lstat = posix.lstat
    readlink = posix.readlink
    getcwd = posix.getcwd
    sys_mod = sys
    str_, bytes_, type_, len_, dict_, list_ = str, bytes, type, len, dict, list
    getattr_, hasattr_, isinstance_ = getattr, hasattr, isinstance
    os_error, any_error = OSError, Exception

    def realpath(path):
        """os.path.realpath from builtins only, so patching os or posixpath changes nothing."""
        path = str_(path)
        if not path.startswith("/"):
            path = getcwd() + "/" + path
        parts = [p for p in path.split("/") if p and p != "."]
        resolved = []
        hops = 0
        while parts:
            part = parts.pop(0)
            if part == "..":
                if resolved:
                    resolved.pop()
                continue
            candidate = "/" + "/".join(resolved + [part])
            try:
                mode = lstat(candidate).st_mode
            except os_error:
                resolved.append(part)
                continue
            if mode & 0o170000 == 0o120000:
                hops += 1
                if hops > 40:
                    return candidate
                target = readlink(candidate)
                if target.startswith("/"):
                    resolved = []
                parts = [p for p in target.split("/") if p and p != "."] + parts
                continue
            resolved.append(part)
        return "/" + "/".join(resolved)

    paths = sysconfig.get_paths()
    stdlib = tuple(sorted({realpath(paths["stdlib"]) + "/", realpath(paths["platstdlib"]) + "/"}))
    allowed = stdlib + (realpath(delivered) + "/",)
    native_suffixes = (".so", ".pyd", ".dylib")

    def stop(reason):
        try:
            write(2, ("pyed-guard: " + reason + "\n").encode("utf-8", "replace"))
        except any_error:
            pass
        try:
            sys_mod.stdout.flush()
        except any_error:
            pass
        exit_now(120)

    def origin_problem(name, origin):
        if not origin or origin in ("built-in", "frozen", "namespace"):
            return None
        real = realpath(origin)
        # site-packages lives inside the standard-library directory, so a prefix test
        # alone would count every installed package as standard library
        for part in real.split("/"):
            if part.startswith(("site-packages", "dist-packages", "site-python")) or ".egg" in part:
                return "imported %s from an installed package (%s)" % (name, real)
        if real.endswith(native_suffixes) and not real.startswith(stdlib):
            return "loaded native code for %s (%s)" % (name, real)
        if not real.startswith(allowed):
            return "imported %s from outside the standard library (%s)" % (name, real)
        return None

    class Warden:
        """Runs before the ordinary finders and refuses a module from anywhere else."""

        __slots__ = ("finders",)

        def __init__(self, finders):
            self.finders = finders

        def find_spec(self, name, path=None, target=None):
            for finder in self.finders:
                find = getattr_(finder, "find_spec", None)
                if find is None:
                    continue
                spec = find(name, path, target)
                if spec is not None:
                    problem = origin_problem(name, getattr_(spec, "origin", None))
                    if problem:
                        stop(problem)
                    return spec
            return None

        def invalidate_caches(self):
            for finder in self.finders:
                if hasattr_(finder, "invalidate_caches"):
                    finder.invalidate_caches()

    finders = tuple(sys.meta_path)
    warden = Warden(finders)
    find_spec = Warden.find_spec
    warden_type = Warden
    class_dict = dict(Warden.__dict__)

    def warden_intact():
        meta = sys_mod.meta_path
        return (type_(meta) is list_ and len_(meta) > 0 and meta[0] is warden
                and type_(warden) is warden_type and warden.finders is finders
                and warden_type.find_spec is find_spec and dict_(warden_type.__dict__) == class_dict)

    process = ("os.exec", "os.spawn", "os.fork", "os.forkpty", "os.posix_spawn", "os.system",
               "os.startfile", "pty.spawn", "subprocess.", "ctypes.", "_posixsubprocess.")
    reach = ("gc.get_objects", "gc.get_referrers", "gc.get_referents", "cpython._PySys_ClearAuditHooks")

    def hook(event, args):
        if event.startswith(process):
            stop("started another program or loaded native code (%s)" % event)
        if event in reach:
            stop("reached into the launcher (%s)" % event)
        if event == "object.__setattr__" and len_(args) > 1 and args[1] == "__code__":
            stop("replaced the code of a function (%s)" % event)
        if event == "open" and args:
            where = args[0]
            if isinstance_(where, bytes_):
                where = where.decode("utf-8", "replace")
            if isinstance_(where, str_) and ("/site-packages/" in where or "/dist-packages/" in where):
                stop("read an installed package (%s)" % where)
        if event == "import":
            if args[0] == "_posixsubprocess" or args[0] == "_ctypes":
                stop("loaded native code for %s" % args[0])
            if not warden_intact():
                stop("changed the import warden")
            problem = origin_problem(args[0], args[1])
            if problem:
                stop(problem)

    def refuse(*_args, **_kwargs):
        stop("started another program (_posixsubprocess.fork_exec)")

    # subprocess reaches fork and exec through a C helper that raises no audit event;
    # replace it before the program can import it, and treat any fresh copy of the
    # helper as native code (the hook stops a second import of it)
    import subprocess
    import _posixsubprocess
    _posixsubprocess.fork_exec = refuse
    subprocess._fork_exec = refuse
    sys.meta_path.insert(0, warden)
    sys.addaudithook(hook)


def main():
    if len(sys.argv) < 2:
        posix.write(2, b"pyed-guard: no program to run\n")
        posix._exit(120)
    program = sys.argv[1]
    if not program.startswith("/"):
        program = posix.getcwd() + "/" + program
    folder = program.rsplit("/", 1)[0] or "/"
    delivered = "/app" if program.startswith("/app/") else folder
    sys.argv = sys.argv[1:]
    sys.path.insert(0, folder)
    install(delivered)
    status = 0
    try:
        runpy.run_path(program, run_name="__main__")
    except SystemExit as leaving:
        code = leaving.code
        status = 0 if code is None else code if isinstance(code, int) else 1
    except BaseException as error:  # an uncaught error ends the run like the interpreter would
        try:
            posix.write(2, ("%s: %s\n" % (type(error).__name__, error)).encode("utf-8", "replace"))
        except Exception:
            pass
        status = 1
    try:
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    posix._exit(status)


main()
