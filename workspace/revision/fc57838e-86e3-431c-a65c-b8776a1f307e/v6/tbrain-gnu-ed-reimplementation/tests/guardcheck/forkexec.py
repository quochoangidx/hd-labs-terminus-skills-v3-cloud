"""A program that starts another program through the C helper behind subprocess, which
raises no audit event of its own: the launcher must stop it."""
import os
import sys

import _posixsubprocess

read_end, write_end = os.pipe()
pid = _posixsubprocess.fork_exec(
    [b"/usr/bin/ed"] + [a.encode() for a in sys.argv[1:]], [b"/usr/bin/ed"], True, (write_end,),
    None, None, -1, -1, -1, -1, -1, -1, read_end, write_end, False, False, -1, None, None, None,
    -1, None, False)
os.waitpid(pid, 0)
print("GNU ed started")
