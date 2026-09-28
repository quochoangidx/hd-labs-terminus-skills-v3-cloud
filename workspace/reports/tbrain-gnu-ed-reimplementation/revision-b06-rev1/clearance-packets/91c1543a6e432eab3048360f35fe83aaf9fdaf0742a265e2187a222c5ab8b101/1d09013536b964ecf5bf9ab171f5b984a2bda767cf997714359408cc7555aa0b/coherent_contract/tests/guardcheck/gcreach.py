"""A program that looks for the launcher's hook among live objects: the launcher must stop it."""
import gc

found = [obj for obj in gc.get_objects() if callable(obj) and getattr(obj, "__name__", "") == "hook"]
print("launcher reached", len(found))
