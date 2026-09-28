"""Recompute every sealed expectation in 50-digit decimal arithmetic from the file's
decimal inputs and report the largest gap to the stored double-precision value."""
import json, sys
from decimal import Decimal as D, getcontext
from pathlib import Path
getcontext().prec = 50
T = [(10,"1.700"),(20,"2.060"),(30,"2.290"),(50,"2.580"),(75,"2.820"),(100,"3.000"),(150,"3.300"),
     (200,"3.530"),(300,"3.900"),(400,"4.220"),(500,"4.510"),(600,"4.790")]
T = [(D(a), D(b)) for a, b in T]
X = lambda v: D(repr(float(v)))
def corr(r):
    if T[0][0] <= r <= T[-1][0]:
        for (d0, v0), (d1, v1) in zip(T, T[1:]):
            if d0 <= r <= d1:
                return v0 + (v1 - v0) * (r - d0) / (d1 - d0)
    (d0, v0), (d1, v1) = (T[0], T[1]) if r < T[0][0] else (T[-2], T[-1])
    return v0 + (v1 - v0) * (r.log10() - d0.log10()) / (d1.log10() - d0.log10())
def reduce(b):
    cs = {s["code"]: X(s["correction"]) for s in b["stations"]}
    out = []
    for e in b["events"]:
        dep = X(e["depth_km"]); amps = {}; epi = {}
        for r in e["recordings"]:
            amps.setdefault(r["code"], []).extend(r["amplitudes"]); epi.setdefault(r["code"], X(r["epi_km"]))
        st = {}
        for c, al in amps.items():
            r = (epi[c] ** 2 + dep ** 2).sqrt()
            ms = [(X(a["amplitude_nm"]) / 2 * 2080 * D("1e-6")).log10() + corr(r) + cs[c]
                  for a in al if X(a["amplitude_nm"]) >= 3 * X(a["noise_nm"])]
            st[c] = (r, sum(ms) / len(ms), D(10) <= r <= D(600))
        v = sorted(m for (_, m, k) in st.values() if k)
        ml = None if len(v) < 3 else (v[len(v)//2] if len(v) % 2 else (v[len(v)//2-1] + v[len(v)//2]) / 2)
        out.append((ml, [(st[r["code"]][0], st[r["code"]][1], st[r["code"]][2]) for r in e["recordings"]]))
    return out
worst = D(0); n = 0; flips = 0
for f in sorted(Path(sys.argv[1]).glob("*.jsonl")):
    for line in f.read_text().splitlines():
        row = json.loads(line); hp = reduce(row["bulletin"])
        for ev, (ml, rows) in zip(row["report"]["events"], hp):
            if (ev["ml"] is None) != (ml is None): flips += 1
            elif ml is not None: worst = max(worst, abs(X(ev["ml"]) - ml)); n += 1
            for srow, (r, m, k) in zip(ev["stations"], rows):
                flips += srow["contributes"] is not k
                worst = max(worst, abs(X(srow["distance_km"]) - r), abs(X(srow["ml"]) - m)); n += 2
print(json.dumps({"values_checked": n, "max_abs_gap": float(worst), "flag_or_null_disagreements": flips}))
