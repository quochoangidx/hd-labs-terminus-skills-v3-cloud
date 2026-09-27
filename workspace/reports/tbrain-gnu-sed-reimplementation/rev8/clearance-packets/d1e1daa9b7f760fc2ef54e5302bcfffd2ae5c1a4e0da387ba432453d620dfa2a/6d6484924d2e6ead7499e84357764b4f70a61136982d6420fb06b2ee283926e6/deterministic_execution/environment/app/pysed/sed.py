"""pysed: a GNU sed 4.9 replacement in pure Python.

Usage: python3 /app/pysed/sed.py [OPTION]... {script-only-if-no-other-script} [input-file]...
"""

import sys


def main(argv):
    sys.stderr.write("pysed: not implemented yet\n")
    return 4


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
