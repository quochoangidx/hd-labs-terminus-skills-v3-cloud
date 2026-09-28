#!/usr/bin/env python3
"""Intrusion triage analyzer.

Usage: python3 /app/triage.py <evidence_dir> <out.json>

Reads one collected evidence directory (layout: /app/docs/record-formats.md),
applies /app/docs/case-guide.md and writes the incident report described in
/app/docs/report.md.
"""

import base64
import calendar
import collections
import gzip
import hashlib
import json
import re
import struct
import sys
import time
from pathlib import Path

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

DAY = 86400

SYSLOG_RE = re.compile(
    r"^(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+"
    r"(?P<h>\d{2}):(?P<mi>\d{2}):(?P<s>\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<prog>[^\s\[\]]+)(?:\[(?P<pid>\d+)\])?:\s(?P<msg>.*)$"
)
REMOTE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+(?P<host>\S+)\s+"
    r"(?P<prog>[^\s\[\]]+)(?:\[(?P<pid>\d+)\])?:\s(?P<msg>.*)$"
)
ACCEPTED_RE = re.compile(
    r"^Accepted (?P<method>\S+) for (?P<user>\S+) from (?P<addr>\S+) port \d+ ssh2"
    r"(?::\s*\S+\s+(?P<fp>SHA256:\S+))?"
)
FAILED_RE = re.compile(
    r"^Failed password for (?:invalid user )?(?P<user>\S+) from (?P<addr>\S+) port \d+ ssh2"
)
SUDO_RE = re.compile(
    r"^\s*(?P<user>\S+)\s+:\s+TTY=(?P<tty>\S+)\s+;\s+PWD=(?P<pwd>.*?)\s+;\s+"
    r"USER=(?P<target>\S+)\s+;\s+COMMAND=(?P<cmd>.*)$"
)
KEY_RE = re.compile(r"ssh-ed25519\s+([A-Za-z0-9+/]+={0,3})")
HIST_TS_RE = re.compile(r"^#(\d{8,12})$")

PERSIST_HOME_KEYS = re.compile(r"^/home/[^/]+/\.ssh/authorized_keys$")


def epoch_utc(y, mo, d, h, mi, s):
    return calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0))


def fmt(t):
    if t is None:
        return None
    y, mo, d, h, mi, s = time.gmtime(t)[:6]
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (y, mo, d, h, mi, s)


def parse_iso(text):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})Z?$", text.strip())
    if not m:
        raise ValueError("bad timestamp: %r" % text)
    return epoch_utc(*[int(g) for g in m.groups()])


# ---------------------------------------------------------------- collection


def read_collection(ev):
    info = {}
    path = ev / "collection.txt"
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
    offset = 0
    raw = info.get("utc_offset", "+00:00")
    m = re.match(r"^([+-])(\d{1,2}):(\d{2})$", raw)
    if m:
        offset = (int(m.group(2)) * 3600 + int(m.group(3)) * 60)
        if m.group(1) == "-":
            offset = -offset
    return {
        "hostname": info.get("hostname", ""),
        "offset": offset,
        "collected": parse_iso(info["collected_utc"]) if "collected_utc" in info else None,
    }


# ---------------------------------------------------------------- auth logs


def auth_files(ev):
    logdir = ev / "var" / "log"
    files = []
    if not logdir.is_dir():
        return files
    for p in logdir.iterdir():
        name = p.name
        if name == "auth.log":
            files.append((0, p))
        else:
            m = re.match(r"^auth\.log\.(\d+)(\.gz)?$", name)
            if m:
                files.append((int(m.group(1)), p))
    # oldest first: highest number first
    files.sort(key=lambda t: -t[0])
    return [p for _, p in files]


def read_lines(path):
    if path.name.endswith(".gz"):
        with gzip.open(path, "rt", errors="replace") as fh:
            return fh.read().splitlines()
    return path.read_text(errors="replace").splitlines()


def parse_auth(ev, offset, collected):
    """Return list of dicts with naive utc epoch ('t'), prog, pid, msg."""
    raw = []
    for path in auth_files(ev):
        for line in read_lines(path):
            m = SYSLOG_RE.match(line)
            if not m:
                continue
            raw.append(m)
    if not raw:
        return []
    # Year inference: walk backwards from the newest line.
    local_collected = (collected if collected is not None else 0) + offset
    last_year = time.gmtime(local_collected).tm_year
    out = []
    year = None
    prev_mo = None
    for m in reversed(raw):
        mo = MONTHS[m.group("mon")]
        if year is None:
            year = last_year
            cand = epoch_utc(year, mo, int(m.group("day")), int(m.group("h")),
                             int(m.group("mi")), int(m.group("s")))
            if cand > local_collected + DAY:
                year -= 1
        elif prev_mo is not None and mo > prev_mo:
            # going back in time, month increased => crossed a new year boundary
            year -= 1
        prev_mo = mo
        local = epoch_utc(year, mo, int(m.group("day")), int(m.group("h")),
                          int(m.group("mi")), int(m.group("s")))
        out.append({
            "t": local - offset,
            "prog": m.group("prog"),
            "pid": m.group("pid"),
            "msg": m.group("msg"),
        })
    out.reverse()
    return out


def parse_remote(ev, hostname):
    rdir = ev / "var" / "log" / "remote"
    out = []
    if not rdir.is_dir():
        return out
    paths = []
    if hostname:
        cand = rdir / (hostname + ".log")
        if cand.exists():
            paths.append(cand)
    if not paths:
        paths = sorted(p for p in rdir.iterdir() if p.is_file())
    for path in paths:
        for line in read_lines(path):
            m = REMOTE_RE.match(line)
            if not m:
                continue
            out.append({
                "t": parse_iso(m.group("ts")),
                "prog": m.group("prog"),
                "pid": m.group("pid"),
                "msg": m.group("msg"),
            })
    out.sort(key=lambda e: e["t"])
    return out


class Clock(object):
    """Maps host-clock (naive UTC) seconds to true UTC seconds."""

    def __init__(self, step=0, threshold=None):
        self.step = step
        self.threshold = threshold

    def __call__(self, t):
        if t is None:
            return None
        if self.step and (self.threshold is None or t <= self.threshold):
            return t + self.step
        return t


def build_clock(auth, remote):
    if not remote:
        return Clock()
    rkey = collections.defaultdict(list)
    for e in remote:
        rkey[(e["prog"], e["pid"], e["msg"])].append(e["t"])
    akey = collections.defaultdict(list)
    for e in auth:
        akey[(e["prog"], e["pid"], e["msg"])].append(e["t"])
    pairs = []
    for key, times in akey.items():
        rt = rkey.get(key)
        if not rt or len(rt) != 1 or len(times) != 1:
            continue
        pairs.append((times[0], rt[0] - times[0]))
    if not pairs:
        return Clock()
    counts = collections.Counter(d for _, d in pairs if 30 <= d <= 7200)
    if not counts:
        return Clock()
    best = max(counts.items(), key=lambda kv: (kv[1], kv[0]))
    step = best[0]
    pre = [t for t, d in pairs if d == step]
    post = [t for t, d in pairs if d == 0]
    threshold = None
    if post:
        threshold = min(post) - step
        if pre and max(pre) > threshold:
            threshold = max(pre)
    return Clock(step, threshold)


# ---------------------------------------------------------------- utmp


def read_utmp(path):
    out = []
    if not path.exists():
        return out
    data = path.read_bytes()
    for i in range(0, len(data) - 127, 128):
        typ, pid, line, user, host, sec, _usec = struct.unpack(
            "<ii16s32s64sii", data[i:i + 128])
        out.append({
            "type": typ,
            "pid": pid,
            "line": line.split(b"\0")[0].decode("utf-8", "replace"),
            "user": user.split(b"\0")[0].decode("utf-8", "replace"),
            "host": host.split(b"\0")[0].decode("utf-8", "replace"),
            "t": sec,
        })
    return out


def build_sessions(ev):
    """Sessions from wtmp: dicts with tty, user, host, start/end (naive)."""
    recs = read_utmp(ev / "var" / "log" / "wtmp")
    recs.sort(key=lambda r: r["t"])
    sessions = []
    open_by_tty = {}
    for r in recs:
        if r["type"] == 7:
            s = {"tty": r["line"], "user": r["user"], "host": r["host"],
                 "start": r["t"], "end": None}
            sessions.append(s)
            open_by_tty[r["line"]] = s
        elif r["type"] == 8:
            s = open_by_tty.pop(r["line"], None)
            if s is not None and s["end"] is None:
                s["end"] = r["t"]
    return sessions


def read_btmp(ev):
    out = []
    for r in read_utmp(ev / "var" / "log" / "btmp"):
        if r["type"] == 6:
            out.append({"t": r["t"], "user": r["user"], "host": r["host"]})
    out.sort(key=lambda r: r["t"])
    return out


# ---------------------------------------------------------------- histories


def read_histories(ev):
    """{account: {'timed': bool, 'entries': [(time_or_None, command)]}}"""
    hist = {}
    cands = []
    root = ev / "root" / ".bash_history"
    if root.exists():
        cands.append(("root", root))
    homes = ev / "home"
    if homes.is_dir():
        for d in sorted(homes.iterdir()):
            p = d / ".bash_history"
            if p.exists():
                cands.append((d.name, p))
    for account, path in cands:
        entries = []
        pending = None
        timed = False
        for line in read_lines(path):
            m = HIST_TS_RE.match(line.strip())
            if m:
                pending = int(m.group(1))
                timed = True
                continue
            entries.append((pending, line))
            pending = None
        hist[account] = {"timed": timed, "entries": entries}
    return hist


def fingerprint(blob):
    try:
        raw = base64.b64decode(blob + "=" * (-len(blob) % 4))
    except Exception:
        return None
    digest = hashlib.sha256(raw).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


# ---------------------------------------------------------------- dpkg


def read_dpkg(ev, offset):
    """List of (naive_epoch, package) for 'status installed' lines."""
    out = []
    path = ev / "var" / "log" / "dpkg.log"
    if not path.exists():
        return out
    for line in read_lines(path):
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2}) "
                     r"status installed (\S+)", line)
        if m:
            local = epoch_utc(*[int(m.group(i)) for i in range(1, 7)])
            pkg = m.group(7).split(":")[0]
            out.append((local - offset, pkg))
    return out


def read_pkg_lists(ev):
    out = {}
    d = ev / "var" / "lib" / "dpkg" / "info"
    if not d.is_dir():
        return out
    for p in sorted(d.iterdir()):
        if p.name.endswith(".list"):
            pkg = p.name[:-5].split(":")[0]
            try:
                paths = set(l.strip() for l in read_lines(p) if l.strip())
            except Exception:
                paths = set()
            out.setdefault(pkg, set()).update(paths)
    return out


def read_fs_listing(ev):
    out = []
    path = ev / "fs-listing.tsv"
    if not path.exists():
        return out
    lines = read_lines(path)
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        try:
            mtime = int(parts[4])
            ctime = int(parts[5])
        except ValueError:
            continue
        out.append({"path": parts[0], "mtime": mtime, "ctime": ctime})
    return out


def is_persistence_kind(path):
    if path.startswith("/etc/cron.d/") and len(path) > len("/etc/cron.d/"):
        return True
    if (path.startswith("/var/spool/cron/crontabs/")
            and len(path) > len("/var/spool/cron/crontabs/")):
        return True
    if path.startswith("/etc/systemd/system/") and (
            path.endswith(".service") or path.endswith(".timer")):
        return True
    if path == "/etc/rc.local":
        return True
    if path == "/root/.ssh/authorized_keys":
        return True
    if PERSIST_HOME_KEYS.match(path):
        return True
    return False


# ---------------------------------------------------------------- analysis


def analyze(evidence_dir):
    ev = Path(evidence_dir)
    info = read_collection(ev)
    offset = info["offset"]
    collected = info["collected"]

    auth = parse_auth(ev, offset, collected)
    remote = parse_remote(ev, info["hostname"])
    clock = build_clock(auth, remote)

    sessions = build_sessions(ev)
    btmp = read_btmp(ev)
    hist = read_histories(ev)

    # --- failed attempts (host clock naive times)
    failures = [(r["t"], r["host"], r["user"]) for r in btmp]
    if not failures:
        for e in auth:
            m = FAILED_RE.match(e["msg"])
            if m:
                failures.append((e["t"], m.group("addr"), m.group("user")))
        failures.sort()

    by_addr = collections.defaultdict(list)
    for t, addr, _user in failures:
        by_addr[addr].append(t)
    hostile = set()
    for addr, times in by_addr.items():
        times = sorted(times)
        for i in range(len(times) - 4):
            if times[i + 4] - times[i] <= 600:
                hostile.add(addr)
                break

    # --- publickey fingerprints per successful login
    fp_by_login = {}
    for e in auth:
        m = ACCEPTED_RE.match(e["msg"])
        if m and m.group("fp"):
            fp_by_login.setdefault((m.group("user"), e["t"]), m.group("fp"))
    fp_by_login_true = {}
    for e in remote:
        m = ACCEPTED_RE.match(e["msg"])
        if m and m.group("fp"):
            fp_by_login_true.setdefault((m.group("user"), e["t"]), m.group("fp"))

    def session_fp(s):
        fp = fp_by_login.get((s["user"], s["start"]))
        if fp is None:
            fp = fp_by_login_true.get((s["user"], clock(s["start"])))
        return fp

    # --- login list (wtmp based) plus accepted-line logins not in wtmp
    logins = []
    for s in sessions:
        logins.append(s)
    known = set((s["user"], s["start"]) for s in sessions)
    for e in auth:
        m = ACCEPTED_RE.match(e["msg"])
        if m and (m.group("user"), e["t"]) not in known and not any(
                s["user"] == m.group("user") and abs(s["start"] - e["t"]) <= 2
                for s in sessions):
            known.add((m.group("user"), e["t"]))
            extra = {"tty": None, "user": m.group("user"), "host": m.group("addr"),
                     "start": e["t"], "end": None, "synthetic": True}
            logins.append(extra)
            sessions.append(extra)
            fp_by_login.setdefault((m.group("user"), e["t"]), m.group("fp"))

    # --- initial access
    hostile_logins = sorted((s["start"], s["user"], s["host"]) for s in logins
                            if s["host"] in hostile)
    if not hostile_logins:
        return {
            "initial_access": None, "sources": [], "accounts": [],
            "privilege_escalation": None,
            "first_activity": None, "last_activity": None, "persistence": [],
        }
    ia_t, ia_user, ia_addr = hostile_logins[0]

    # --- sudo lines
    sudo_lines = []
    for e in auth:
        if e["prog"] != "sudo":
            continue
        m = SUDO_RE.match(e["msg"])
        if m:
            sudo_lines.append({"t": e["t"], "user": m.group("user"),
                               "tty": m.group("tty"), "target": m.group("target"),
                               "cmd": m.group("cmd")})

    def session_end_true(s):
        if s["end"] is None:
            return collected if collected is not None else clock(s["start"])
        return clock(s["end"])

    # --- fixpoint over the intruder's sources / accounts / keys
    sources = {ia_addr}
    keys = set()
    intruder = []
    for _ in range(12):
        fps = set()
        for blob in keys:
            fp = fingerprint(blob)
            if fp:
                fps.add(fp)
        new_intruder = []
        for s in sessions:
            if s["host"] in sources:
                new_intruder.append(s)
            elif fps:
                fp = session_fp(s)
                if fp and fp in fps:
                    new_intruder.append(s)
        new_sources = set(sources) | set(s["host"] for s in new_intruder if s["host"])
        accounts = set(s["user"] for s in new_intruder)

        spans = [(clock(s["start"]), session_end_true(s)) for s in new_intruder]

        def in_span(t):
            return any(a <= t <= b for a, b in spans)

        # acted as root?
        root_times = []
        for s in new_intruder:
            if s["user"] == "root":
                root_times.append(clock(s["start"]))
        for sl in sudo_lines:
            t = clock(sl["t"])
            if any(s["user"] == sl["user"] and s["tty"] == sl["tty"]
                   and a <= t <= b
                   for s, (a, b) in zip(new_intruder, spans)):
                root_times.append(t)
        acct_pool = set(accounts)
        if root_times or any(
                acc == "root" for acc in accounts):
            acct_pool.add("root")
        # timestamped root-history commands inside an intruder session
        if "root" in acct_pool:
            h = hist.get("root")
            if h:
                for ts, _cmd in h["entries"]:
                    if ts is not None and in_span(clock(ts)):
                        root_times.append(clock(ts))
        if root_times:
            acct_pool.add("root")

        # keys the intruder added
        new_keys = set(keys)
        for acc in acct_pool:
            h = hist.get(acc)
            if not h:
                continue
            for ts, cmd in h["entries"]:
                if "authorized_keys" not in cmd:
                    continue
                if h["timed"]:
                    if ts is None or not in_span(clock(ts)):
                        continue
                for blob in KEY_RE.findall(cmd):
                    new_keys.add(blob)

        if new_sources == sources and new_keys == keys and new_intruder == intruder:
            intruder = new_intruder
            break
        sources, keys, intruder = new_sources, new_keys, new_intruder

    spans = [(clock(s["start"]), session_end_true(s)) for s in intruder]

    def in_span(t):
        return any(a <= t <= b for a, b in spans)

    accounts = set(s["user"] for s in intruder)

    # --- privilege escalation / root commands
    root_events = []
    for s, (a, _b) in zip(intruder, spans):
        if s["user"] == "root":
            root_events.append(a)
    intruder_sudo = []
    for sl in sudo_lines:
        t = clock(sl["t"])
        if any(s["user"] == sl["user"] and s["tty"] == sl["tty"] and a <= t <= b
               for s, (a, b) in zip(intruder, spans)):
            intruder_sudo.append(t)
            if sl["target"] == "root":
                root_events.append(t)
    hist_events = []
    for acc in set(accounts) | ({"root"} if root_events else set()):
        h = hist.get(acc)
        if not h:
            continue
        for ts, _cmd in h["entries"]:
            if ts is not None and in_span(clock(ts)):
                hist_events.append(clock(ts))
                if acc == "root":
                    root_events.append(clock(ts))
    if root_events:
        accounts.add("root")
    priv = min(root_events) if root_events else None

    # --- persistence
    installs = read_dpkg(ev, offset)
    pkg_files = read_pkg_lists(ev)
    pkg_written = collections.defaultdict(list)
    for t, pkg in installs:
        for path in pkg_files.get(pkg, ()):  # naive host-clock seconds
            pkg_written[path].append(t)

    persistence = []
    persist_times = []
    for row in read_fs_listing(ev):
        path = row["path"]
        if not is_persistence_kind(path):
            continue
        ct = clock(row["ctime"])
        if not in_span(ct):
            continue
        if any(abs(row["ctime"] - t) <= 2 for t in pkg_written.get(path, ())):
            continue
        persistence.append(path)
        persist_times.append(ct)

    # --- first / last activity
    events = list(persist_times) + list(intruder_sudo) + hist_events
    for t, addr, _user in failures:
        if addr in sources:
            events.append(clock(t))
    for s, (a, b) in zip(intruder, spans):
        events.append(a)
        if s["end"] is not None:
            events.append(b)

    first = min(events) if events else None
    last = max(events) if events else None

    return {
        "initial_access": {"account": ia_user, "source": ia_addr,
                           "time": fmt(clock(ia_t))},
        "sources": sorted(sources),
        "accounts": sorted(accounts),
        "privilege_escalation": fmt(priv),
        "persistence": sorted(set(persistence)),
        "first_activity": fmt(first),
        "last_activity": fmt(last),
    }


def main(argv):
    if len(argv) != 3:
        print("usage: triage.py <evidence_dir> <out.json>", file=sys.stderr)
        return 2
    Path(argv[2]).write_text(json.dumps(analyze(Path(argv[1])), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
