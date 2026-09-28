#!/usr/bin/env python3
"""Write natural-but-wrong analyzers as one-edit variants of solution/triage.py into wrong/<name>/triage.py."""
import sys
from pathlib import Path
task, out = Path(sys.argv[1]), Path(sys.argv[2])
src = (task / "solution/triage.py").read_text()
EDITS = {
 "no_year_rollover": ('parsed[i][0] > parsed[i + 1][0]', 'False'),
 "ignore_clock_step": ('step_n, lag = d, True', 'pass'),
 "step_on_authlog_only": ('auth = [(t + step_n if step_i is not None and i < step_i else t, msg) for i, (t, msg) in enumerate(dated)]', 'auth = [(t + step_n if step_i is not None and i < step_i else t, msg) for i, (t, msg) in enumerate(dated)]' + '\n    fix = lambda t: t  # noqa: E731'),
 "always_add_correction": ([('auth = [(t + step_n if step_i is not None and i < step_i else t, msg) for i, (t, msg) in enumerate(dated)]', 'auth = [(t + step_n, msg) for t, msg in dated]'), ('return t + step_n if step_t is not None and t < step_t else t', 'return t + step_n')]),
 "split_by_step_time": ('auth = [(t + step_n if step_i is not None and i < step_i else t, msg) for i, (t, msg) in enumerate(dated)]', 'auth = [(fix(t), msg) for t, msg in dated]'),
 "drop_root_login_branch": ('esc += [s["start"] for s in atk if s["user"] == "root"]', 'esc += []'),
 "local_time_as_utc": ('off = (int(m[2]) * 3600 + int(m[3]) * 60) * (1 if m[1] == "+" else -1)', 'off = 0'),
 "trust_mtime": ('path, ctime = f[0], fix(int(f[5]))', 'path, ctime = f[0], fix(int(f[4]))'),
 "first_success_is_initial": ('cands = sorted((s for s in sessions if s["host"] in hostile), key=lambda s: s["start"])', 'cands = sorted(sessions, key=lambda s: s["start"])'),
 "sudo_by_account": ('esc = [x["t"] for x in sudos if x["target"] == "root" and id(session_at(x["tty"], x["t"])) in {id(s) for s in atk}]',
                     'esc = [x["t"] for x in sudos if x["target"] == "root" and x["user"] in accounts and x["t"] >= ia["start"]]'),
 "hostile_strict_600": ('ts[i + 4] - ts[i] <= 600', 'ts[i + 4] - ts[i] < 600'),
 "hostile_any_five": ('if any(ts[i + 4] - ts[i] <= 600 for i in range(len(ts) - 4)):', 'if len(ts) >= 5:'),
 "failures_from_authlog": ('btmp = [(host, fix(sec)) for typ, _, _, _, host, sec in read_records(ev / "var/log/btmp") if typ == 6]',
                           'btmp = [(m[1], t) for t, msg in auth for m in [re.search(r"Failed password for (?:invalid user )?\\S+ from (\\S+)", msg)] if m]'),
 "keys_from_every_history": ('for acct in accounts:\n            for _, cmd in histories.get(acct, []):', 'for acct in histories:\n            for _, cmd in histories.get(acct, []):'),
 "no_package_exception": ('if any(abs(ctime - t) <= 2 for pkg', 'if False and any(abs(ctime - t) <= 2 for pkg'),
}
for name, spec in EDITS.items():
    text = src
    for a, b in (spec if isinstance(spec, list) else [spec]):
        assert text.count(a) == 1, name
        text = text.replace(a, b)
    d = out / name; d.mkdir(parents=True, exist_ok=True)
    (d / "triage.py").write_text(text)
print("wrote", len(EDITS))
