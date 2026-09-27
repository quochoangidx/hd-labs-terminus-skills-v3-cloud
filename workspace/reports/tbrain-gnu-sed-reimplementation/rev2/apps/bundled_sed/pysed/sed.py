#!/usr/bin/env python3
"""Run the bundled GNU sed 4.9 with the required C locale."""
import os
import sys

executable = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gnu-sed")
environment = os.environ.copy()
environment["LC_ALL"] = "C"
os.execve(executable, ["sed", *sys.argv[1:]], environment)
