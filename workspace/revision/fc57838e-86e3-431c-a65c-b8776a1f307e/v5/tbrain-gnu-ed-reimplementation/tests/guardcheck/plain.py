"""An ordinary standard-library program: the launcher must let it run and keep its status."""
import os
import re
import sys

sys.stdout.write("plain %s %s\n" % (os.path.basename(sys.argv[0]), " ".join(sys.argv[1:])))
sys.stdout.write("re %s\n" % re.sub("a", "b", "aa"))
sys.exit(3 if sys.argv[1:] == ["fail"] else 0)
