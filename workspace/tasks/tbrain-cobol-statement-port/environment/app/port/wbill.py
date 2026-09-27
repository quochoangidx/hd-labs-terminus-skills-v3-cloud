"""Python replacement for the WBILL job step (see ../legacy/WBILL.cbl).

Usage: python3 wbill.py READINGS PAYMENTS OUTPUT
"""

import sys


def main(argv):
    if len(argv) != 4:
        sys.exit("usage: wbill.py READINGS PAYMENTS OUTPUT")
    raise NotImplementedError("the WBILL port has not been written yet")


if __name__ == "__main__":
    main(sys.argv)
