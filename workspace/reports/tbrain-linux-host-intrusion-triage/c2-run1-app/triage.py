#!/usr/bin/env python3
"""Intrusion triage analyzer.

Usage: python3 /app/triage.py <evidence_dir> <out.json>

Reads one collected evidence directory (layout: /app/docs/record-formats.md),
applies /app/docs/case-guide.md and writes the incident report described in
/app/docs/report.md.
"""

import base64
import calendar
import gzip
import hashlib
import json
import re
import struct
import sys
import time
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

DAY = 86400
HOSTILE_COUNT = 5
HOSTILE_WINDOW = 600
PKG_SLACK = 2

PERSIST_DIRS = ("/etc/cron.d/", "/var/spool/cron/crontabs/")
KEY_BLOB_RE = re.compile(r"AAAAC3NzaC1lZDI1NTE5[A-Za-z0-9+/=]+")


# ---------------------------------------------------------------- utilities

def to_epoch(y, mo, d, h, mi, s):
    return calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0))


def fmt(epoch):
    if epoch is None:
        return None
    y, mo, d, h, mi, s = time.gmtime(int(epoch))[:6]
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (y, mo, d, h, mi, s)


def read_text(path):
    try:
        if str(path).endswith(".gz"):
            with gzip.open(path, "rt", errors="replace") as fh:
                return fh.read()
        return path.read_text(errors="replace")
    except OSError:
        return ""


def is_persistence_kind(path):
    for d in PERSIST_DIRS:
        if path.startswith(d) and len(path) > len(d):
            return True
    if path.startswith("/etc/systemd/system/") and (
            path.endswith(".service") or path.endswith(".timer")):
        return True
    if path == "/etc/rc.local":
        return True
    if path == "/root/.ssh/authorized_keys":
        return True
    m = re.fullmatch(r"/home/([^/]+)/\.ssh/authorized_keys", path)
    return bool(m)


def key_fingerprint(blob):
    pad = "=" * (-len(blob) % 4)
    try:
        raw = base64.b64decode(blob + pad)
    except Exception:
        return None
    digest = hashlib.sha256(raw).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


# ---------------------------------------------------------------- collection

def parse_collection(root):
    info = {}
    for line in read_text(root / "collection.txt").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    hostname = info.get("hostname", "")
    off = info.get("utc_offset", "+00:00")
    sign = -1 if off.startswith("-") else 1
    hh, mm = off.lstrip("+-").split(":")
    offset = sign * (int(hh) * 3600 + int(mm) * 60)
    c = info.get("collected_utc", "")
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z", c)
    collected = to_epoch(*(int(g) for g in m.groups())) if m else 0
    return hostname, offset, collected


# ---------------------------------------------------------------- auth logs

AUTH_LINE_RE = re.compile(
    r"^([A-Z][a-z]{2}) ([ \d]\d) (\d\d):(\d\d):(\d\d) (\S+) (.*)$")
PROG_PID_RE = re.compile(r"^(\S+?)\[(\d+)\]:\s?(.*)$")
PROG_RE = re.compile(r"^([A-Za-z0-9_.-]+):\s*(.*)$")


def auth_files(logdir):
    files = []
    for p in logdir.glob("auth.log*"):
        name = p.name
        if name == "auth.log":
            files.append((0, p))
            continue
        m = re.fullmatch(r"auth\.log\.(\d+)(\.gz)?", name)
        if m:
            files.append((int(m.group(1)), p))
    # oldest first: highest rotation number first
    files.sort(key=lambda t: -t[0])
    return [p for _, p in files]


def parse_auth(logdir, offset, collected):
    """Return list of dicts with keys: reading (host-clock epoch), prog, pid, msg."""
    raw = []
    for path in auth_files(logdir):
        for line in read_text(path).splitlines():
            m = AUTH_LINE_RE.match(line)
            if not m:
                continue
            mon = MONTHS.get(m.group(1))
            if not mon:
                continue
            day = int(m.group(2))
            hh, mi, ss = int(m.group(3)), int(m.group(4)), int(m.group(5))
            rest = m.group(7)
            pm = PROG_PID_RE.match(rest)
            if pm:
                prog, pid, msg = pm.group(1), int(pm.group(2)), pm.group(3)
            else:
                pm = PROG_RE.match(rest)
                if not pm:
                    continue
                prog, pid, msg = pm.group(1), None, pm.group(2)
            raw.append([mon, day, hh, mi, ss, prog, pid, msg])
    if not raw:
        return []
    # assign years walking backwards from the newest line
    cl = time.gmtime(collected + offset)
    year = cl.tm_year
    if raw[-1][0] == 12 and cl.tm_mon == 1:
        year -= 1
    years = [0] * len(raw)
    years[-1] = year
    for i in range(len(raw) - 2, -1, -1):
        if raw[i][0] > raw[i + 1][0]:
            year -= 1
        years[i] = year
    out = []
    for y, r in zip(years, raw):
        mon, day, hh, mi, ss, prog, pid, msg = r
        try:
            local = to_epoch(y, mon, day, hh, mi, ss)
        except Exception:
            continue
        out.append({"reading": local - offset, "prog": prog,
                    "pid": pid, "msg": msg})
    return out


REMOTE_RE = re.compile(
    r"^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z \S+ (\S+?)\[(\d+)\]:\s?(.*)$")


def parse_remote(logdir, hostname):
    remote = []
    cands = []
    p = logdir / "remote" / ("%s.log" % hostname)
    if p.exists():
        cands = [p]
    elif (logdir / "remote").is_dir():
        cands = sorted((logdir / "remote").glob("*.log"))
    for path in cands:
        for line in read_text(path).splitlines():
            m = REMOTE_RE.match(line)
            if not m:
                continue
            t = to_epoch(*(int(m.group(i)) for i in range(1, 7)))
            remote.append({"utc": t, "prog": m.group(7),
                           "pid": int(m.group(8)), "msg": m.group(9)})
    return remote


# ---------------------------------------------------------------- clock step

class Clock(object):
    """Maps host-clock readings (epoch seconds) to true UTC."""

    def __init__(self, delta=0, threshold=None):
        self.delta = delta
        self.threshold = threshold

    def __call__(self, reading):
        if self.delta and (self.threshold is None or reading < self.threshold):
            return reading + self.delta
        return reading


def build_clock(auth, remote):
    """Match auth sshd lines against the collector's copy to find the step."""
    by_key = {}
    for r in remote:
        by_key.setdefault((r["pid"], r["msg"]), []).append(r["utc"])
    for v in by_key.values():
        v.sort()
    used = {}
    matched = []  # (reading, discrepancy)
    for e in auth:
        if e["prog"] != "sshd" or e["pid"] is None:
            continue
        key = (e["pid"], e["msg"])
        times = by_key.get(key)
        if not times:
            continue
        i = used.get(key, 0)
        if i >= len(times):
            i = len(times) - 1
        d = times[i] - e["reading"]
        used[key] = i + 1
        if abs(d) <= 7300:
            matched.append((e["reading"], d))
            e["d"] = d
            e["utc"] = times[i]
    if not matched:
        return Clock()
    counts = {}
    for _, d in matched:
        if d:
            counts[d] = counts.get(d, 0) + 1
    if not counts:
        return Clock()
    delta = max(counts.items(), key=lambda kv: (kv[1], abs(kv[0])))[0]
    # a discrepancy that is neither 0 nor the step is a mismatch; drop it
    for e in auth:
        if e.get("d") not in (None, 0, delta):
            e.pop("d", None)
            e.pop("utc", None)
    pre = [r for r, d in matched if d == delta]
    post = [r for r, d in matched if d == 0]
    if not pre:
        return Clock()
    if not post:
        return Clock(delta, None)
    if delta > 0:
        threshold = min(post) - delta
        if threshold <= max(pre):
            threshold = max(pre) + 1
    else:
        threshold = min(post)
    return Clock(delta, threshold)


def propagate_d(auth, clock):
    """Give every auth entry a step side: from its own collector match when it
    has one, else from its neighbours when they agree (auth lines are in true
    chronological order), else from the reading threshold."""
    n = len(auth)
    prev = [None] * n
    last = None
    for i, e in enumerate(auth):
        prev[i] = last
        if e.get("d") is not None:
            last = e["d"]
    nxt = [None] * n
    later = None
    for i in range(n - 1, -1, -1):
        nxt[i] = later
        if auth[i].get("d") is not None:
            later = auth[i]["d"]
    for i, e in enumerate(auth):
        if e.get("d") is None:
            if prev[i] is not None and prev[i] == nxt[i]:
                e["d"] = prev[i]
            elif prev[i] is not None and nxt[i] is None:
                e["d"] = prev[i]
            elif nxt[i] is not None and prev[i] is None:
                e["d"] = nxt[i]
            else:
                e["d"] = clock(e["reading"]) - e["reading"]
        e["utc"] = e["reading"] + e["d"]


# ---------------------------------------------------------------- wtmp/btmp

def parse_utmp(path):
    try:
        data = path.read_bytes()
    except OSError:
        return []
    out = []
    for i in range(0, len(data) - 127, 128):
        typ, pid, line, user, host, sec, _usec = struct.unpack(
            "<ii16s32s64sii", data[i:i + 128])
        cut = lambda b: b.split(b"\0")[0].decode("utf-8", "replace")
        out.append({"type": typ, "pid": pid, "line": cut(line),
                    "user": cut(user), "host": cut(host), "sec": sec})
    return out


# ---------------------------------------------------------------- sessions

ACCEPTED_RE = re.compile(
    r"^Accepted (\S+) for (\S+) from (\S+) port (\d+) ssh2(?::.*?(SHA256:\S+))?\s*$")
CLOSED_RE = re.compile(r"^pam_unix\(sshd:session\): session closed for user (\S+)")
SUDO_RE = re.compile(
    r"^\s*(\S+) : TTY=(\S+) ; PWD=(\S+) ; USER=(\S+) ; COMMAND=(.*)$")
FAILED_RE = re.compile(
    r"^Failed \S+ for (?:invalid user )?(\S+) from (\S+) port (\d+)")


def build_sessions(auth, remote, wtmp, clock, collected):
    logins = []

    def find_login(user, addr, t, tol=2):
        best = None
        for s in logins:
            if s["user"] != user:
                continue
            if addr is not None and s["addr"] is not None and s["addr"] != addr:
                continue
            if abs(s["start"] - t) <= tol:
                if best is None or abs(s["start"] - t) < abs(best["start"] - t):
                    best = s
        return best

    def add_login(user, addr, t, pid=None, method=None, fp=None, tty=None,
                  d=None):
        s = find_login(user, addr, t)
        if s is None:
            s = {"user": user, "addr": addr, "start": t, "end": None,
                 "pid": None, "wpid": None, "tty": None,
                 "method": None, "fp": None, "d": None}
            logins.append(s)
        if d is not None and s["d"] is None:
            s["d"] = d
        if addr and not s["addr"]:
            s["addr"] = addr
        if pid and not s["pid"]:
            s["pid"] = pid
        if tty and not s["tty"]:
            s["tty"] = tty
        if method and not s["method"]:
            s["method"] = method
        if fp and not s["fp"]:
            s["fp"] = fp
        return s

    # collector copy first: correct times, complete for the whole period
    for r in remote:
        if r["prog"] != "sshd":
            continue
        m = ACCEPTED_RE.match(r["msg"])
        if m:
            add_login(m.group(2), m.group(3), r["utc"], pid=r["pid"],
                      method=m.group(1), fp=m.group(5))
    for e in auth:
        if e["prog"] != "sshd":
            continue
        m = ACCEPTED_RE.match(e["msg"])
        if m:
            add_login(m.group(2), m.group(3), e["utc"],
                      pid=e["pid"], method=m.group(1), fp=m.group(5),
                      d=e["d"])
    for rec in wtmp:
        if rec["type"] == 7 and rec["user"]:
            # the collector's copy settles which side of a clock step the
            # record lies on: try both candidate times against known logins
            s = None
            for cand_d in (0, clock.delta):
                s = find_login(rec["user"], rec["host"] or None,
                               rec["sec"] + cand_d)
                if s is not None:
                    if s["d"] is None:
                        s["d"] = cand_d
                    break
            if s is None:
                s = add_login(rec["user"], rec["host"] or None,
                              clock(rec["sec"]), tty=rec["line"],
                              d=clock(rec["sec"]) - rec["sec"])
            if not s["wpid"]:
                s["wpid"] = rec["pid"]
            if not s["tty"]:
                s["tty"] = rec["line"]

    logins.sort(key=lambda s: s["start"])

    def close_by_pid(pid, user, t):
        cand = [s for s in logins
                if s["pid"] == pid and s["start"] <= t + 1 and s["end"] is None
                and (user is None or s["user"] == user)]
        if cand:
            cand[-1]["end"] = t
            return True
        return False

    closes = []
    for r in remote:
        m = CLOSED_RE.match(r["msg"])
        if m:
            closes.append((r["utc"], r["pid"], m.group(1)))
    for e in auth:
        m = CLOSED_RE.match(e["msg"])
        if m:
            closes.append((e["utc"], e["pid"], m.group(1)))
    closes.sort()
    seen = set()
    for t, pid, user in closes:
        if (pid, user, t) in seen:
            continue
        seen.add((pid, user, t))
        close_by_pid(pid, user, t)

    for s in logins:
        if s["d"] is None:
            cand = s["start"] - clock.delta
            s["d"] = clock.delta if clock(cand) == s["start"] else 0

    for rec in wtmp:
        if rec["type"] != 8:
            continue
        cand = [s for s in logins if s["wpid"] == rec["pid"]
                and s["start"] <= rec["sec"] + s["d"] + 1]
        if not cand:
            cand = [s for s in logins if s["tty"] == rec["line"]
                    and s["start"] <= rec["sec"] + s["d"] + 1
                    and s["end"] is None]
        if cand:
            s = cand[-1]
            if s["end"] is None:
                s["end"] = rec["sec"] + s["d"]

    for s in logins:
        s["open_end"] = s["end"] if s["end"] is not None else collected
    return logins


# ---------------------------------------------------------------- histories

def parse_histories(root):
    """{account: [(time_or_None, command), ...]} with host-clock readings."""
    hist = {}
    cands = []
    rh = root / "root" / ".bash_history"
    if rh.exists():
        cands.append(("root", rh))
    home = root / "home"
    if home.is_dir():
        for d in sorted(home.iterdir()):
            p = d / ".bash_history"
            if p.exists():
                cands.append((d.name, p))
    for account, path in cands:
        items = []
        pending = None
        for line in read_text(path).splitlines():
            if re.fullmatch(r"#\d+", line.strip()):
                pending = int(line.strip()[1:])
                continue
            items.append((pending, line))
            pending = None
        hist[account] = items
    return hist


def added_keys(hist, accounts):
    fps = set()
    for account in accounts:
        for _t, cmd in hist.get(account, []):
            if "authorized_keys" not in cmd:
                continue
            for blob in KEY_BLOB_RE.findall(cmd):
                fp = key_fingerprint(blob)
                if fp:
                    fps.add(fp)
    return fps


# ---------------------------------------------------------------- dpkg / fs

def parse_dpkg(root, offset):
    installs = {}
    path = root / "var" / "log" / "dpkg.log"
    for line in read_text(path).splitlines():
        m = re.match(r"^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d) status installed "
                     r"([^:\s]+):\S+", line)
        if m:
            reading = to_epoch(*(int(m.group(i)) for i in range(1, 7))) - offset
            installs.setdefault(m.group(7), []).append(reading)
    pkg_files = {}
    info = root / "var" / "lib" / "dpkg" / "info"
    if info.is_dir():
        for p in sorted(info.glob("*.list")):
            pkg = p.name[:-5]
            pkg_files[pkg] = set(
                l.strip() for l in read_text(p).splitlines() if l.strip())
    return installs, pkg_files


def parse_fs(root):
    rows = []
    path = root / "fs-listing.tsv"
    lines = read_text(path).splitlines()
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        try:
            mtime = int(parts[4])
            ctime = int(parts[5])
        except ValueError:
            continue
        rows.append({"path": parts[0], "mtime": mtime, "ctime": ctime})
    return rows


# ---------------------------------------------------------------- analysis

def analyze(evidence_dir):
    root = Path(evidence_dir)
    hostname, offset, collected = parse_collection(root)
    logdir = root / "var" / "log"
    auth = parse_auth(logdir, offset, collected)
    remote = parse_remote(logdir, hostname)
    clock = build_clock(auth, remote)
    propagate_d(auth, clock)

    wtmp = parse_utmp(logdir / "wtmp")
    btmp = parse_utmp(logdir / "btmp")

    # ---- failed attempts: btmp holds every one of them
    failed = {}
    have_btmp = False
    for rec in btmp:
        if rec["type"] == 6 and rec["host"]:
            have_btmp = True
            failed.setdefault(rec["host"], []).append(clock(rec["sec"]))
    if not have_btmp:
        for e in auth:
            if e["prog"] != "sshd":
                continue
            m = FAILED_RE.match(e["msg"])
            if m:
                failed.setdefault(m.group(2), []).append(e["utc"])

    hostile = set()
    fail_times = {}
    for addr, ts in failed.items():
        ts = sorted(ts)
        fail_times[addr] = ts
        for i in range(len(ts) - HOSTILE_COUNT + 1):
            if ts[i + HOSTILE_COUNT - 1] - ts[i] <= HOSTILE_WINDOW:
                hostile.add(addr)
                break

    sessions = build_sessions(auth, remote, wtmp, clock, collected)

    # ---- sudo commands run as root
    sudos = []
    for e in auth:
        if e["prog"] != "sudo":
            continue
        m = SUDO_RE.match(e["msg"])
        if m and m.group(4) == "root":
            sudos.append({"user": m.group(1), "tty": m.group(2),
                          "cmd": m.group(5), "t": e["utc"]})

    hist = parse_histories(root)

    # ---- initial access: earliest successful login from a hostile address
    cand = [s for s in sessions if s["addr"] in hostile]
    if not cand:
        cand = sessions
    if not cand:
        return {"initial_access": None, "sources": [], "accounts": [],
                "privilege_escalation": None, "persistence": [],
                "first_activity": None, "last_activity": None}
    first = min(cand, key=lambda s: s["start"])

    intruder = {id(first): first}
    sources = {first["addr"]}
    accounts = {first["user"]}
    keys = set()

    def ttys():
        return set(s["tty"] for s in intruder.values() if s["tty"])

    def active(t, user=None, tty=None, pool=None):
        """Sessions open at true time t."""
        out = []
        for s in (sessions if pool is None else pool):
            if user is not None and s["user"] != user:
                continue
            if tty is not None and s["tty"] != tty:
                continue
            if s["start"] <= t <= s["open_end"]:
                out.append(s)
        return out

    def in_intruder_session(t, user=None, tty=None):
        got = active(t, user, tty, pool=list(intruder.values()))
        return got[0] if got else None

    def owner(t, user, tty):
        """The session a command recorded at true time t belongs to."""
        act = active(t, user=user)
        by_tty = [s for s in act if s["tty"] == tty] if tty else []
        pool = by_tty if by_tty else act
        if not pool:
            return None, False
        mine = [s for s in pool if id(s) in intruder]
        return (mine[0] if mine else pool[0]), (len(mine) == len(pool)
                                                and bool(mine))

    def reading_owner(reading, user=None, intruder_only=True):
        """Place a host-clock reading in a session, using that session's own
        side of the clock step (the collector settles it)."""
        best = None
        pool = list(intruder.values()) if intruder_only else sessions
        for s in pool:
            if user is not None and s["user"] != user:
                continue
            t = reading + s["d"]
            if s["start"] <= t <= s["open_end"]:
                if best is None or t < best[1]:
                    best = (s, t)
        return best

    def intruder_sudos():
        out = []
        for sd in sudos:
            s, sole = owner(sd["t"], sd["user"], sd["tty"])
            if s is not None and sole:
                out.append(sd)
        return out

    for _ in range(12):
        changed = False
        keys |= added_keys(hist, accounts)
        for s in sessions:
            if id(s) in intruder:
                continue
            if s["addr"] in sources or (s["fp"] and s["fp"] in keys):
                intruder[id(s)] = s
                changed = True
        for s in list(intruder.values()):
            if s["addr"] and s["addr"] not in sources:
                sources.add(s["addr"])
                changed = True
            if s["user"] not in accounts:
                accounts.add(s["user"])
                changed = True
        if intruder_sudos() and "root" not in accounts:
            accounts.add("root")
            changed = True
        if not changed:
            break

    intruder_sessions = sorted(intruder.values(), key=lambda s: s["start"])

    # ---- intruder root actions (privilege escalation)
    root_events = [sd["t"] for sd in intruder_sudos()]
    for s in intruder_sessions:
        if s["user"] == "root":
            root_events.append(s["start"])
    root_hist = []
    for t, _cmd in hist.get("root", []):
        if t is None:
            continue
        got = reading_owner(t)
        if got is not None:
            root_hist.append(got[1])
    if root_events:
        floor = min(root_events)
        root_events.extend(t for t in root_hist if t >= floor)
    else:
        root_events.extend(root_hist)
    if root_events:
        accounts.add("root")

    # ---- timestamped history commands by the intruder
    cmd_events = []
    for account, items in hist.items():
        if account not in accounts:
            continue
        for t, _cmd in items:
            if t is None:
                continue
            if account == "root":
                continue
            got = reading_owner(t, user=account)
            if got is not None:
                cmd_events.append(got[1])
    cmd_events.extend(root_events)

    # ---- persistence
    installs, pkg_files = parse_dpkg(root, offset)
    fs = parse_fs(root)
    persistence = []
    persist_times = []
    for row in fs:
        path = row["path"]
        if not is_persistence_kind(path):
            continue
        got = reading_owner(row["ctime"])
        if got is None:
            continue
        ctime_true = got[1]
        # a file the package manager wrote is never persistence
        pkg_written = False
        for pkg, paths in pkg_files.items():
            if path in paths:
                for t in installs.get(pkg, []):
                    if abs(row["ctime"] - t) <= PKG_SLACK:
                        pkg_written = True
                        break
            if pkg_written:
                break
        if pkg_written:
            continue
        # visibly changed by someone else at that very moment?
        other = False
        for sd in sudos:
            if abs(sd["t"] - ctime_true) <= PKG_SLACK and path in sd["cmd"]:
                s, sole = owner(sd["t"], sd["user"], sd["tty"])
                if not sole:
                    other = True
        if other:
            continue
        persistence.append(path)
        persist_times.append(ctime_true)

    # ---- first / last activity
    events = []
    for addr in sources:
        events.extend(fail_times.get(addr, []))
    for s in intruder_sessions:
        events.append(s["start"])
        if s["end"] is not None:
            events.append(s["end"])
    events.extend(cmd_events)
    events.extend(persist_times)
    events = [e for e in events if e is not None]

    return {
        "initial_access": {"account": first["user"], "source": first["addr"],
                           "time": fmt(first["start"])},
        "sources": sorted(a for a in sources if a),
        "accounts": sorted(accounts),
        "privilege_escalation": fmt(min(root_events)) if root_events else None,
        "persistence": sorted(set(persistence)),
        "first_activity": fmt(min(events)) if events else None,
        "last_activity": fmt(max(events)) if events else None,
    }


def main(argv):
    if len(argv) != 3:
        print("usage: triage.py <evidence_dir> <out.json>", file=sys.stderr)
        return 2
    Path(argv[2]).write_text(json.dumps(analyze(Path(argv[1])), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
