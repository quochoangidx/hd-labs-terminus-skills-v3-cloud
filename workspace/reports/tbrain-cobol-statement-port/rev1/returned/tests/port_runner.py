"""Launch an untrusted single-file Python port with only stdlib facilities.

The task asks for a Python implementation, not a wrapper around another job.
The artifact list transfers only wbill.py; this launcher additionally rejects
the ordinary process-spawning APIs that could delegate the work to cat, awk,
or a compiled COBOL executable.
"""

import runpy
import sys


BLOCKED_EVENTS = {
    "ctypes.dlopen",
    "os.exec",
    "os.fork",
    "os.forkpty",
    "os.posix_spawn",
    "os.spawn",
    "os.system",
    "subprocess.Popen",
}


def _audit(event, _args):
    if event in BLOCKED_EVENTS or event.startswith(("os.exec", "os.spawn")):
        raise PermissionError(f"external process delegation is not allowed: {event}")


def main():
    if len(sys.argv) != 5:
        raise SystemExit("usage: port_runner.py PORT CUSTIN PAYIN STMTOUT")
    port, *job_args = sys.argv[1:]
    sys.addaudithook(_audit)
    sys.argv = [port, *job_args]
    runpy.run_path(port, run_name="__main__")


if __name__ == "__main__":
    main()
