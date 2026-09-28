"""A program that reaches an installed package through importlib: the launcher must stop it."""
import importlib
import sys

module = importlib.import_module("pytest")
print("installed package loaded", module.__name__, file=sys.stdout)
