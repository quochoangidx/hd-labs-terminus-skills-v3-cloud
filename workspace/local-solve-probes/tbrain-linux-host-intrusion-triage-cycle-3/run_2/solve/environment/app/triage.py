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
import time
from pathlib import Path

MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

PERSIST_DIRS = ("/etc/cron.d/", "/var/spool/cron/crontabs/")
UNIT_DIR = "/etc/systemd/system/"


def utc(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(ts)))


def parse_iso(s):
    t = time.strptime(s.strip(), "%Y-%m-%dT%H:%M:%SZ")
    return calendar.timegm(t)


# ---------------------------------------------------------------- collection

def read_collection(root):
    info = {}
    for line in (root / "collection.txt").read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    off = info["utc_offset"]
    sign = -1 if off.startswith("-") else 1
    hh, mm = off[1:].split(":")
    offset = sign * (int(hh) * 3600 + int(mm) * 60)
    return info["hostname"], offset, parse_iso(info["collected_utc"])


def local_to_host_epoch(y, mo, d, h, mi, s, offset):
    """Host wall-clock time -> host-clock epoch value."""
    return calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0)) - offset


# ------------------------------------------------------------------ auth log

AUTH_RE = re.compile(
    r"^([A-Z][a-z]{2}) ([ \d]\d) (\d\d):(\d\d):(\d\d) (\S+) (.*)$")
PROG_RE = re.compile(r"^([A-Za-z0-9_.\-]+)(?:\[(\d+)\])?:\s?(.*)$")


def auth_log_paths(root):
    logdir = root / "var" / "log"
    paths = []
    for p in glob.glob(str(logdir / "auth.log*")):
        name = os.path.basename(p)
        if name == "auth.log":
            n = 0
        else:
            m = re.match(r"^auth\.log\.(\d+)(\.gz)?$", name)
            if not m:
                continue
            n = int(m.group(1))
        paths.append((n, p))
    # higher number = older, so read from the largest down to auth.log
    paths.sort(key=lambda x: -x[0])
    return [p for _, p in paths]


def read_text_lines(path):
    if path.endswith(".gz"):
        with gzip.open(path, "rt", errors="replace") as fh:
            return fh.read().splitlines()
    with open(path, "rt", errors="replace") as fh:
        return fh.read().splitlines()


def parse_auth_logs(root, offset, collected_utc):
    """Return list of dicts with host_epoch, program, pid, message (in order)."""
    raw = []
    for path in auth_log_paths(root):
        for line in read_text_lines(path):
            m = AUTH_RE.match(line)
            if not m:
                continue
            mon, day, hh, mi, ss, host, rest = m.groups()
            if mon not in MONTHS:
                continue
            pm = PROG_RE.match(rest)
            if not pm:
                continue
            prog, pid, msg = pm.groups()
            raw.append({
                "mon": MONTHS[mon], "day": int(day),
                "h": int(hh), "mi": int(mi), "s": int(ss),
                "program": prog, "pid": int(pid) if pid else None,
                "message": msg,
            })
    # assign years working backwards from the collection date (host wall clock)
    ct = time.gmtime(collected_utc + offset)
    year = ct.tm_year
    prev = (ct.tm_mon, ct.tm_mday)
    for e in reversed(raw):
        md = (e["mon"], e["day"])
        if md > prev:
            year -= 1
        e["year"] = year
        prev = md
    for e in raw:
        e["host_epoch"] = local_to_host_epoch(
            e["year"], e["mon"], e["day"], e["h"], e["mi"], e["s"], offset)
    return raw


# --------------------------------------------------------------- remote log

REMOTE_RE = re.compile(
    r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) (\S+) ([A-Za-z0-9_.\-]+)"
    r"(?:\[(\d+)\])?:\s?(.*)$")


def parse_remote(root, hostname):
    out = []
    rdir = root / "var" / "log" / "remote"
    if not rdir.is_dir():
        return out
    for name in sorted(os.listdir(str(rdir))):
        for line in read_text_lines(str(rdir / name)):
            m = REMOTE_RE.match(line)
            if not m:
                continue
            ts, host, prog, pid, msg = m.groups()
            out.append({
                "true": parse_iso(ts), "program": prog,
                "pid": int(pid) if pid else None, "message": msg,
            })
    out.sort(key=lambda e: e["true"])
    return out


# ------------------------------------------------------------ clock skew fix

class Clock(object):
    """Maps host-clock times to true UTC times (rule 1)."""

    def __init__(self, delta=0, threshold=None):
        self.delta = delta          # amount the host clock ran behind
        self.threshold = threshold  # first host-clock value that is correct

    def true(self, host_epoch):
        if self.delta and (self.threshold is None
                           or host_epoch < self.threshold):
            return host_epoch + self.delta
        return host_epoch


MAX_STEP = 7200
MIN_STEP = 30


def build_clock(auth, remote):
    """The host clock may have run behind by a fixed amount and then been set
    forward once (rule 1).  Lines the remote collector also holds pin it down:
    every such line gives the difference between the collector's correct time
    and the host's own stamp."""
    index = {}
    for r in remote:
        if r["program"] != "sshd" or r["pid"] is None:
            continue
        index.setdefault((r["pid"], r["message"]), []).append(r["true"])

    votes = []      # (host_epoch, delta) from lines with one plausible match
    for e in auth:
        if e["program"] != "sshd" or e["pid"] is None:
            continue
        h = e["host_epoch"]
        cand = set()
        for true in index.get((e["pid"], e["message"]), ()):
            d = true - h
            if d == 0 or MIN_STEP <= d <= MAX_STEP:
                cand.add(d)
        if len(cand) == 1:
            votes.append((h, cand.pop()))
    if not votes:
        return Clock()

    counts = {}
    for _, d in votes:
        if d:
            counts[d] = counts.get(d, 0) + 1
    if not counts:
        return Clock()
    delta = max(counts, key=lambda d: (counts[d], d))
    correct = [h for h, d in votes if d == 0]
    threshold = min(correct) if correct else None
    if threshold is not None:
        behind = [h for h, d in votes if d == delta and h < threshold]
        if not behind:
            # nothing actually ran behind before that point
            return Clock()
    return Clock(delta, threshold)


# --------------------------------------------------------------- wtmp / btmp

def parse_utmp(path):
    recs = []
    try:
        data = open(path, "rb").read()
    except IOError:
        return recs
    for i in range(0, len(data) - 127, 128):
        chunk = data[i:i + 128]
        rtype, pid = struct.unpack("<ii", chunk[0:8])
        line = chunk[8:24].split(b"\0")[0].decode("utf-8", "replace")
        user = chunk[24:56].split(b"\0")[0].decode("utf-8", "replace")
        host = chunk[56:120].split(b"\0")[0].decode("utf-8", "replace")
        sec = struct.unpack("<i", chunk[120:124])[0]
        recs.append({"type": rtype, "pid": pid, "line": line,
                     "user": user, "host": host, "sec": sec})
    return recs


# ------------------------------------------------------------------ dpkg

DPKG_RE = re.compile(r"^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d) (.*)$")


def parse_dpkg(root, offset):
    """Return list of (host_epoch, package) for 'status installed' lines."""
    out = []
    p = root / "var" / "log" / "dpkg.log"
    if not p.is_file():
        return out
    for line in read_text_lines(str(p)):
        m = DPKG_RE.match(line)
        if not m:
            continue
        y, mo, d, hh, mi, ss, action = m.groups()
        parts = action.split()
        if len(parts) >= 2 and parts[0] == "status" and parts[1] == "installed":
            pkg = parts[2].split(":")[0] if len(parts) > 2 else ""
            out.append((local_to_host_epoch(int(y), int(mo), int(d), int(hh),
                                            int(mi), int(ss), offset), pkg))
    return out


def package_files(root):
    files = {}
    d = root / "var" / "lib" / "dpkg" / "info"
    if not d.is_dir():
        return files
    for name in sorted(os.listdir(str(d))):
        if not name.endswith(".list"):
            continue
        pkg = name[:-len(".list")]
        paths = set()
        for line in read_text_lines(str(d / name)):
            line = line.strip()
            if line:
                paths.add(line)
        files[pkg] = paths
    return files


# ------------------------------------------------------------- fs listing

def parse_fs_listing(root):
    out = []
    p = root / "fs-listing.tsv"
    if not p.is_file():
        return out
    lines = read_text_lines(str(p))
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        try:
            mtime = int(parts[4])
            ctime = int(parts[5])
        except ValueError:
            continue
        out.append({"path": parts[0], "mode": parts[1], "owner": parts[2],
                    "mtime": mtime, "ctime": ctime})
    return out


HOME_KEYS_RE = re.compile(r"^/home/[^/]+/\.ssh/authorized_keys$")


def is_persistence_kind(path):
    if path.startswith(PERSIST_DIRS):
        return True
    if path.startswith(UNIT_DIR) and (path.endswith(".service")
                                      or path.endswith(".timer")):
        return True
    if path == "/etc/rc.local":
        return True
    if path == "/root/.ssh/authorized_keys":
        return True
    return bool(HOME_KEYS_RE.match(path))


# -------------------------------------------------------------- histories

HIST_TIME_RE = re.compile(r"^#(\d{6,})\s*$")
KEY_RE = re.compile(r"ssh-ed25519\s+([A-Za-z0-9+/=]{20,})")


def read_histories(root):
    """account -> list of (host_epoch or None, command)."""
    hist = {}
    candidates = []
    rp = root / "root" / ".bash_history"
    if rp.is_file():
        candidates.append(("root", rp))
    home = root / "home"
    if home.is_dir():
        for user in sorted(os.listdir(str(home))):
            p = home / user / ".bash_history"
            if p.is_file():
                candidates.append((user, p))
    for account, path in candidates:
        entries = []
        pending = None
        for line in read_text_lines(str(path)):
            m = HIST_TIME_RE.match(line)
            if m:
                pending = int(m.group(1))
                continue
            entries.append((pending, line))
            pending = None
        hist[account] = entries
    return hist


def key_fingerprint(blob_b64):
    try:
        blob = base64.b64decode(blob_b64 + "=" * (-len(blob_b64) % 4))
    except Exception:
        return None
    digest = hashlib.sha256(blob).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


# ------------------------------------------------------------------ triage

SUDO_RE = re.compile(
    r"^\s*(\S+)\s*:\s*TTY=(\S+)\s*;\s*PWD=(.*?)\s*;\s*USER=(\S+)\s*;"
    r"\s*COMMAND=(.*)$")
FAILED_RE = re.compile(
    r"^Failed password for (?:invalid user )?(\S+) from (\S+) port \d+ ssh2")
ACCEPT_RE = re.compile(
    r"^Accepted (\S+) for (\S+) from (\S+) port (\d+) ssh2(?::.*?"
    r"(SHA256:[A-Za-z0-9+/]+))?\s*$")


def analyze(evidence_dir):
    root = Path(evidence_dir)
    hostname, offset, collected = read_collection(root)
    auth = parse_auth_logs(root, offset, collected)
    remote = parse_remote(root, hostname)
    clock = build_clock(auth, remote)
    T = clock.true

    logdir = root / "var" / "log"
    wtmp = parse_utmp(str(logdir / "wtmp"))
    btmp = parse_utmp(str(logdir / "btmp"))

    # --- failed attempts (rule 2): btmp holds every one of them
    failures = []
    for r in btmp:
        if r["type"] == 6 and r["host"]:
            failures.append({"t": T(r["sec"]), "user": r["user"],
                             "addr": r["host"]})
    if not failures:
        # btmp normally holds every failed attempt; fall back to the auth logs
        for e in auth:
            if e["program"] != "sshd":
                continue
            m = FAILED_RE.match(e["message"])
            if m:
                failures.append({"t": T(e["host_epoch"]), "user": m.group(1),
                                 "addr": m.group(2)})
    by_addr = {}
    for f in failures:
        by_addr.setdefault(f["addr"], []).append(f["t"])
    hostile = set()
    for addr, times in by_addr.items():
        times.sort()
        for i in range(len(times) - 4):
            if times[i + 4] - times[i] <= 600:
                hostile.add(addr)
                break

    # --- sessions, from wtmp (terminals) merged with sshd "Accepted" lines
    sessions = []
    open_by_line = {}
    for r in sorted(wtmp, key=lambda r: r["sec"]):
        if r["type"] == 7 and r["user"]:
            s = {"user": r["user"], "addr": r["host"], "tty": r["line"],
                 "login": T(r["sec"]), "logout": None, "fp": None,
                 "method": None}
            sessions.append(s)
            open_by_line[(r["pid"], r["line"])] = s
        elif r["type"] == 8:
            s = open_by_line.pop((r["pid"], r["line"]), None)
            if s is None:
                for cand in reversed(sessions):
                    if cand["tty"] == r["line"] and cand["logout"] is None \
                            and cand["login"] <= T(r["sec"]):
                        s = cand
                        break
            if s is not None:
                s["logout"] = T(r["sec"])

    # accepted logins seen in the logs (auth logs + remote collector)
    accepted = []
    for e in auth:
        if e["program"] != "sshd":
            continue
        m = ACCEPT_RE.match(e["message"])
        if m:
            accepted.append({"t": T(e["host_epoch"]), "method": m.group(1),
                             "user": m.group(2), "addr": m.group(3),
                             "fp": m.group(5), "pid": e["pid"]})
    for r in remote:
        if r["program"] != "sshd":
            continue
        m = ACCEPT_RE.match(r["message"])
        if m:
            accepted.append({"t": r["true"], "method": m.group(1),
                             "user": m.group(2), "addr": m.group(3),
                             "fp": m.group(5), "pid": r["pid"]})
    seen = set()
    logins = []
    for a in sorted(accepted, key=lambda a: a["t"]):
        key = (a["t"], a["user"], a["addr"])
        if key in seen:
            continue
        seen.add(key)
        logins.append(a)

    # attach method/fingerprint to wtmp sessions; add logins wtmp never saw
    for a in logins:
        match = None
        for s in sessions:
            if s["user"] == a["user"] and s["addr"] == a["addr"] \
                    and s["login"] == a["t"]:
                match = s
                break
        if match is None:
            for s in sessions:
                if s["user"] == a["user"] and s["addr"] == a["addr"] \
                        and abs(s["login"] - a["t"]) <= 2 \
                        and s["method"] is None:
                    match = s
                    break
        if match is not None:
            match["method"] = a["method"]
            match["fp"] = a["fp"]
        else:
            sessions.append({"user": a["user"], "addr": a["addr"], "tty": None,
                             "login": a["t"], "logout": None, "fp": a["fp"],
                             "method": a["method"]})
    sessions.sort(key=lambda s: s["login"])

    # --- initial access (rule 3)
    first = None
    for s in sessions:
        if s["addr"] in hostile:
            if first is None or s["login"] < first["login"]:
                first = s
    if first is None:
        return {"initial_access": None, "sources": [], "accounts": [],
                "privilege_escalation": None, "persistence": [],
                "first_activity": None, "last_activity": None}
    ia_time = first["login"]
    initial_access = {"account": first["user"], "source": first["addr"],
                      "time": utc(ia_time)}

    # --- sudo commands
    sudos = []
    for e in auth:
        if e["program"] != "sudo":
            continue
        m = SUDO_RE.match(e["message"])
        if not m:
            continue
        user, tty, pwd, target, cmd = m.groups()
        sudos.append({"t": T(e["host_epoch"]), "user": user, "tty": tty,
                      "target": target, "cmd": cmd})

    histories = read_histories(root)

    # --- persistence-kind files changed during the intrusion (rule 6)
    installs = [(T(h), pkg) for h, pkg in parse_dpkg(root, offset)]
    pkg_files = package_files(root)

    def package_written(path, ctime_true):
        for t, pkg in installs:
            if abs(ctime_true - t) <= 2 and path in pkg_files.get(pkg, ()):
                return True
        return False

    persistence = []
    for f in parse_fs_listing(root):
        if not is_persistence_kind(f["path"]):
            continue
        ct = T(f["ctime"])
        if ct < ia_time or ct > collected:
            continue
        if package_written(f["path"], ct):
            continue
        persistence.append({"path": f["path"], "t": ct})

    # --- who is the intruder (rule 4): grow the tie set to a fixed point
    sources = {first["addr"]}
    accounts = {first["user"]}
    intruder_sessions = []
    intruder_sudos = []
    hist_events = []
    escalation = None

    def session_end(s):
        return s["logout"] if s["logout"] is not None else collected

    shells = []
    for _ in range(12):
        keys = set()
        for account in accounts:
            for ts, cmd in histories.get(account, ()):
                if "authorized_keys" not in cmd:
                    continue
                if ts is not None and not command_is_intruders(
                        account, T(ts), collected, intruder_sessions,
                        session_end, shells):
                    continue
                for blob in KEY_RE.findall(cmd):
                    fp = key_fingerprint(blob)
                    if fp:
                        keys.add(fp)

        new_sessions = [s for s in sessions
                        if s["addr"] in sources
                        or (s["fp"] and s["fp"] in keys)]
        new_sources = set(sources) | {s["addr"] for s in new_sessions
                                      if s["addr"]}
        new_accounts = set(accounts) | {s["user"] for s in new_sessions}

        new_sudos = []
        for sd in sudos:
            for s in new_sessions:
                if s["user"] == sd["user"] and s["tty"] == sd["tty"] \
                        and s["login"] <= sd["t"] <= session_end(s):
                    new_sudos.append(sd)
                    break

        esc_candidates = [sd["t"] for sd in new_sudos]
        esc_candidates += [s["login"] for s in new_sessions
                           if s["user"] == "root"]
        if esc_candidates:
            new_accounts.add("root")
            new_escalation = min(esc_candidates)
        else:
            new_escalation = None

        new_shells = root_shells(sudos, sessions, new_sudos, new_sessions)
        changed = (new_sources != sources or new_accounts != accounts
                   or new_shells != shells
                   or len(new_sessions) != len(intruder_sessions)
                   or len(new_sudos) != len(intruder_sudos)
                   or new_escalation != escalation)
        sources, accounts = new_sources, new_accounts
        intruder_sessions, intruder_sudos = new_sessions, new_sudos
        escalation = new_escalation
        shells = new_shells
        if not changed:
            break

    # commands from timestamped histories that we can pin on the intruder
    hist_events = []
    for account in accounts:
        for ts, cmd in histories.get(account, ()):
            if ts is None:
                continue
            t = T(ts)
            if command_is_intruders(account, t, collected, intruder_sessions,
                                    session_end, shells):
                hist_events.append(t)

    # --- activity (rule 7)
    events = []
    for f in failures:
        if f["addr"] in sources:
            events.append(f["t"])
    for s in intruder_sessions:
        events.append(s["login"])
        if s["logout"] is not None:
            events.append(s["logout"])
    events += [sd["t"] for sd in intruder_sudos]
    events += hist_events
    events += [p["t"] for p in persistence]
    events.append(ia_time)

    return {
        "initial_access": initial_access,
        "sources": sorted(sources),
        "accounts": sorted(accounts),
        "privilege_escalation": (utc(escalation) if escalation is not None
                                 else None),
        "persistence": sorted(set(p["path"] for p in persistence)),
        "first_activity": utc(min(events)),
        "last_activity": utc(max(events)),
    }


SHELLS = ("bash", "sh", "zsh", "dash", "ksh", "csh", "tcsh", "fish", "su",
          "login", "screen", "tmux")


def opens_root_shell(command):
    first = command.split()[0] if command.split() else ""
    return os.path.basename(first) in SHELLS


def root_shells(sudos, sessions, intruder_sudos, intruder_sessions):
    """Root shells anyone opened, as (start_time, is_intruders)."""
    shells = []
    for sd in sudos:
        if sd["target"] == "root" and opens_root_shell(sd["cmd"]):
            shells.append((sd["t"], sd in intruder_sudos))
    for s in sessions:
        if s["user"] == "root":
            shells.append((s["login"], s in intruder_sessions))
    shells.sort(key=lambda x: x[0])
    return shells


def command_is_intruders(account, t, collected, intruder_sessions,
                         session_end, shells):
    """Was a timestamped shell command of `account` at true time t run by the
    intruder?  A root command belongs to whoever opened the root shell it ran
    in; a command of any other account belongs to the session open on it."""
    if t > collected:
        return False
    if account == "root":
        owner = None
        for start, mine in shells:
            if start <= t:
                owner = mine
            else:
                break
        return bool(owner)
    for s in intruder_sessions:
        if s["user"] == account and s["login"] <= t <= session_end(s):
            return True
    return False


def main(argv):
    if len(argv) != 3:
        print("usage: triage.py <evidence_dir> <out.json>", file=sys.stderr)
        return 2
    Path(argv[2]).write_text(json.dumps(analyze(Path(argv[1])), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
