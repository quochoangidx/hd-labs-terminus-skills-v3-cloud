"""A program that replaces itself with another program: the launcher must stop it."""
import os
import sys

os.execv("/bin/grep", ["grep"] + sys.argv[1:])
