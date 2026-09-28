"""Load a copy of the `commission` package from an app directory under a private module name."""

import importlib.util
import sys
from pathlib import Path


def load(app_dir, alias):
    src = Path(app_dir) / "src" / "commission"
    spec = importlib.util.spec_from_file_location(alias, src / "__init__.py", submodule_search_locations=[str(src)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod
