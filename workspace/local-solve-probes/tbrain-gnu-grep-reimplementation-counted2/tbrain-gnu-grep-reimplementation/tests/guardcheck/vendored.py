"""A program that imports code from outside its own files: the launcher must stop it."""
import sys

sys.path.insert(0, "/opt/pygrepguard/guardvendor")
import thirdparty  # noqa: E402

print(thirdparty.NAME)
