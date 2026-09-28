"""A program that calls into the C library for its work: the launcher must stop it."""
import ctypes
import ctypes.util
import sys

libc = ctypes.CDLL(ctypes.util.find_library("c"))
print("libc loaded", bool(libc), file=sys.stdout)
