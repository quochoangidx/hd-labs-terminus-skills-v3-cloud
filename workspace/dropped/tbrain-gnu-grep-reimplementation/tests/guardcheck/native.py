"""A program that loads native code through ctypes: the launcher must stop it."""
import ctypes
import ctypes.util

libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")
print("native", libc.abs(-3))
