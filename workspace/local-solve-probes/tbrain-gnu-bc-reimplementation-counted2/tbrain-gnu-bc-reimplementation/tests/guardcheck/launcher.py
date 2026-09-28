"""A program that delegates its work to another program: the launcher must stop it."""
import subprocess
import sys

sys.exit(subprocess.run(["/usr/bin/bc"] + sys.argv[1:], stdin=sys.stdin, check=False).returncode)
