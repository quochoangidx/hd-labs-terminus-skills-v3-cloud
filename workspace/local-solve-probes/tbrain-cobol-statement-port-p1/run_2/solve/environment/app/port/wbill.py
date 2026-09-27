"""Python replacement for the WBILL job step (see ../legacy/WBILL.cbl).

Usage: python3 wbill.py INPUT OUTPUT
"""

import sys


def main(argv):
    if len(argv) != 3:
        sys.exit("usage: wbill.py INPUT OUTPUT")
    raise NotImplementedError("the WBILL port has not been written yet")


if __name__ == "__main__":
    main(sys.argv)
