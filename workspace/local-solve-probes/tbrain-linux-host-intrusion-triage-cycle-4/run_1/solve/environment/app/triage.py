#!/usr/bin/env python3
"""Intrusion triage analyzer.

Usage: python3 /app/triage.py <evidence_dir> <out.json>

Reads one collected evidence directory (layout: /app/docs/record-formats.md),
applies /app/docs/case-guide.md and writes the incident report described in
/app/docs/report.md.
"""

import base64
import gzip
import hashlib
import json
import re
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

PERSIST_DIRS = ("/etc/cron.d/", "/var/spool/cron/crontabs/")
HOME_KEYS_RE = re.compile(r"^/home/[^/]+/\.ssh/authorized_keys$")
KEY_RE = re.compile(r"ssh-ed25519\s+([A-Za-z0-9+/=]{20,})")


def fmt(ts):
    if ts is None:
        return None
    return (EPOCH + timedelta(seconds=int(ts))).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_epoch(dt_naive):
    """Seconds since the epoch for a naive datetime read as UTC."""
    return int((dt_naive.replace(tzinfo=timezone.utc) - EPOCH).total_seconds())


# ---------------------------------------------------------------- collection

def read_collection(root):
    info = {}
    text = (root / "collection.txt").read_text(errors="replace")
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        info[key.strip()] = value.strip()
    off = info["utc_offset"]
    sign = -1 if off.startswith("-") else 1
    hh, mm = off[1:].split(":")
    offset = sign * (int(hh) * 3600 + int(mm) * 60)
    collected = to_epoch(datetime.strptime(info["collected_utc"], "%Y-%m-%dT%H:%M:%SZ"))
    return info.get("hostname", ""), offset, collected


# ---------------------------------------------------------------- auth logs

AUTH_RE = re.compile(
    r"^(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<prog>[^:\[]+)(?:\[(?P<pid>\d+)\])?:\s?(?P<msg>.*)$")


def auth_files(root):
    logdir = root / "var" / "log"
    found = []
    if not logdir.is_dir():
        return found
    for p in logdir.iterdir():
        name = p.name
        if name == "auth.log":
            found.append((0, p))
        else:
            m = re.match(r"^auth\.log\.(\d+)(\.gz)?$", name)
            if m:
                found.append((int(m.group(1)), p))
    # oldest first == highest rotation number first
    found.sort(key=lambda t: -t[0])
    return [p for _, p in found]


def read_text_file(path):
    data = path.read_bytes()
    if path.suffix == ".gz" or data[:2] == b"\x1f\x8b":
        try:
            data = gzip.decompress(data)
        except OSError:
            pass
    return data.decode("utf-8", errors="replace")


def parse_auth_logs(root, offset, collected):
    """Return list of dicts with raw (host-clock) epoch seconds."""
    recs = []
    for path in auth_files(root):
        for line in read_text_file(path).splitlines():
            m = AUTH_RE.match(line)
            if not m:
                continue
            mon = MONTHS.get(m.group("mon"))
            if mon is None:
                continue
            recs.append({
                "mon": mon, "day": int(m.group("day")),
                "h": int(m.group("h")), "mi": int(m.group("m")), "sec": int(m.group("s")),
                "prog": m.group("prog").strip(),
                "pid": int(m.group("pid")) if m.group("pid") else None,
                "msg": m.group("msg"),
            })
    # assign years walking backwards from the newest line
    coll_local = EPOCH + timedelta(seconds=collected + offset)
    coll_local = coll_local.replace(tzinfo=None)
    year = coll_local.year
    later = None
    for rec in reversed(recs):
        dt = None
        while dt is None:
            try:
                dt = datetime(year, rec["mon"], rec["day"], rec["h"], rec["mi"], rec["sec"])
            except ValueError:
                year -= 1
        limit = coll_local if later is None else later
        while dt > limit:
            year -= 1
            try:
                dt = datetime(year, rec["mon"], rec["day"], rec["h"], rec["mi"], rec["sec"])
            except ValueError:
                continue
        rec["raw"] = to_epoch(dt) - offset
        later = dt
    return recs


# ---------------------------------------------------------------- remote log

REMOTE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+(?P<host>\S+)\s+"
    r"(?P<prog>[^:\[]+)(?:\[(?P<pid>\d+)\])?:\s?(?P<msg>.*)$")


def parse_remote(root):
    out = []
    rdir = root / "var" / "log" / "remote"
    if not rdir.is_dir():
        return out
    for path in sorted(rdir.iterdir()):
        if not path.is_file():
            continue
        for line in read_text_file(path).splitlines():
            m = REMOTE_RE.match(line)
            if not m:
                continue
            out.append({
                "time": to_epoch(datetime.strptime(m.group("ts"), "%Y-%m-%dT%H:%M:%SZ")),
                "pid": int(m.group("pid")) if m.group("pid") else None,
                "prog": m.group("prog").strip(),
                "msg": m.group("msg"),
            })
    return out


# ---------------------------------------------------------------- clock step

class Clock:
    """Maps host-clock epoch seconds to true UTC epoch seconds."""

    def __init__(self, step=0, last_shifted=None):
        self.step = step
        self.last_shifted = last_shifted

    def true(self, raw):
        if raw is None:
            return None
        if self.step and (self.last_shifted is None or raw <= self.last_shifted):
            return raw + self.step
        return raw


def build_clock(auth_recs, remote_recs):
    index = {}
    for rec in remote_recs:
        index.setdefault((rec["pid"], rec["msg"]), []).append(rec["time"])
    diffs = {}
    for rec in auth_recs:
        cands = index.get((rec["pid"], rec["msg"]))
        if not cands or len(cands) != 1:
            continue
        diff = cands[0] - rec["raw"]
        if diff < 0:
            continue
        diffs.setdefault(diff, []).append(rec["raw"])
    if not diffs:
        return Clock()
    step = max(diffs)
    if step == 0:
        return Clock()
    return Clock(step, max(diffs[step]))


# ---------------------------------------------------------------- utmp

def parse_utmp(path):
    out = []
    if not path.is_file():
        return out
    data = path.read_bytes()
    for i in range(0, len(data) - 127, 128):
        ty, pid, line, user, host, sec, _usec = struct.unpack("<ii16s32s64sii", data[i:i + 128])
        out.append({
            "type": ty, "pid": pid,
            "line": line.split(b"\0")[0].decode("utf-8", "replace"),
            "user": user.split(b"\0")[0].decode("utf-8", "replace"),
            "host": host.split(b"\0")[0].decode("utf-8", "replace"),
            "raw": sec,
        })
    return out


# ---------------------------------------------------------------- keys

def fingerprint(blob):
    try:
        raw = base64.b64decode(blob + "=" * (-len(blob) % 4))
    except Exception:
        return None
    digest = hashlib.sha256(raw).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def history_paths(root):
    """Map account name -> history file path."""
    out = {}
    rh = root / "root" / ".bash_history"
    if rh.is_file():
        out["root"] = rh
    home = root / "home"
    if home.is_dir():
        for user in sorted(home.iterdir()):
            hist = user / ".bash_history"
            if hist.is_file():
                out[user.name] = hist
    return out


def parse_history(path):
    """Return list of (time_or_None, command)."""
    out = []
    pending = None
    for line in read_text_file(path).splitlines():
        if re.fullmatch(r"#\d{9,12}", line.strip()):
            pending = int(line.strip()[1:])
            continue
        out.append((pending, line))
        pending = None
    return out


# ---------------------------------------------------------------- fs / dpkg

def parse_fs(root):
    out = []
    path = root / "fs-listing.tsv"
    if not path.is_file():
        return out
    lines = read_text_file(path).splitlines()
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        try:
            out.append({"path": parts[0], "mtime": int(parts[4]), "ctime": int(parts[5])})
        except ValueError:
            continue
    return out


def parse_dpkg(root):
    """Return {package: [install times (host clock, naive local)]}"""
    out = {}
    path = root / "var" / "log" / "dpkg.log"
    if not path.is_file():
        return out
    for line in read_text_file(path).splitlines():
        m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+status installed\s+(\S+?)(?::\S+)?\s", line)
        if not m:
            continue
        when = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        out.setdefault(m.group(2), []).append(when)
    return out


def parse_pkg_lists(root):
    """Return {path: set(packages)}"""
    out = {}
    info = root / "var" / "lib" / "dpkg" / "info"
    if not info.is_dir():
        return out
    for path in sorted(info.iterdir()):
        if path.suffix != ".list":
            continue
        pkg = path.name[:-len(".list")]
        for line in read_text_file(path).splitlines():
            line = line.strip()
            if line:
                out.setdefault(line, set()).add(pkg)
    return out


def is_persistence_kind(path):
    if any(path.startswith(d) for d in PERSIST_DIRS):
        return True
    if path.startswith("/etc/systemd/system/") and (path.endswith(".service") or path.endswith(".timer")):
        return True
    if path == "/etc/rc.local":
        return True
    if path == "/root/.ssh/authorized_keys":
        return True
    return bool(HOME_KEYS_RE.match(path))


# ---------------------------------------------------------------- analysis

SUDO_RE = re.compile(r"^\s*(?P<user>\S+)\s*:\s*TTY=(?P<tty>\S+)\s*;\s*PWD=(?P<pwd>[^;]*?)\s*;\s*USER=(?P<target>\S+)\s*;\s*COMMAND=(?P<cmd>.*)$")
ACCEPT_RE = re.compile(r"^Accepted (?P<method>\S+) for (?P<user>\S+) from (?P<addr>\S+) port (?P<port>\d+) ssh2(?::\s*\S+\s+(?P<fp>SHA256:\S+))?")


def analyze(evidence_dir):
    root = Path(evidence_dir)
    hostname, offset, collected = read_collection(root)
    auth = parse_auth_logs(root, offset, collected)
    remote = parse_remote(root)
    clock = build_clock(auth, remote)
    T = clock.true

    wtmp = parse_utmp(root / "var" / "log" / "wtmp")
    btmp = parse_utmp(root / "var" / "log" / "btmp")

    # ---- failed attempts (btmp is complete)
    failures = [{"time": T(r["raw"]), "user": r["user"], "addr": r["host"]}
                for r in btmp if r["type"] == 6]
    for r in auth:
        m = re.match(r"^Failed password for (?:invalid user )?(\S+) from (\S+) port", r["msg"])
        if m:
            cand = {"time": T(r["raw"]), "user": m.group(1), "addr": m.group(2)}
            if not any(f["time"] == cand["time"] and f["addr"] == cand["addr"]
                       and f["user"] == cand["user"] for f in failures):
                failures.append(cand)

    by_addr = {}
    for f in failures:
        by_addr.setdefault(f["addr"], []).append(f["time"])
    hostile = set()
    for addr, times in by_addr.items():
        times = sorted(times)
        for i in range(len(times) - 4):
            if times[i + 4] - times[i] <= 600:
                hostile.add(addr)
                break

    # ---- successful logins / sessions
    accepted = {}  # (user, addr, true time) -> dict
    for r in auth:
        if r["prog"] != "sshd":
            continue
        m = ACCEPT_RE.match(r["msg"])
        if m:
            accepted[(m.group("user"), m.group("addr"), T(r["raw"]))] = {
                "method": m.group("method"), "fp": m.group("fp")}
    for r in remote:
        if r["prog"] != "sshd":
            continue
        m = ACCEPT_RE.match(r["msg"])
        if m:
            accepted.setdefault((m.group("user"), m.group("addr"), r["time"]), {
                "method": m.group("method"), "fp": m.group("fp")})

    used = set()

    def take_accepted(user, addr, t):
        """Closest Accepted line for this login, within a second of slack."""
        best, best_key = None, None
        for key, extra in accepted.items():
            if key[0] != user or key[1] != addr or key in used:
                continue
            if abs(key[2] - t) > 1:
                continue
            if best is None or abs(key[2] - t) < abs(best_key[2] - t):
                best, best_key = extra, key
        if best_key is not None:
            used.add(best_key)
            return best
        return {}

    logins = []
    for i, r in enumerate(wtmp):
        if r["type"] != 7 or not r["host"]:
            continue
        t = T(r["raw"])
        logout = None
        for later in wtmp[i + 1:]:
            if later["type"] == 8 and later["pid"] == r["pid"] and later["raw"] >= r["raw"]:
                logout = T(later["raw"])
                break
        extra = take_accepted(r["user"], r["host"], t)
        logins.append({"user": r["user"], "addr": r["host"], "time": t,
                       "tty": r["line"], "logout": logout,
                       "method": extra.get("method"), "fp": extra.get("fp")})
    for (user, addr, t), extra in accepted.items():
        if (user, addr, t) not in used:
            logins.append({"user": user, "addr": addr, "time": t, "tty": None,
                           "logout": None, "method": extra.get("method"),
                           "fp": extra.get("fp")})
    logins.sort(key=lambda lg: lg["time"])

    # ---- initial access
    initial = None
    for lg in logins:
        if lg["addr"] in hostile:
            initial = lg
            break
    if initial is None:
        return {"initial_access": None, "sources": [], "accounts": [],
                "privilege_escalation": None, "persistence": [],
                "first_activity": None, "last_activity": None}

    # ---- sudo lines
    sudos = []
    for r in auth:
        if not r["prog"].startswith("sudo"):
            continue
        m = SUDO_RE.match(r["msg"])
        if m:
            sudos.append({"time": T(r["raw"]), "user": m.group("user"),
                          "tty": m.group("tty"), "target": m.group("target"),
                          "cmd": m.group("cmd")})

    histories = {acct: parse_history(p) for acct, p in history_paths(root).items()}

    # ---- iterative attribution
    intruder = {id(initial): initial}
    sources = {initial["addr"]}
    accounts = {initial["user"]}
    root_acted = False
    for _ in range(12):
        sessions = [(lg["time"], lg["logout"] if lg["logout"] is not None else collected,
                     lg["tty"]) for lg in intruder.values()]

        def in_session(t, tty=None):
            for start, end, sty in sessions:
                if start <= t <= end and (tty is None or sty is None or tty == sty):
                    return True
            return False

        # keys the intruder added
        fps = set()
        for acct in list(accounts):
            for _t, cmd in histories.get(acct, []):
                if "authorized_keys" not in cmd:
                    continue
                for blob in KEY_RE.findall(cmd):
                    fp = fingerprint(blob)
                    if fp:
                        fps.add(fp)

        changed = False
        for lg in logins:
            if id(lg) in intruder:
                continue
            if lg["addr"] in sources or (lg["fp"] and lg["fp"] in fps):
                intruder[id(lg)] = lg
                changed = True
        for lg in intruder.values():
            if lg["addr"] not in sources:
                sources.add(lg["addr"])
                changed = True
            if lg["user"] not in accounts:
                accounts.add(lg["user"])
                changed = True

        # did the intruder act as root?
        acted = any(lg["user"] == "root" for lg in intruder.values())
        for s in sudos:
            if s["target"] == "root" and in_session(s["time"], s["tty"]):
                acted = True
        for t, _cmd in histories.get("root", []):
            if t is not None and in_session(T(t)):
                acted = True
        if acted and not root_acted:
            root_acted = True
            changed = True
        if root_acted and "root" not in accounts:
            accounts.add("root")
            changed = True
        if not changed:
            break

    sessions = [(lg["time"], lg["logout"] if lg["logout"] is not None else collected,
                 lg["tty"]) for lg in intruder.values()]

    def in_session(t, tty=None):
        for start, end, sty in sessions:
            if start <= t <= end and (tty is None or sty is None or tty == sty):
                return True
        return False

    # ---- persistence
    dpkg = parse_dpkg(root)
    pkg_of = parse_pkg_lists(root)
    dpkg_true = {pkg: [T(to_epoch(w) - offset) for w in times] for pkg, times in dpkg.items()}
    persistence = []
    for entry in parse_fs(root):
        path = entry["path"]
        if not is_persistence_kind(path):
            continue
        ctime = T(entry["ctime"])
        if not in_session(ctime):
            continue
        pkg_written = False
        for pkg in pkg_of.get(path, ()):  # a package that lists this file
            for t in dpkg_true.get(pkg, ()):
                if abs(ctime - t) <= 2:
                    pkg_written = True
        if pkg_written:
            continue
        persistence.append((path, ctime))

    # ---- privilege escalation
    esc = []
    for lg in intruder.values():
        if lg["user"] == "root":
            esc.append(lg["time"])
    for s in sudos:
        if s["target"] == "root" and in_session(s["time"], s["tty"]):
            esc.append(s["time"])
    for t, _cmd in histories.get("root", []):
        if t is not None and in_session(T(t)):
            esc.append(T(t))
    escalation = min(esc) if esc else None

    # ---- first / last activity
    events = []
    for f in failures:
        if f["addr"] in sources:
            events.append(f["time"])
    for lg in intruder.values():
        events.append(lg["time"])
        if lg["logout"] is not None:
            events.append(lg["logout"])
    for s in sudos:
        if in_session(s["time"], s["tty"]):
            events.append(s["time"])
    for acct in accounts:
        for t, _cmd in histories.get(acct, []):
            if t is not None and in_session(T(t)):
                events.append(T(t))
    for _path, ctime in persistence:
        events.append(ctime)

    return {
        "initial_access": {"account": initial["user"], "source": initial["addr"],
                           "time": fmt(initial["time"])},
        "sources": sorted(sources),
        "accounts": sorted(accounts),
        "privilege_escalation": fmt(escalation),
        "persistence": sorted({p for p, _ in persistence}),
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
