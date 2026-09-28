"""A program that replaces itself with another program: the launcher must stop it."""
import os
import sys

os.execv("/usr/bin/bc", ["bc"] + sys.argv[1:])
