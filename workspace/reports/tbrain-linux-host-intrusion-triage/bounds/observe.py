def observe(rows):
    out = {k: [] for k in ("utc_offset_min", "step_s", "year_lo", "year_hi", "auth_files")}
    for r in rows:
        f = r.get("facts") if isinstance(r, dict) else None
        if not f:
            continue
        for k in out:
            if f.get(k) is not None:
                out[k].append(f[k])
    return out
