#!/usr/bin/env python3
"""Reconstruct an SSH intrusion from a collected evidence directory.

Usage: python3 /app/triage.py <evidence_dir> <out.json>

Follows /app/docs/case-guide.md rule by rule; comments cite the rule numbers.
"""

import base64
import gzip
import hashlib
import json
import re
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
REC = struct.Struct("<ii16s32s64sii")
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
ACCEPT = re.compile(r"sshd\[\d+\]: Accepted (\w+) for (\S+) from (\S+) port \d+ ssh2(?:: \S+ (SHA256:\S+))?")
SUDO = re.compile(r"sudo:\s+(\S+) : TTY=(\S+) ; PWD=.* ; USER=(\S+) ; COMMAND=")
KEY = re.compile(r"ssh-ed25519 (AAAA[A-Za-z0-9+/]+=*)")


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch(y, mo, d, h, mi, s, off):
    return int((datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc) - EPOCH).total_seconds()) - off


def read_collection(ev):
    kv = dict(line.split(": ", 1) for line in (ev / "collection.txt").read_text().splitlines() if ": " in line)
    m = re.fullmatch(r"([+-])(\d\d):(\d\d)", kv["utc_offset"].strip())
    off = 0
    coll = int((datetime.strptime(kv["collected_utc"].strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) - EPOCH).total_seconds())
    return off, coll


def auth_lines(ev):
    """Rule 2 reading order: highest rotation first, auth.log last."""
    files = []
    for p in (ev / "var/log").glob("auth.log*"):
        m = re.fullmatch(r"auth\.log(?:\.(\d+))?(\.gz)?", p.name)
        if m:
            files.append((int(m[1] or 0), p))
    out = []
    for _, p in sorted(files, key=lambda r: -r[0]):
        data = gzip.decompress(p.read_bytes()) if p.name.endswith(".gz") else p.read_bytes()
        out += [ln for ln in data.decode("utf-8", "replace").splitlines() if ln.strip()]
    return out


def date_lines(lines, off, coll):
    """Rules 2 and 1: host-clock UTC seconds for every auth-log line (before the step correction)."""
    parsed = []
    for ln in lines:
        m = re.match(r"(\w{3}) +(\d+) (\d\d):(\d\d):(\d\d) \S+ (.*)", ln)
        if m:
            parsed.append([MONTHS[m[1]], int(m[2]), int(m[3]), int(m[4]), int(m[5]), m[6]])
    if not parsed:
        return []
    coll_local = datetime.fromtimestamp(coll + off, timezone.utc)
    mo, d, h, mi, s, _ = parsed[-1]
    year = coll_local.year
    if (mo, d, h, mi, s) > (coll_local.month, coll_local.day, coll_local.hour, coll_local.minute, coll_local.second):
        year -= 1
    out = []
    for i in range(len(parsed) - 1, -1, -1):
        if i < len(parsed) - 1 and parsed[i][0] > parsed[i + 1][0]:
            year -= 1
        mo, d, h, mi, s, msg = parsed[i]
        out.append((epoch(year, mo, d, h, mi, s, off), msg))
    out.reverse()
    return out


def read_records(path):
    data = path.read_bytes() if path.exists() else b""
    recs = []
    for i in range(0, len(data) - len(data) % REC.size, REC.size):
        typ, pid, line, user, host, sec, _ = REC.unpack_from(data, i)
        dec = [x.split(b"\0", 1)[0].decode("utf-8", "replace") for x in (line, user, host)]
        recs.append((typ, pid, dec[0], dec[1], dec[2], sec))
    return recs


def fingerprint(b64):
    blob = base64.b64decode(b64)
    return "SHA256:" + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")


def read_history(path):
    """Return [(time or None, command)]."""
    cmds, stamp = [], None
    for ln in path.read_text(errors="replace").splitlines():
        m = re.fullmatch(r"#(\d{9,11})", ln.strip())
        if m:
            stamp = int(m[1])
            continue
        cmds.append((stamp, ln))
        stamp = None
    return cmds


def analyze(ev):
    ev = Path(ev)
    off, coll = read_collection(ev)
    dated = date_lines(auth_lines(ev), off, coll)
    # Rule 1: find the host-clock error by matching sshd lines against the remote collector's copy.
    true_at = {}
    for p in (ev / "var/log/remote").glob("*.log"):
        for ln in p.read_text(errors="replace").splitlines():
            m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) \S+ (.*)", ln)
            if m:
                true_at[m[2]] = int((datetime.strptime(m[1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) - EPOCH).total_seconds())
    step_n, step_t, lag = 0, None, False
    for t, msg in dated:
        if msg in true_at:
            d = true_at[msg] - t
            if d > 0:
                step_n, lag = d, True
            elif lag and d == 0 and step_t is None:
                step_t = t

    def fix(t):
        return t + step_n if step_t is not None and t < step_t else t

    auth = [(fix(t), msg) for t, msg in dated]
    # Rule 4: logins, logouts and failures.
    wtmp = [(typ, line, user, host, fix(sec)) for typ, _, line, user, host, sec in read_records(ev / "var/log/wtmp")]
    btmp = [(host, fix(sec)) for typ, _, _, _, host, sec in read_records(ev / "var/log/btmp") if typ == 6]
    sessions = []
    open_by_line = {}
    for typ, line, user, host, t in sorted(wtmp, key=lambda r: r[4]):
        if typ == 7:
            s = {"user": user, "host": host, "start": t, "end": None, "line": line}
            sessions.append(s)
            open_by_line[line] = s
        elif typ == 8 and line in open_by_line:
            open_by_line.pop(line)["end"] = t
    accepted = []
    sudos = []
    for t, msg in auth:
        m = ACCEPT.search(msg)
        if m:
            accepted.append({"t": t, "method": m[1], "user": m[2], "host": m[3], "fp": m[4]})
        m = SUDO.search(msg)
        if m:
            sudos.append({"t": t, "user": m[1], "tty": m[2], "target": m[3]})
    # Rule 5: hostile addresses.
    by_host = {}
    for host, t in btmp:
        by_host.setdefault(host, []).append(t)
    hostile = set()
    for host, ts in by_host.items():
        ts.sort()
        if any(ts[i + 4] - ts[i] <= 600 for i in range(len(ts) - 4)):
            hostile.add(host)
    # Rule 6: initial access.
    cands = sorted((s for s in sessions if s["host"] in hostile), key=lambda s: s["start"])
    if not cands:
        return {}
    ia = cands[0]

    def session_at(tty, t):
        for s in sessions:
            if s["line"] == tty and s["start"] <= t and (s["end"] is None or t <= s["end"]):
                return s
        return None

    histories = {}
    for p in list(ev.glob("home/*/.bash_history")) + [ev / "root/.bash_history"]:
        if p.exists():
            owner = "root" if p.parent.name == "root" else p.parent.name
            histories[owner] = read_history(p)
    # Rules 7, 8, 10: iterate to a fixed point.
    addrs = {ia["host"]}
    accounts = set()
    keys = set()
    pe = None
    while True:
        before = (frozenset(addrs), frozenset(accounts), frozenset(keys), pe)
        for a in accepted:
            if a["fp"] and a["fp"] in keys:
                addrs.add(a["host"])
        atk = [s for s in sessions if s["host"] in addrs]
        accounts |= {s["user"] for s in atk}
        esc = [x["t"] for x in sudos if x["target"] == "root" and id(session_at(x["tty"], x["t"])) in {id(s) for s in atk}]
        esc += [s["start"] for s in atk if s["user"] == "root"]
        pe = min(esc) if esc else None
        if pe is not None:
            accounts.add("root")
        for acct in accounts:
            for _, cmd in histories.get(acct, []):
                for k in KEY.findall(cmd):
                    try:
                        keys.add(fingerprint(k))
                    except ValueError:
                        pass
        if (frozenset(addrs), frozenset(accounts), frozenset(keys), pe) == before:
            break
    atk = [s for s in sessions if s["host"] in addrs]
    windows = [(s["start"], s["end"] if s["end"] is not None else coll) for s in atk]

    def in_window(t):
        return any(a <= t <= b for a, b in windows)

    # Rule 11: persistence.
    installed = {}
    dpkg = ev / "var/log/dpkg.log"
    if dpkg.exists():
        for ln in dpkg.read_text(errors="replace").splitlines():
            m = re.match(r"(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d) status installed ([^:\s]+)", ln)
            if m:
                t = fix(epoch(*(int(m[i]) for i in range(1, 7)), off))
                installed.setdefault(m[7], []).append(t)
    owner_pkgs = {}
    for p in ev.glob("var/lib/dpkg/info/*.list"):
        for path in p.read_text(errors="replace").splitlines():
            owner_pkgs.setdefault(path.strip(), []).append(p.name[:-5].split(":")[0])
    persistence = {}
    rows = (ev / "fs-listing.tsv").read_text(errors="replace").splitlines()[1:]
    for row in rows:
        f = row.split("\t")
        if len(f) < 6:
            continue
        path, ctime = f[0], fix(int(f[5]))
        cls = (path.startswith(("/etc/cron.d/", "/var/spool/cron/crontabs/")) or path == "/etc/rc.local"
               or (path.startswith("/etc/systemd/system/") and path.endswith((".service", ".timer")))
               or re.fullmatch(r"/(home/[^/]+|root)/\.ssh/authorized_keys", path) is not None)
        if not cls or not in_window(ctime):
            continue
        if any(abs(ctime - t) <= 2 for pkg in owner_pkgs.get(path, []) for t in installed.get(pkg, [])):
            continue
        persistence[path] = ctime
    # Rule 12: first and last activity.
    ev_times = [t for host, t in btmp if host in addrs]
    for s in atk:
        ev_times.append(s["start"])
        if s["end"] is not None:
            ev_times.append(s["end"])
    ev_times += [x["t"] for x in sudos if id(session_at(x["tty"], x["t"])) in {id(s) for s in atk}]
    ev_times += list(persistence.values())
    for acct in accounts:
        ev_times += [fix(t) for t, _ in histories.get(acct, []) if t is not None and in_window(fix(t))]
    return {
        "initial_access": {"account": ia["user"], "source": ia["host"], "time": iso(ia["start"])},
        "sources": sorted(addrs),
        "accounts": sorted(accounts),
        "privilege_escalation": iso(pe) if pe is not None else None,
        "persistence": sorted(persistence),
        "first_activity": iso(min(ev_times)),
        "last_activity": iso(max(ev_times)),
    }


def main(argv):
    if len(argv) != 3:
        print("usage: triage.py <evidence_dir> <out.json>", file=sys.stderr)
        return 2
    Path(argv[2]).write_text(json.dumps(analyze(argv[1]), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
