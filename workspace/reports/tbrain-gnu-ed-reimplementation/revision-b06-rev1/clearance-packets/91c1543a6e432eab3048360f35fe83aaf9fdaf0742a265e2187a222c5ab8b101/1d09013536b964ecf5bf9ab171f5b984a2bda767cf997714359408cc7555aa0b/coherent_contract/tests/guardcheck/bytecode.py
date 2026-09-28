"""A program that imports its code from a compiled module with no Python source beside
it (legacy.pyc, written next to it by the test): the launcher must stop it."""
import legacy

print("bytecode loaded", legacy.NAME)
