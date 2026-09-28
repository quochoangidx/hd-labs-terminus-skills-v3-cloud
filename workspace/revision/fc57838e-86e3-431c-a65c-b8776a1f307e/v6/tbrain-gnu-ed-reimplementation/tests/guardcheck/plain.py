"""An ordinary standard-library program: the launcher must let it run and keep its status."""
import dataclasses
import logging
import os
import re
import subprocess  # imported, never used to start anything
import sys
import traceback


@dataclasses.dataclass
class Pair:
    left: str = "a"
    right: str = "b"


try:
    raise ValueError("handled")
except ValueError:
    logging.getLogger("plain").debug(traceback.format_exc())
pair = Pair()
assert subprocess.PIPE == -1
sys.stdout.write("plain %s %s\n" % (os.path.basename(sys.argv[0]), " ".join(sys.argv[1:])))
sys.stdout.write("re %s\n" % re.sub(pair.left, pair.right, "aa"))
sys.exit(3 if sys.argv[1:] == ["fail"] else 0)
