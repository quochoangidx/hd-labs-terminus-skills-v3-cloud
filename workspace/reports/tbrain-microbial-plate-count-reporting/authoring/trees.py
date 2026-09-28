"""Load a platecount package tree under a unique module name (authoring only)."""

import importlib.util
import itertools
import shutil
import subprocess
import sys
from pathlib import Path

from gen import TASK

_n = itertools.count()
SHIPPED_SRC = TASK / "environment" / "app" / "src" / "platecount"


def load(pkg_dir):
    name = f"platecount_{next(_n)}"
    spec = importlib.util.spec_from_file_location(name, Path(pkg_dir) / "__init__.py",
                                                  submodule_search_locations=[str(pkg_dir)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def oracle_tree(dest):
    """Copy environment/app to dest and apply solution/fix.patch; return the package dir."""
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(TASK / "environment" / "app", dest / "app")
    subprocess.run(["patch", "-s", "-p1", "--no-backup-if-mismatch", "-i", str(TASK / "solution" / "fix.patch")],
                   cwd=dest, check=True)
    return dest / "app" / "src" / "platecount"
