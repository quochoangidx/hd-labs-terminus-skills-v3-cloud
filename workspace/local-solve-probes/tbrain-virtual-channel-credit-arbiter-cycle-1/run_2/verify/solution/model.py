"""Cycle-accurate reference model of vc_arb, written from docs/spec.md only.

Also holds the per-family constrained-random stimulus generator and the
stimulus/trace encodings shared with the simulation harness.
"""
import random

NVC = 3
FAMILIES = ["credit", "flush", "runs", "backpressure", "buffer", "config", "reset", "mixed"]


def reset_state():
    return {
        "fifo": [[], [], []],
        "cred": [4, 4, 4],
        "ov": 0, "ovc": 0, "od": 0,
        "last": 2, "run": 2,
    }


def outputs(s):
    """Section 3: every output from registers only."""
    ready = sum((1 << v) for v in range(NVC) if len(s["fifo"][v]) < 2)
    credits = sum(s["cred"][v] << (3 * v) for v in range(NVC))
    return (ready, s["ov"], s["ovc"], s["od"], credits)


def step(s, x):
    """One rising edge. x is a dict of inputs; returns the new state."""
    if not x["rst_n"]:
        return reset_state()
    fifo = [list(f) for f in s["fifo"]]
    cred = list(s["cred"])
    last, run = s["last"], s["run"]
    ov, ovc, od = s["ov"], s["ovc"], s["od"]
    flush = [(x["flush"] >> v) & 1 for v in range(NVC)]

    opp = (ov == 0) or x["out_ready"]
    elig = [len(fifo[v]) > 0 and cred[v] > 0 and not flush[v] for v in range(NVC)]
    grant = None
    if opp:
        if run == 1 and elig[last]:
            grant, run = last, 2
        else:
            for k in (1, 2, 3):
                v = (last + k) % NVC
                if elig[v]:
                    grant, last, run = v, v, 1
                    break
    if grant is None and flush[last]:
        run = 2

    if grant is not None:
        ov, ovc, od = 1, grant, fifo[grant][0]
    elif ov and x["out_ready"]:
        ov, ovc, od = 0, 0, 0

    for v in range(NVC):
        push = (x["in_valid"] >> v) & 1 and len(s["fifo"][v]) < 2
        byte = (x["in_data"] >> (8 * v)) & 0xFF
        if flush[v]:
            fifo[v] = [byte] if push else []
        else:
            if grant == v:
                fifo[v].pop(0)
            if push:
                fifo[v].append(byte)
        base = x["cfg_credits"] if (x["cfg_we"] and x["cfg_vc"] == v) else cred[v]
        n = base - (1 if grant == v else 0) + ((x["cr_ret"] >> v) & 1)
        cred[v] = min(7, max(0, n))

    return {"fifo": fifo, "cred": cred, "ov": ov, "ovc": ovc, "od": od,
            "last": last, "run": run}


def simulate(vectors):
    """Outputs after each edge, starting from reset (vectors begin with reset)."""
    s = reset_state()
    trace = []
    for x in vectors:
        s = step(s, x)
        trace.append(outputs(s))
    return trace


# ---- stimulus encoding (41 bits per cycle, one hex word per line) ----
FIELDS = [("rst_n", 1), ("in_valid", 3), ("in_data", 24), ("out_ready", 1),
          ("cr_ret", 3), ("flush", 3), ("cfg_we", 1), ("cfg_vc", 2), ("cfg_credits", 3)]


def encode(x):
    w = 0
    for name, bits in FIELDS:
        w = (w << bits) | (x[name] & ((1 << bits) - 1))
    return "%011x" % w


def decode_trace_line(line):
    a = line.split()
    return tuple(int(t) for t in a[2:7])


# ---- constrained-random stimulus, per family ----
def _bit(r, p):
    return 1 if r.random() < p else 0


def _bits(r, p):
    return sum(_bit(r, p) << v for v in range(NVC))


def generate(family, seed, cycles=400):
    r = random.Random("%s:%d" % (family, seed))
    P = {
        "credit":       dict(iv=0.6, rdy=0.8, ret=0.35, fl=0.02, cfg=0.15, rst=0.0),
        "flush":        dict(iv=0.7, rdy=0.7, ret=0.5, fl=0.25, cfg=0.02, rst=0.0),
        "runs":         dict(iv=0.8, rdy=0.9, ret=0.6, fl=0.08, cfg=0.02, rst=0.0),
        "backpressure": dict(iv=0.6, rdy=0.45, ret=0.4, fl=0.05, cfg=0.05, rst=0.0),
        "buffer":       dict(iv=0.9, rdy=0.6, ret=0.45, fl=0.05, cfg=0.03, rst=0.0),
        "config":       dict(iv=0.6, rdy=0.8, ret=0.4, fl=0.03, cfg=0.4, rst=0.0),
        "reset":        dict(iv=0.6, rdy=0.7, ret=0.4, fl=0.05, cfg=0.08, rst=0.03),
        "mixed":        dict(iv=0.6, rdy=0.7, ret=0.4, fl=0.08, cfg=0.08, rst=0.01),
    }[family]
    vec = []
    rdy_state = 1
    for c in range(cycles):
        x = {"rst_n": 0 if c < 2 else 1 - _bit(r, P["rst"])}
        # per-segment rate wobble concentrates coincidences
        wob = 0.5 + r.random() if c % 37 == 0 else 1.0
        x["in_valid"] = _bits(r, min(1.0, P["iv"] * wob))
        x["in_data"] = r.getrandbits(24)
        if family == "backpressure":
            if r.random() < 0.2:
                rdy_state ^= 1
            x["out_ready"] = rdy_state if r.random() < 0.85 else 1 - rdy_state
        else:
            x["out_ready"] = _bit(r, P["rdy"])
        x["cr_ret"] = _bits(r, P["ret"])
        x["flush"] = _bits(r, P["fl"])
        x["cfg_we"] = _bit(r, P["cfg"])
        x["cfg_vc"] = r.randrange(4)
        x["cfg_credits"] = r.choice([0, 0, 1, 1, 2, 6, 7, r.randrange(8)])
        if family == "credit" and r.random() < 0.3:
            # starve credits so returns coincide with empty counts
            x["cr_ret"] = _bits(r, 0.1)
        vec.append(x)
    return vec
