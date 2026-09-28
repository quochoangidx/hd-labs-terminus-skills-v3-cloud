"""Import a copy of the rebate package from <app_dir>/src under a unique name (authoring only)."""
import importlib.util
import sys
from pathlib import Path

_n = [0]


def load(src_dir):
    _n[0] += 1
    name = f"rebate_copy{_n[0]}"
    init = Path(src_dir) / "rebate" / "__init__.py"
    spec = importlib.util.spec_from_file_location(name, init, submodule_search_locations=[str(init.parent)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
