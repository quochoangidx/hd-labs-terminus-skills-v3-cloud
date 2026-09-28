#!/usr/bin/env python3
"""Intrusion triage analyzer.

Usage: python3 /app/triage.py <evidence_dir> <out.json>

Reads one collected evidence directory (layout: /app/docs/record-formats.md),
applies /app/docs/case-guide.md and writes the incident report described in
/app/docs/report.md.
"""

import base64
import calendar
import glob
import gzip
import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

SYSLOG_RE = re.compile(
    r"^(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+"
    r"(?P<h>\d{2}):(?P<mi>\d{2}):(?P<s>\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<prog>[^:]+):\s?(?P<msg>.*)$"
)
REMOTE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+(?P<host>\S+)\s+"
    r"(?P<prog>[^:]+):\s?(?P<msg>.*)$"
)
PROG_RE = re.compile(r"^(?P<name>[^\[\s]+)(?:\[(?P<pid>\d+)\])?\s*$")

ACCEPTED_RE = re.compile(
    r"^Accepted (?P<method>\S+) for (?P<user>\S+) from (?P<addr>\S+) port (?P<port>\d+) ssh2"
    r"(?::\s*(?P<keytype>\S+)\s+SHA256:(?P<fp>\S+))?"
)
FAILED_RE = re.compile(
    r"^Failed \S+ for (?:invalid user )?(?P<user>\S+) from (?P<addr>\S+) port (?P<port>\d+)"
)
SUDO_RE = re.compile(
    r"^\s*(?P<user>\S+)\s*:\s*TTY=(?P<tty>\S+)\s*;\s*PWD=(?P<pwd>[^;]*?)\s*;\s*"
    r"USER=(?P<target>\S+)\s*;\s*COMMAND=(?P<cmd>.*)$"
)
SESSION_CLOSED_RE = re.compile(r"^pam_unix\(sshd:session\): session closed for user (?P<user>\S+)")
KEY_RE = re.compile(r"ssh-ed25519\s+(?P<blob>[A-Za-z0-9+/=]{40,})")

HOME_AK_RE = re.compile(r"^/home/[^/]+/\.ssh/authorized_keys$")


def iso(ts):
    if ts is None:
        return None
    y, mo, d, h, mi, s, _, _, _ = __import__("time").gmtime(int(ts))
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (y, mo, d, h, mi, s)


def parse_iso(text):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})Z?$", text.strip())
    if not m:
        return None
    g = [int(x) for x in m.groups()]
    return calendar.timegm(tuple(g) + (0, 0, 0))


# --------------------------------------------------------------------------- #
# collection.txt


def read_collection(root):
    info = {"hostname": None, "utc_offset": 0, "collected_utc": None}
    path = root / "collection.txt"
    if not path.exists():
        return info
    for line in path.read_text(errors="replace").splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "hostname":
            info["hostname"] = value
        elif key == "utc_offset":
            m = re.match(r"^([+-])(\d{2}):(\d{2})$", value)
            if m:
                sign = 1 if m.group(1) == "+" else -1
                info["utc_offset"] = sign * (int(m.group(2)) * 3600 + int(m.group(3)) * 60)
        elif key == "collected_utc":
            info["collected_utc"] = parse_iso(value)
    return info


# --------------------------------------------------------------------------- #
# auth logs


def auth_log_files(root):
    logdir = root / "var" / "log"
    found = []
    for path in glob.glob(str(logdir / "auth.log*")):
        name = os.path.basename(path)
        m = re.match(r"^auth\.log(?:\.(\d+))?(\.gz)?$", name)
        if not m:
            continue
        idx = int(m.group(1)) if m.group(1) else 0
        found.append((idx, path))
    # oldest first: higher rotation number is older
    found.sort(key=lambda p: -p[0])
    return [p for _, p in found]


def read_text_file(path):
    if path.endswith(".gz"):
        with gzip.open(path, "rt", errors="replace") as handle:
            return handle.read().splitlines()
    with open(path, "rt", errors="replace") as handle:
        return handle.read().splitlines()


def parse_auth_logs(root, offset, collected):
    """Return list of dicts with keys: reading, prog, pid, msg."""
    raw = []
    for path in auth_log_files(root):
        for line in read_text_file(path):
            if not line.strip():
                continue
            m = SYSLOG_RE.match(line)
            if not m:
                continue
            mon = MONTHS.get(m.group("mon"))
            if mon is None:
                continue
            raw.append(
                (
                    mon,
                    int(m.group("day")),
                    int(m.group("h")),
                    int(m.group("mi")),
                    int(m.group("s")),
                    m.group("prog"),
                    m.group("msg"),
                )
            )
    if not raw:
        return []

    # assign years walking backwards from the collection time (host local)
    base_local = collected if collected is not None else 0
    ref = base_local + offset
    ry, rmo, rd, rh, rmi, rs = __import__("time").gmtime(int(ref))[:6]
    year = ry
    prev = (rmo, rd, rh, rmi, rs)
    stamps = [None] * len(raw)
    for i in range(len(raw) - 1, -1, -1):
        mon, day, h, mi, s = raw[i][:5]
        cur = (mon, day, h, mi, s)
        if cur > prev:
            year -= 1
        while True:
            try:
                local = calendar.timegm((year, mon, day, h, mi, s, 0, 0, 0))
                break
            except Exception:
                year -= 1
        stamps[i] = local - offset
        prev = cur

    events = []
    for i, item in enumerate(raw):
        prog = item[5].strip()
        pm = PROG_RE.match(prog)
        name = pm.group("name") if pm else prog
        pid = int(pm.group("pid")) if (pm and pm.group("pid")) else None
        events.append(
            {"reading": stamps[i], "prog": name, "pid": pid, "msg": item[6]}
        )
    return events


def parse_remote_log(root, hostname):
    logdir = root / "var" / "log" / "remote"
    paths = []
    if logdir.is_dir():
        if hostname:
            cand = logdir / ("%s.log" % hostname)
            if cand.exists():
                paths.append(str(cand))
        if not paths:
            paths = sorted(glob.glob(str(logdir / "*.log")))
    events = []
    for path in paths:
        for line in read_text_file(path):
            if not line.strip():
                continue
            m = REMOTE_RE.match(line)
            if not m:
                continue
            ts = parse_iso(m.group("ts"))
            if ts is None:
                continue
            prog = m.group("prog").strip()
            pm = PROG_RE.match(prog)
            name = pm.group("name") if pm else prog
            pid = int(pm.group("pid")) if (pm and pm.group("pid")) else None
            events.append({"time": ts, "prog": name, "pid": pid, "msg": m.group("msg")})
    return events


# --------------------------------------------------------------------------- #
# clock step


def build_clock(auth_events, remote_events, wtmp=()):
    """Return a function mapping a host-clock reading to the true UTC time."""
    auth_index = {}
    for ev in auth_events:
        auth_index.setdefault((ev["pid"], ev["msg"]), []).append(ev["reading"])
    remote_index = {}
    for ev in remote_events:
        remote_index.setdefault((ev["pid"], ev["msg"]), []).append(ev["time"])

    pairs = []
    for key, readings in auth_index.items():
        trues = remote_index.get(key)
        if not trues or len(readings) != 1 or len(trues) != 1:
            continue
        pairs.append((readings[0], trues[0] - readings[0]))

    if not pairs:
        return lambda reading: reading

    counts = {}
    for _, delta in pairs:
        counts[delta] = counts.get(delta, 0) + 1
    values = sorted(counts, key=lambda d: (-counts[d], d))[:2]
    d_lo = min(values)
    d_hi = max(values)
    if d_lo == d_hi:
        shift = d_lo
        return lambda reading: reading + shift

    # Refine where the step lies: the collector also holds every successful
    # login, so wtmp logins can be tied to their true time independently of
    # what survived log rotation.
    remote_logins = []
    for ev in remote_events:
        if ev["prog"] != "sshd":
            continue
        m = ACCEPTED_RE.match(ev["msg"])
        if m:
            remote_logins.append((ev["time"], m.group("user"), m.group("addr")))
    for rec in wtmp:
        if rec.get("type") != 7 or not rec.get("host"):
            continue
        deltas = set()
        for t, user, addr in remote_logins:
            if user != rec["user"] or addr != rec["host"]:
                continue
            delta = t - rec["reading"]
            if delta in (d_lo, d_hi):
                deltas.add(delta)
        if len(deltas) == 1:
            pairs.append((rec["reading"], deltas.pop()))

    threshold = min(r for r, d in pairs if d == d_lo)

    def correct(reading):
        return reading + (d_hi if reading < threshold else d_lo)

    return correct


# --------------------------------------------------------------------------- #
# wtmp / btmp

UTMP = struct.Struct("<ii16s32s64sii")


def parse_utmp(path):
    records = []
    if not path.exists():
        return records
    data = path.read_bytes()
    for off in range(0, len(data) - 127, 128):
        typ, pid, line, user, host, sec, _usec = UTMP.unpack(data[off:off + 128])
        records.append(
            {
                "type": typ,
                "pid": pid,
                "line": line.split(b"\0")[0].decode("utf-8", "replace"),
                "user": user.split(b"\0")[0].decode("utf-8", "replace"),
                "host": host.split(b"\0")[0].decode("utf-8", "replace"),
                "reading": sec,
            }
        )
    records.sort(key=lambda r: r["reading"])
    return records


# --------------------------------------------------------------------------- #
# dpkg / fs listing


def parse_dpkg(root, offset):
    installs = {}
    path = root / "var" / "log" / "dpkg.log"
    if path.exists():
        for line in read_text_file(str(path)):
            m = re.match(
                r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) status installed (\S+?)(?::\S+)? ",
                line,
            )
            if not m:
                continue
            reading = parse_iso(m.group(1).replace(" ", "T"))
            if reading is None:
                continue
            installs.setdefault(m.group(2), []).append(reading - offset)
    listed = {}
    infodir = root / "var" / "lib" / "dpkg" / "info"
    if infodir.is_dir():
        for path in sorted(glob.glob(str(infodir / "*.list"))):
            pkg = os.path.basename(path)[: -len(".list")]
            for line in read_text_file(path):
                line = line.strip()
                if line:
                    listed.setdefault(line, set()).add(pkg)
    return installs, listed


def parse_fs_listing(root):
    rows = []
    path = root / "fs-listing.tsv"
    if not path.exists():
        return rows
    lines = read_text_file(str(path))
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        if parts[0] == "path":
            continue
        try:
            mtime = int(parts[4])
            ctime = int(parts[5])
        except ValueError:
            continue
        rows.append({"path": parts[0], "owner": parts[2], "mtime": mtime, "ctime": ctime})
    return rows


def is_persistence_kind(path):
    if path.startswith("/etc/cron.d/"):
        return True
    if path.startswith("/var/spool/cron/crontabs/"):
        return True
    if path.startswith("/etc/systemd/system/") and (
        path.endswith(".service") or path.endswith(".timer")
    ):
        return True
    if path == "/etc/rc.local":
        return True
    if path == "/root/.ssh/authorized_keys":
        return True
    if HOME_AK_RE.match(path):
        return True
    return False


# --------------------------------------------------------------------------- #
# histories and keys


def history_files(root):
    out = {}
    rootpath = root / "root" / ".bash_history"
    if rootpath.exists():
        out["root"] = rootpath
    homedir = root / "home"
    if homedir.is_dir():
        for entry in sorted(homedir.iterdir()):
            path = entry / ".bash_history"
            if path.exists():
                out[entry.name] = path
    return out


def parse_history(path):
    """Return list of (reading_or_None, command)."""
    entries = []
    pending = None
    for line in read_text_file(str(path)):
        if re.match(r"^#\d{6,}\s*$", line):
            pending = int(line[1:].strip())
            continue
        if line.strip() == "":
            continue
        entries.append((pending, line))
        pending = None
    return entries


def fingerprint(blob):
    try:
        raw = base64.b64decode(blob + "=" * (-len(blob) % 4))
    except Exception:
        return None
    digest = hashlib.sha256(raw).digest()
    return base64.b64encode(digest).decode("ascii").rstrip("=")


def keys_written(entries):
    """Fingerprints of keys that commands in this history write to authorized_keys."""
    out = set()
    for _ts, cmd in entries:
        if "authorized_keys" not in cmd:
            continue
        for m in KEY_RE.finditer(cmd):
            fp = fingerprint(m.group("blob"))
            if fp:
                out.add(fp)
    return out


# --------------------------------------------------------------------------- #
# analysis


def analyze(evidence_dir):
    root = Path(evidence_dir)
    info = read_collection(root)
    offset = info["utc_offset"]
    collected = info["collected_utc"]

    auth_events = parse_auth_logs(root, offset, collected)
    remote_events = parse_remote_log(root, info["hostname"])
    wtmp = parse_utmp(root / "var" / "log" / "wtmp")
    btmp = parse_utmp(root / "var" / "log" / "btmp")
    correct = build_clock(auth_events, remote_events, wtmp)

    # ---- failed attempts (btmp is complete; auth logs may be rotated away)
    failures = {}
    for rec in btmp:
        if rec["type"] != 6:
            continue
        if not rec["host"]:
            continue
        failures[(rec["reading"], rec["host"], rec["user"])] = True
    for ev in auth_events:
        if ev["prog"] != "sshd":
            continue
        m = FAILED_RE.match(ev["msg"])
        if m:
            failures[(ev["reading"], m.group("addr"), m.group("user"))] = True
    fail_list = [
        {"time": correct(reading), "addr": addr, "user": user}
        for (reading, addr, user) in failures
    ]

    by_addr = {}
    for f in fail_list:
        by_addr.setdefault(f["addr"], []).append(f["time"])
    hostile = set()
    for addr, times in by_addr.items():
        times.sort()
        for i in range(len(times) - 4):
            if times[i + 4] - times[i] <= 600:
                hostile.add(addr)
                break

    # ---- logins
    logins = {}

    def login_slot(t, user, addr):
        key = (t, user, addr)
        if key not in logins:
            logins[key] = {
                "time": t,
                "user": user,
                "addr": addr,
                "method": None,
                "fp": None,
                "pid": None,
                "terminal": None,
            }
        return logins[key]

    for ev in remote_events:
        if ev["prog"] != "sshd":
            continue
        m = ACCEPTED_RE.match(ev["msg"])
        if not m:
            continue
        slot = login_slot(ev["time"], m.group("user"), m.group("addr"))
        slot["method"] = m.group("method")
        if m.group("fp"):
            slot["fp"] = m.group("fp")
        if ev["pid"] is not None:
            slot["pid"] = ev["pid"]
    for ev in auth_events:
        if ev["prog"] != "sshd":
            continue
        m = ACCEPTED_RE.match(ev["msg"])
        if not m:
            continue
        slot = login_slot(correct(ev["reading"]), m.group("user"), m.group("addr"))
        slot["method"] = m.group("method")
        if m.group("fp"):
            slot["fp"] = m.group("fp")
        if ev["pid"] is not None:
            slot["pid"] = ev["pid"]
    for rec in wtmp:
        if rec["type"] != 7:
            continue
        slot = login_slot(correct(rec["reading"]), rec["user"], rec["host"])
        slot["terminal"] = rec["line"]

    sessions = sorted(logins.values(), key=lambda s: (s["time"], s["user"]))

    # ---- session ends
    closes_by_pid = {}
    for ev in remote_events:
        if ev["prog"] != "sshd":
            continue
        m = SESSION_CLOSED_RE.match(ev["msg"])
        if m and ev["pid"] is not None:
            closes_by_pid.setdefault(ev["pid"], []).append(ev["time"])
    for ev in auth_events:
        if ev["prog"] != "sshd":
            continue
        m = SESSION_CLOSED_RE.match(ev["msg"])
        if m and ev["pid"] is not None:
            closes_by_pid.setdefault(ev["pid"], []).append(correct(ev["reading"]))

    dead_by_line = {}
    for rec in wtmp:
        if rec["type"] == 8 and rec["line"]:
            dead_by_line.setdefault(rec["line"], []).append(correct(rec["reading"]))
    for times in dead_by_line.values():
        times.sort()

    starts_by_line = {}
    for s in sessions:
        if s["terminal"]:
            starts_by_line.setdefault(s["terminal"], []).append(s["time"])
    for times in starts_by_line.values():
        times.sort()

    for s in sessions:
        cands = []
        if s["pid"] is not None:
            for t in closes_by_pid.get(s["pid"], []):
                if t >= s["time"]:
                    cands.append(t)
        if s["terminal"]:
            nxt = None
            for t in starts_by_line.get(s["terminal"], []):
                if t > s["time"]:
                    nxt = t
                    break
            for t in dead_by_line.get(s["terminal"], []):
                if t >= s["time"] and (nxt is None or t <= nxt):
                    cands.append(t)
                    break
        if cands:
            s["logout"] = min(cands)
            s["end"] = s["logout"]
        else:
            s["logout"] = None
            s["end"] = collected if collected is not None else s["time"]

    # ---- sudo commands
    sudos = []
    for ev in auth_events:
        if ev["prog"] != "sudo":
            continue
        m = SUDO_RE.match(ev["msg"])
        if not m:
            continue
        sudos.append(
            {
                "time": correct(ev["reading"]),
                "user": m.group("user"),
                "tty": m.group("tty"),
                "target": m.group("target"),
                "cmd": m.group("cmd"),
            }
        )

    # ---- histories
    hist_paths = history_files(root)
    histories = {name: parse_history(path) for name, path in hist_paths.items()}

    # ---- attribution fixpoint
    if not hostile:
        return empty_report()
    entry = None
    for s in sessions:
        if s["addr"] in hostile:
            entry = s
            break
    if entry is None:
        return empty_report()

    sources = {entry["addr"]}
    accounts = {entry["user"]}
    intruder_sessions = [entry]
    intruder_keys = set()

    def in_intruder_session(t, terminal=None):
        for s in intruder_sessions:
            if terminal is not None and s["terminal"] != terminal:
                continue
            if s["time"] <= t <= s["end"]:
                return s
        return None

    root_times = []
    intruder_sudos = []
    hist_events = []

    changed = True
    while changed:
        changed = False

        for name in sorted(accounts):
            if name not in histories:
                continue
            for fp in keys_written(histories[name]):
                if fp not in intruder_keys:
                    intruder_keys.add(fp)
                    changed = True

        for s in sessions:
            if s in intruder_sessions:
                continue
            if s["addr"] in sources or (s["fp"] and s["fp"] in intruder_keys):
                intruder_sessions.append(s)
                changed = True

        for s in intruder_sessions:
            if s["addr"] not in sources:
                sources.add(s["addr"])
                changed = True
            if s["user"] not in accounts:
                accounts.add(s["user"])
                changed = True

        # commands the intruder ran as root: sudo on one of its terminals,
        # or a login straight to root
        root_times = []
        intruder_sudos = []
        for sd in sudos:
            s = in_intruder_session(sd["time"], sd["tty"])
            if s is not None and s["user"] == sd["user"]:
                intruder_sudos.append(sd)
                if sd["target"] == "root":
                    root_times.append(sd["time"])
        for s in intruder_sessions:
            if s["user"] == "root":
                root_times.append(s["time"])

        # timestamped history commands inside the intruder's sessions
        hist_events = []
        for name in sorted(set(accounts) | {"root"}):
            if name not in histories:
                continue
            for ts, _cmd in histories[name]:
                if ts is None:
                    continue
                t = correct(ts)
                for s in intruder_sessions:
                    if s["time"] <= t <= s["end"] and (
                        name == "root" or s["user"] == name
                    ):
                        hist_events.append((name, t))
                        break
        for name, t in hist_events:
            if name == "root":
                root_times.append(t)

        if root_times and "root" not in accounts:
            accounts.add("root")
            changed = True

    # ---- persistence
    installs, listed = parse_dpkg(root, offset)
    rows = parse_fs_listing(root)
    persistence = []
    for row in rows:
        path = row["path"]
        if not is_persistence_kind(path):
            continue
        t = correct(row["ctime"])
        if in_intruder_session(t) is None:
            continue
        pkg_written = False
        for pkg in listed.get(path, ()):
            for r in installs.get(pkg, ()):
                if abs(row["ctime"] - r) <= 2:
                    pkg_written = True
                    break
            if pkg_written:
                break
        if pkg_written:
            continue
        persistence.append((path, t))

    # ---- activity window
    events = []
    for f in fail_list:
        if f["addr"] in sources:
            events.append(f["time"])
    for s in intruder_sessions:
        events.append(s["time"])
        if s["logout"] is not None:
            events.append(s["logout"])
    for sd in intruder_sudos:
        events.append(sd["time"])
    for _name, t in hist_events:
        events.append(t)
    for _path, t in persistence:
        events.append(t)

    first = min(events) if events else entry["time"]
    last = max(events) if events else entry["time"]

    return {
        "initial_access": {
            "account": entry["user"],
            "source": entry["addr"],
            "time": iso(entry["time"]),
        },
        "sources": sorted(sources),
        "accounts": sorted(accounts),
        "privilege_escalation": iso(min(root_times)) if root_times else None,
        "persistence": sorted({p for p, _ in persistence}),
        "first_activity": iso(first),
        "last_activity": iso(last),
    }


def empty_report():
    return {
        "initial_access": {"account": None, "source": None, "time": None},
        "sources": [],
        "accounts": [],
        "privilege_escalation": None,
        "persistence": [],
        "first_activity": None,
        "last_activity": None,
    }


def main(argv):
    if len(argv) != 3:
        print("usage: triage.py <evidence_dir> <out.json>", file=sys.stderr)
        return 2
    Path(argv[2]).write_text(json.dumps(analyze(Path(argv[1])), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
