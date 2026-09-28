"""A program that loads a fresh copy of the C helper behind subprocess to get its original
fork-and-exec function back: the launcher must stop it."""
import sys

del sys.modules["_posixsubprocess"]
import _posixsubprocess  # noqa: E402

print("GNU ed started", _posixsubprocess.fork_exec)
