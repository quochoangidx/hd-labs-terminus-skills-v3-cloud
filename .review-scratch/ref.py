QMIN, QMAX = -128, 127


def rnd(x):
    n, d = float(x).as_integer_ratio()
    q, r = divmod(abs(n), d)
    if 2 * r >= d:
        q += 1
    return q if n >= 0 else -q


def rnd_ratio(n, d):
    assert d > 0
    q, r = divmod(abs(n), d)
    if 2 * r >= d:
        q += 1
    return q if n >= 0 else -q


def extent(k, dl):
    return (k - 1) * dl + 1


def axis(L, E, s, pad):
    if pad == "none":
        return (L - E) // s + 1, 0, 0
    out = -(-L // s)
    tot = max((out - 1) * s + E - L, 0)
    top = tot // 2
    return out, top, tot - top


def geom(H, W, Kh, Kw, st, dl, pad):
    Eh, Ew = extent(Kh, dl[0]), extent(Kw, dl[1])
    oh, pt, pb = axis(H, Eh, st[0], pad)
    ow, pl, pr = axis(W, Ew, st[1], pad)
    return oh, ow, pt, pb, pl, pr


def accumulate(codes, H, W, C, izp, kc, Kh, Kw, kzp, bias, st, dl, g):
    oh, ow, pt, pb, pl, pr = g
    out = []
    for y in range(oh):
        for x in range(ow):
            for c in range(C):
                t = bias[c]
                for i in range(Kh):
                    for j in range(Kw):
                        r = y * st[0] - pt + i * dl[0]
                        col = x * st[1] - pl + j * dl[1]
                        p = codes[((r * W) + col) * C + c] if (0 <= r < H and 0 <= col < W) else izp
                        t += (p - izp) * (kc[((i * Kw) + j) * C + c] - kzp[c])
                out.append(t)
    return out


def fpm(m):
    s = 0
    while m < 0.5:
        m *= 2.0
        s += 1
    while m >= 1.0:
        m /= 2.0
        s -= 1
    m0 = rnd(m * float(1 << 31))
    if m0 == 1 << 31:
        m0 = 1 << 30
        s -= 1
    return m0, s


def chmul(isc, ksc, osc):
    ms = []
    ss = []
    for k in ksc:
        a, b = fpm(isc * k / osc)
        ms.append(a)
        ss.append(b)
    return ms, ss


def requant_one(m0, s, acc, ozp):
    h = rnd_ratio(acc * m0, 1 << 31)
    r = rnd_ratio(h, 1 << s) if s >= 0 else h << (-s)
    return r + ozp


def act_bounds(osc, ozp, lo, hi):
    return (max(QMIN, min(QMAX, rnd(lo / osc) + ozp)),
            max(QMIN, min(QMAX, rnd(hi / osc) + ozp)))


def clampb(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def layer(job):
    t = job["input"]
    k = job["kernel"]
    b = job["bias"]
    st = tuple(job["stride"])
    dl = tuple(job["dilation"])
    C = t["c"]
    g = geom(t["h"], t["w"], k["kh"], k["kw"], st, dl, job["padding"])
    acc = accumulate(t["codes"], t["h"], t["w"], C, t["zero_point"], k["codes"],
                     k["kh"], k["kw"], k["zero_points"], b, st, dl, g)
    ms, ss = chmul(t["scale"], k["scales"], job["output"]["scale"])
    ozp = job["output"]["zero_point"]
    a = job["activation"]
    if a["kind"] == "clamped":
        lo, hi = act_bounds(job["output"]["scale"], ozp, a["lower"], a["upper"])
    else:
        lo, hi = QMIN, QMAX
    codes = [clampb(requant_one(ms[i % C], ss[i % C], v, ozp), lo, hi) for i, v in enumerate(acc)]
    return {"out_h": g[0], "out_w": g[1], "pad_top": g[2], "pad_bottom": g[3],
            "pad_left": g[4], "pad_right": g[5], "mantissas": ms, "shifts": ss, "codes": codes}
