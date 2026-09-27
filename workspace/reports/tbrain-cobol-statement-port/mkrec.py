import sys
def hdr(date, region):
    return ("H" + f"{date:08d}" + f"{region:<20.20}").ljust(80)
def cust(acct, name, tariff, prev, curr, days, arrears_cents, paid_cents, negative_zero=False):
    sign = "-" if arrears_cents < 0 or negative_zero else "+"
    s = ("C" + f"{acct:<8.8}" + f"{name:<24.24}" + tariff + f"{prev:06d}" + f"{curr:06d}" + f"{days:03d}"
         + sign + f"{abs(arrears_cents):07d}" + f"{paid_cents:07d}")
    assert len(s) == 64, len(s)
    return s.ljust(80)
if __name__ == "__main__":
    rows = [hdr(20250331, "NORTH DISTRICT"),
            cust("10004821", "jane  o'hara", "D", 12345, 12612, 90, 0, 0),
            cust("10009917", "ACME BOTTLING LTD", "C", 400100, 401350, 91, 12550, 125500),
            cust("20000456", "  smith", "L", 999950, 120, 92, -4210, 0),
            cust("20000999", "MARY-ANN O'CONNOR", "X", 100, 200, 90, 0, 0),
            cust("30001234", "WEST WORKS", "C", 0, 0, 0, 0, 0),
            cust("30005555", "harbour cafe", "C", 1000, 1000, 29, -99999, 20000)]
    open(sys.argv[1], "w").write("\n".join(rows) + "\n")
