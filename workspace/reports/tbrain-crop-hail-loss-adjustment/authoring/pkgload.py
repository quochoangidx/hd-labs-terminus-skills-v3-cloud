"""Load a copy of the hailadj package from an app directory under a fresh module name."""

import importlib.util
import sys as _sys
_sys.dont_write_bytecode = True
import itertools
import sys
from pathlib import Path

_counter = itertools.count()


def load(app_dir):
    pkg_dir = Path(app_dir) / "src" / "hailadj"
    name = f"hailadj_copy{next(_counter)}"
    spec = importlib.util.spec_from_file_location(name, pkg_dir / "__init__.py",
                                                  submodule_search_locations=[str(pkg_dir)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
