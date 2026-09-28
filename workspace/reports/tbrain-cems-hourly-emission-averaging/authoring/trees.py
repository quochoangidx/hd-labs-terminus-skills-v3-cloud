"""Load a cemsqr tree in process (authoring only)."""
import importlib
import sys
from pathlib import Path


def load(app_dir):
    for name in [m for m in sys.modules if m == "cemsqr" or m.startswith("cemsqr.")]:
        del sys.modules[name]
    src = str(Path(app_dir).resolve() / "src")
    sys.path.insert(0, src)
    try:
        return importlib.import_module("cemsqr")
    finally:
        sys.path.remove(src)
