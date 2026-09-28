"""Source entry point; the editor itself is delivered as compiled bytecode (implementation.pyc)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import implementation  # noqa: E402

sys.exit(implementation.main(sys.argv[1:]))
